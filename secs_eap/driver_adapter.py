"""
驱动适配层

封装 SECS Driver，提供统一的接口给上层调用。
消息层和业务逻辑层都通过这个适配器与底层驱动交互。
"""

import asyncio
import logging
from typing import Optional, Callable, List, Dict, Any
from enum import Enum

from secs_driver.src.config import DriverConfig, ConnectionConfig, HSMSConfig, LoggingConfig
from secs_driver.src.secs_driver import SECSDriver, SECSEventHandler, SECSMessage, SECSItem
from secs_driver.src.secs_types import SECSTypeInfo
from secs_driver.src.hsms_protocol import HSMSConnectionState

from .config import EAPConfig, EquipmentConfig


logger = logging.getLogger(__name__)


def _format_scalar_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        hex_value = value.hex().upper()
        return f" 0x{hex_value}" if hex_value else " 0x"
    if isinstance(value, str):
        return f" '{value}'"
    return f" {value}"


def _format_item_standard(item: SECSItem, indent: int = 0) -> List[str]:
    pad = "  " * indent
    type_name = SECSTypeInfo.get_name(item.type)

    if type_name == "L":
        lines = [f"{pad}<L [{len(item.children)}]"]
        for child in item.children:
            lines.extend(_format_item_standard(child, indent + 1))
        lines.append(f"{pad}>")
        return lines

    return [f"{pad}<{type_name}{_format_scalar_value(item.value)}>"]


def _format_message_standard(message: SECSMessage) -> str:
    lines = [f"{message.sf}{' W' if message.w_bit else ''}"]
    for item in message.items or []:
        lines.extend(_format_item_standard(item, 1))
    return "\n".join(lines)


class ConnectionState(Enum):
    """连接状态"""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    SELECTED = "selected"
    DISCONNECTING = "disconnecting"


class DriverAdapter(SECSEventHandler):
    """
    SECS Driver 适配器

    封装 SECSDriver，提供：
    1. 统一的连接管理
    2. 消息发送接口
    3. 事件回调管理
    4. 状态管理
    """

    def __init__(self, config: EquipmentConfig):
        """
        初始化驱动适配器

        Args:
            config: 设备配置
        """
        self._config = config
        self._driver: Optional[SECSDriver] = None
        self._state = ConnectionState.DISCONNECTED

        # 事件回调
        self._on_state_changed: Optional[Callable] = None
        self._on_message_received: Optional[Callable] = None
        self._on_error: Optional[Callable] = None

        # 连接锁
        self._connect_lock = asyncio.Lock()

        logger.info(f"DriverAdapter initialized: {config.name}")

    def set_callbacks(
        self,
        on_state_changed: Optional[Callable] = None,
        on_message_received: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
    ) -> None:
        """设置回调函数"""
        self._on_state_changed = on_state_changed
        self._on_message_received = on_message_received
        self._on_error = on_error

    def _invoke_callback(self, callback: Optional[Callable], *args) -> None:
        """统一处理同步/异步回调。"""
        if not callback:
            return

        try:
            result = callback(*args)
            if asyncio.iscoroutine(result):
                task = asyncio.create_task(result)
                task.add_done_callback(self._log_task_error)
        except Exception as e:
            logger.error(f"Callback error: {e}")

    @staticmethod
    def _log_task_error(task: asyncio.Task) -> None:
        """记录异步回调任务中的未处理异常。"""
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Async callback task failed: {e}")

    def _update_state(self, new_state: ConnectionState) -> None:
        """更新连接状态"""
        if self._state != new_state:
            logger.info(f"Connection state: {self._state.value} -> {new_state.value}")
            self._state = new_state
            self._invoke_callback(self._on_state_changed, new_state)

    # ==================== SECSEventHandler 回调实现 ====================

    def on_connected(self, session_id: int) -> None:
        """TCP 连接建立"""
        logger.info(f"TCP connected, session_id={session_id}")
        self._update_state(ConnectionState.CONNECTED)

    def on_disconnected(self, session_id: int, reason: str) -> None:
        """TCP 连接断开"""
        logger.info(f"TCP disconnected: {reason}")
        self._update_state(ConnectionState.DISCONNECTED)

    def on_selected(self) -> None:
        """会话选择成功"""
        logger.info("Session selected")
        self._update_state(ConnectionState.SELECTED)

    def on_deselected(self) -> None:
        """会话取消选择"""
        logger.info("Session deselected")
        self._update_state(ConnectionState.CONNECTED)

    def on_separated(self) -> None:
        """对方发起断开连接"""
        logger.info("Received Separate request")
        self._update_state(ConnectionState.CONNECTED)

    def on_message_received(self, message: SECSMessage) -> None:
        """收到 SECS-II 消息"""
        logger.info("RX\n%s", _format_message_standard(message))
        self._invoke_callback(self._on_message_received, message)

    def on_message_sent(self, message: SECSMessage) -> None:
        """消息发送成功"""
        logger.debug(f"Message sent: {message.sf}")

    def on_timeout(self, message: SECSMessage) -> None:
        """消息超时"""
        logger.warning(f"Message timeout: {message.sf}")
        self._invoke_callback(self._on_error, TimeoutError(f"Message timeout: {message.sf}"))

    def on_error(self, error: Exception) -> None:
        """发生错误"""
        logger.error(f"Driver error: {error}")
        self._invoke_callback(self._on_error, error)

    # ==================== 连接管理 ====================

    async def connect(self) -> bool:
        """
        建立连接

        Returns:
            连接是否成功
        """
        async with self._connect_lock:
            if self._state in (ConnectionState.CONNECTING, ConnectionState.CONNECTED, ConnectionState.SELECTED):
                logger.warning(f"Already connected: {self._state.value}")
                return True

            self._update_state(ConnectionState.CONNECTING)

            try:
                # 创建 Driver 配置
                driver_config = DriverConfig(
                    name=self._config.name,
                    device_id=self._config.device_id,
                    connection=ConnectionConfig(
                        mode=self._config.mode,
                        host=self._config.host,
                        port=self._config.port,
                        timeout=self._config.timeout,
                        retry_interval=self._config.retry_interval,
                        max_retry=self._config.max_retry,
                    ),
                    hsms=HSMSConfig(
                        t3_timeout=self._config.t3_timeout,
                        t5_timeout=self._config.t5_timeout,
                        t6_timeout=self._config.t6_timeout,
                        t7_timeout=self._config.t7_timeout,
                        t8_timeout=self._config.t8_timeout,
                    ),
                    logging=LoggingConfig(
                        level=self._config.log_level,
                        file=self._config.log_file,
                    ),
                )

                # 创建 Driver
                self._driver = SECSDriver(driver_config)
                self._driver.set_event_handler(self)

                # 连接
                success = await self._driver.connect()

                if success:
                    logger.info(f"Connected to {self._config.host}:{self._config.port}")
                    return True
                else:
                    logger.error("Failed to connect")
                    self._update_state(ConnectionState.DISCONNECTED)
                    return False

            except Exception as e:
                logger.error(f"Connection error: {e}")
                self._update_state(ConnectionState.DISCONNECTED)
                self._invoke_callback(self._on_error, e)
                return False

    async def disconnect(self) -> None:
        """断开连接"""
        async with self._connect_lock:
            if self._state == ConnectionState.DISCONNECTED:
                return

            self._update_state(ConnectionState.DISCONNECTING)

            try:
                if self._driver:
                    await self._driver.disconnect()
                    self._driver = None
                logger.info("Disconnected")
            except Exception as e:
                logger.error(f"Disconnect error: {e}")
            finally:
                self._update_state(ConnectionState.DISCONNECTED)

    # ==================== 消息发送 ====================

    async def send_message(
        self,
        stream: int,
        function: int,
        items: List[SECSItem] = None,
        wait_reply: bool = True,
        timeout: Optional[float] = None,
    ) -> Optional[SECSMessage]:
        """
        发送 SECS 消息并等待回复

        Args:
            stream: Stream 编号
            function: Function 编号
            items: 消息数据项列表
            wait_reply: 是否等待回复
            timeout: 超时时间（秒）

        Returns:
            回复消息
        """
        if not self._driver or not self._driver.is_connected:
            logger.warning("Driver not connected")
            return None

        try:
            tx_preview = SECSMessage(
                stream=stream,
                function=function,
                w_bit=wait_reply,
                device_id=self._config.device_id,
                items=items or [],
            )
            logger.info(
                "TX\n%s",
                _format_message_standard(tx_preview),
            )
            reply = await self._driver.send_message(
                stream=stream,
                function=function,
                items=items,
                wait_reply=wait_reply,
                timeout=timeout,
            )
            if reply:
                logger.info("RX-REPLY\n%s", _format_message_standard(reply))
            return reply
        except Exception as e:
            logger.error(f"Send message error: {e}")
            self._invoke_callback(self._on_error, e)
            return None

    async def send_message_async(
        self,
        stream: int,
        function: int,
        items: List[SECSItem] = None,
        callback: Optional[Callable[[SECSMessage], None]] = None,
    ) -> None:
        """
        异步发送 SECS 消息

        Args:
            stream: Stream 编号
            function: Function 编号
            items: 消息数据项列表
            callback: 回复回调函数
        """
        if not self._driver or not self._driver.is_connected:
            logger.warning("Driver not connected")
            return

        try:
            logger.info("TX-ASYNC S%sF%s", stream, function)
            await self._driver.send_message_async(
                stream=stream,
                function=function,
                items=items,
                callback=callback,
            )
        except Exception as e:
            logger.error(f"Send async message error: {e}")
            self._invoke_callback(self._on_error, e)

    async def send_reply(
        self,
        original_message: SECSMessage,
        items: List[SECSItem] = None,
    ) -> bool:
        """
        发送回复消息

        Args:
            original_message: 原消息
            items: 回复数据项列表

        Returns:
            是否发送成功
        """
        if not self._driver:
            return False

        try:
            preview_reply = original_message.create_reply(items)
            logger.info(
                "TX-REPLY for %s\n%s",
                original_message.sf,
                _format_message_standard(preview_reply),
            )
            return await self._driver.send_reply(original_message, items)
        except Exception as e:
            logger.error(f"Send reply error: {e}")
            self._invoke_callback(self._on_error, e)
            return False

    # ==================== 状态查询 ====================

    @property
    def state(self) -> ConnectionState:
        """获取连接状态"""
        return self._state

    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._driver is not None and self._driver.is_connected

    @property
    def is_selected(self) -> bool:
        """检查会话是否已选中"""
        return self._state == ConnectionState.SELECTED

    @property
    def driver(self) -> Optional[SECSDriver]:
        """获取底层 Driver（谨慎使用）"""
        return self._driver
