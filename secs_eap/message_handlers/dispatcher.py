"""
消息分发器

协调 DriverAdapter 和 MessageHandlerRegistry，
处理消息的接收和回复。
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable

from secs_driver.src.secs_message import SECSMessage, SECSItem

from .base_handler import MessageHandlerRegistry, HandlerResult
from ..driver_adapter import DriverAdapter, ConnectionState


logger = logging.getLogger(__name__)


class MessageDispatcher:
    """
    SECS 消息分发器

    工作流程：
    1. 从 DriverAdapter 接收消息
    2. 交给 MessageHandlerRegistry 分发给具体的处理器
    3. 处理器返回 HandlerResult
    4. 根据结果自动发送回复（或调用回调）
    """

    def __init__(self, driver_adapter: DriverAdapter):
        """
        初始化消息分发器

        Args:
            driver_adapter: 驱动适配器
        """
        self._driver_adapter = driver_adapter
        self._registry = MessageHandlerRegistry()
        self._running = False

        # 回调
        self._on_message_handled: Optional[Callable] = None
        self._on_no_handler: Optional[Callable] = None

        # 上下文信息
        self._context: Dict[str, Any] = {}

    def set_registry(self, registry: MessageHandlerRegistry) -> None:
        """设置消息处理器注册表"""
        self._registry = registry

    def set_context(self, key: str, value: Any) -> None:
        """设置上下文信息"""
        self._context[key] = value

    def get_context(self, key: str) -> Optional[Any]:
        """获取上下文信息"""
        return self._context.get(key)

    def set_callbacks(
        self,
        on_message_handled: Optional[Callable] = None,
        on_no_handler: Optional[Callable] = None,
    ) -> None:
        """设置回调函数"""
        self._on_message_handled = on_message_handled
        self._on_no_handler = on_no_handler

    def _invoke_callback(self, callback: Optional[Callable], *args, **kwargs) -> None:
        """统一处理同步/异步回调。"""
        if not callback:
            return

        try:
            result = callback(*args, **kwargs)
            if asyncio.iscoroutine(result):
                task = asyncio.create_task(result)
                task.add_done_callback(self._log_task_error)
        except Exception as e:
            logger.error(f"Dispatcher callback error: {e}")

    @staticmethod
    def _log_task_error(task: asyncio.Task) -> None:
        """记录异步回调任务中的未处理异常。"""
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Dispatcher async callback failed: {e}")

    async def start(self) -> None:
        """启动分发器"""
        if self._running:
            return

        self._running = True

        # 设置 Driver 的消息回调
        self._driver_adapter.set_callbacks(
            on_state_changed=self._on_state_changed,
            on_message_received=self._on_message_received,
            on_error=self._on_error,
        )

        logger.info("MessageDispatcher started")

    async def stop(self) -> None:
        """停止分发器"""
        self._running = False
        self._driver_adapter.set_callbacks()

        logger.info("MessageDispatcher stopped")

    async def _on_state_changed(self, state: ConnectionState) -> None:
        """连接状态变化回调"""
        logger.info(f"Dispatcher: connection state changed to {state.value}")
        self._context["connection_state"] = state

        # 连接断开时清理上下文
        if state == ConnectionState.DISCONNECTED:
            self._context.pop("session_id", None)

    async def _on_message_received(self, message: SECSMessage) -> None:
        """消息接收回调"""
        if not self._running:
            return

        logger.info(
            "Dispatcher received: %s (w_bit=%s, items=%d)",
            message.sf,
            message.w_bit,
            len(message.items or []),
        )
        self._context["last_message"] = message

        try:
            result = await self._registry.dispatch(message, self._context)

            if result is None:
                # 没有找到处理器
                logger.warning(f"No handler for {message.sf}")
                self._invoke_callback(self._on_no_handler, message)
                return

            if result.success:
                # 处理成功，检查是否需要回复
                await self._send_reply_if_needed(message, result)

                workflow_engine = self._context.get("workflow_engine")
                if workflow_engine:
                    await workflow_engine.handle_message(message, self._context)

                self._invoke_callback(self._on_message_handled, message, result)
            else:
                # 处理失败
                logger.warning(f"Handler failed for {message.sf}: {result.message}")
                self._invoke_callback(self._on_message_handled, message, result, success=False)

        except Exception as e:
            logger.exception(f"Error dispatching message {message.sf}: {e}")

    async def _send_reply_if_needed(
        self,
        message: SECSMessage,
        result: HandlerResult,
    ) -> None:
        """发送回复消息（如果需要）"""
        # 主消息需要回复
        if not message.w_bit:
            logger.info("Skip auto reply for %s because w_bit=False", message.sf)
            return

        # 回复消息已经由业务逻辑处理了，这里只需要发送回复
        reply_items = result.reply_items

        try:
            success = await self._driver_adapter.send_reply(message, reply_items)
            if success:
                logger.info("Sent auto reply for %s", message.sf)
            else:
                logger.warning(f"Failed to send reply for {message.sf}")
        except Exception as e:
            logger.error(f"Error sending reply for {message.sf}: {e}")

    async def send_reply(
        self,
        original_message: SECSMessage,
        items: list = None,
    ) -> bool:
        """
        手动发送回复

        Args:
            original_message: 原消息
            items: 回复数据项

        Returns:
            是否发送成功
        """
        return await self._driver_adapter.send_reply(original_message, items)

    def _on_error(self, error: Exception) -> None:
        """错误回调"""
        logger.error(f"Dispatcher error: {error}")

    @property
    def registry(self) -> MessageHandlerRegistry:
        """获取消息处理器注册表"""
        return self._registry

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running
