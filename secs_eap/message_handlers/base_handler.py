"""
消息处理器基类

定义消息处理器的接口和通用功能。
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Callable, Any
from dataclasses import dataclass
from enum import Enum

from secs_driver.src.secs_message import SECSMessage, SECSItem


logger = logging.getLogger(__name__)


class HandlerPriority(Enum):
    """处理器优先级"""

    HIGH = 1  # 高优先级，先处理
    NORMAL = 2  # 普通优先级
    LOW = 3  # 低优先级，后处理


@dataclass
class HandlerResult:
    """处理器结果"""

    success: bool
    message: Optional[str] = None
    reply_items: List[SECSItem] = None
    data: Any = None


class BaseMessageHandler(ABC):
    """
    消息处理器基类

    所有具体的消息处理器都应继承此类。
    """

    def __init__(self, name: str = None):
        """
        初始化消息处理器

        Args:
            name: 处理器名称
        """
        self._name = name or self.__class__.__name__
        self._enabled = True
        self._priority = HandlerPriority.NORMAL

    @property
    def name(self) -> str:
        """获取处理器名称"""
        return self._name

    @property
    def priority(self) -> HandlerPriority:
        """获取处理器优先级"""
        return self._priority

    @priority.setter
    def priority(self, value: HandlerPriority) -> None:
        """设置处理器优先级"""
        self._priority = value

    @property
    def enabled(self) -> bool:
        """是否启用"""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """设置启用状态"""
        self._enabled = value

    @abstractmethod
    def can_handle(self, message: SECSMessage) -> bool:
        """
        判断此处理器是否可以处理该消息

        Args:
            message: SECS 消息

        Returns:
            是否可以处理
        """
        pass

    @abstractmethod
    async def handle(
        self,
        message: SECSMessage,
        context: Dict[str, Any],
    ) -> HandlerResult:
        """
        处理消息

        Args:
            message: SECS 消息
            context: 上下文信息（包含 driver_adapter 等）

        Returns:
            处理结果
        """
        pass

    async def on_message(self, message: SECSMessage, context: Dict[str, Any]) -> HandlerResult:
        """
        消息处理入口

        如果处理器未启用，返回失败。
        子类可以重写此方法添加预处理逻辑。

        Args:
            message: SECS 消息
            context: 上下文信息

        Returns:
            处理结果
        """
        if not self._enabled:
            return HandlerResult(
                success=False,
                message=f"Handler {self._name} is disabled",
            )

        try:
            return await self.handle(message, context)
        except Exception as e:
            logger.exception(f"Handler {self._name} error: {e}")
            return HandlerResult(
                success=False,
                message=str(e),
            )

    def __repr__(self) -> str:
        return f"{self._name}(priority={self._priority.name}, enabled={self._enabled})"


class MessageHandlerRegistry:
    """
    消息处理器注册表

    管理所有消息处理器，提供消息分发功能。
    """

    def __init__(self):
        self._handlers: Dict[str, List[BaseMessageHandler]] = {}  # key: "S{n}F{m}"
        self._stream_handlers: Dict[int, List[BaseMessageHandler]] = {}  # stream -> handlers
        self._default_handlers: List[BaseMessageHandler] = []

    def register(
        self,
        handler: BaseMessageHandler,
        stream: int = None,
        function: int = None,
    ) -> None:
        """
        注册消息处理器

        Args:
            handler: 消息处理器
            stream: 指定的 Stream 编号（可选）
            function: 指定的 Function 编号（可选）
        """
        if stream is not None and function is not None:
            # 注册到特定的 S-F
            key = f"S{stream}F{function}"
            if key not in self._handlers:
                self._handlers[key] = []
            self._handlers[key].append(handler)
            logger.debug(f"Registered handler {handler.name} for {key}")
        elif stream is not None:
            # 注册到整个 Stream
            if stream not in self._stream_handlers:
                self._stream_handlers[stream] = []
            self._stream_handlers[stream].append(handler)
            logger.debug(f"Registered handler {handler.name} for S{stream}*")
        else:
            # 注册为默认处理器
            self._default_handlers.append(handler)
            logger.debug(f"Registered handler {handler.name} as default")

        # 按优先级排序
        self._sort_handlers()

    def unregister(self, handler: BaseMessageHandler) -> None:
        """注销处理器"""
        # 从 S-F 映射中移除
        for key in list(self._handlers.keys()):
            if handler in self._handlers[key]:
                self._handlers[key].remove(handler)
            if not self._handlers[key]:
                del self._handlers[key]

        # 从 Stream 映射中移除
        for stream in list(self._stream_handlers.keys()):
            if handler in self._stream_handlers[stream]:
                self._stream_handlers[stream].remove(handler)
            if not self._stream_handlers[stream]:
                del self._stream_handlers[stream]

        # 从默认处理器中移除
        if handler in self._default_handlers:
            self._default_handlers.remove(handler)

    def _sort_handlers(self) -> None:
        """对所有处理器按优先级排序"""
        all_handler_lists = [
            self._handlers,
            {k: v for k, v in self._stream_handlers.items()},
            {"_default": self._default_handlers},
        ]

        for handler_dict in all_handler_lists:
            for key in handler_dict:
                handler_dict[key].sort(key=lambda h: h.priority.value)

    def find_handlers(self, message: SECSMessage) -> List[BaseMessageHandler]:
        """
        查找可以处理该消息的处理器

        Args:
            message: SECS 消息

        Returns:
            处理器列表（按优先级排序）
        """
        result: List[BaseMessageHandler] = []

        # 1. 查找精确匹配的 S-F 处理器
        key = f"S{message.stream}F{message.function}"
        if key in self._handlers:
            result.extend(self._handlers[key])

        # 2. 查找 Stream 级别的处理器
        if message.stream in self._stream_handlers:
            for handler in self._stream_handlers[message.stream]:
                if handler not in result:
                    result.append(handler)

        # 3. 查找默认处理器
        for handler in self._default_handlers:
            if handler not in result:
                result.append(handler)

        # 4. 过滤掉不能处理的处理器
        result = [h for h in result if h.can_handle(message)]

        return result

    async def dispatch(
        self,
        message: SECSMessage,
        context: Dict[str, Any],
    ) -> Optional[HandlerResult]:
        """
        分发消息给处理器

        Args:
            message: SECS 消息
            context: 上下文信息

        Returns:
            处理结果（如果有）
        """
        handlers = self.find_handlers(message)

        if not handlers:
            logger.warning(f"No handler for message: {message.sf}")
            return None

        # 按优先级执行处理器
        for handler in handlers:
            logger.debug(f"Dispatching {message.sf} to {handler.name}")
            result = await handler.on_message(message, context)

            if result.success:
                logger.debug(f"{handler.name} handled {message.sf}: {result.message}")
                return result

        logger.warning(f"All handlers failed for {message.sf}")
        return HandlerResult(success=False, message="No handler processed the message")

    def get_handler_count(self) -> int:
        """获取已注册的处理器数量"""
        count = len(self._default_handlers)
        for handlers in self._handlers.values():
            count += len(handlers)
        for handlers in self._stream_handlers.values():
            count += len(handlers)
        return count
