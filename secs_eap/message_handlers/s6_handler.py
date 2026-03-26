"""
S6 系列消息处理器

S6: Data Collection
"""

import logging
from typing import Dict, Any, List

from secs_driver.src.secs_message import SECSMessage, SECSItem
from secs_driver.src.secs_types import SECSType

from .base_handler import BaseMessageHandler, HandlerResult, HandlerPriority


logger = logging.getLogger(__name__)


class S6F1Handler(BaseMessageHandler):
    """S6F1 - Data Collection"""

    def __init__(self):
        super().__init__("S6F1Handler")

    def can_handle(self, message: SECSMessage) -> bool:
        return message.stream == 6 and message.function == 1

    async def handle(self, message: SECSMessage, context: Dict[str, Any]) -> HandlerResult:
        """处理 S6F1 数据收集"""
        logger.info("Received S6F1: Data Collection")

        # 解析数据
        data_items = []
        for item in message.items:
            data_items.append(item)

        # 保存到上下文
        context["collected_data"] = data_items

        # 发送到数据收集服务
        data_service = context.get("data_collection_service")
        if data_service:
            try:
                await data_service.collect_data(data_items)
            except Exception as e:
                logger.error(f"Failed to collect data: {e}")

        return HandlerResult(
            success=True,
            message=f"S6F1 handled, collected {len(data_items)} items",
            data=data_items,
        )


class S6F3Handler(BaseMessageHandler):
    """S6F3 - Date/Time Variable Data Request"""

    def __init__(self):
        super().__init__("S6F3Handler")

    def can_handle(self, message: SECSMessage) -> bool:
        return message.stream == 6 and message.function == 3

    async def handle(self, message: SECSMessage, context: Dict[str, Any]) -> HandlerResult:
        """处理 S6F3"""
        logger.info("Received S6F3: Date/Time Variable Data Request")

        # 从数据收集服务获取数据
        data_service = context.get("data_collection_service")
        data = []

        if data_service:
            try:
                data = await data_service.get_date_time_data()
            except Exception as e:
                logger.error(f"Failed to get date/time data: {e}")

        return HandlerResult(
            success=True,
            message="S6F3 handled",
            reply_items=data,
        )


class S6F5Handler(BaseMessageHandler):
    """S6F5 - Variable Collection Request"""

    def __init__(self):
        super().__init__("S6F5Handler")

    def can_handle(self, message: SECSMessage) -> bool:
        return message.stream == 6 and message.function == 5

    async def handle(self, message: SECSMessage, context: Dict[str, Any]) -> HandlerResult:
        """处理 S6F5 变量收集请求"""
        logger.info("Received S6F5: Variable Collection Request")

        # 解析请求的变量列表
        var_requests = []
        if message.items:
            for item in message.items:
                if item.value is not None:
                    var_requests.append(item.value)

        # 从数据收集服务获取变量数据
        data_service = context.get("data_collection_service")
        data = []

        if data_service:
            try:
                data = await data_service.get_variable_data(var_requests)
            except Exception as e:
                logger.error(f"Failed to get variable data: {e}")

        return HandlerResult(
            success=True,
            message="S6F6 handled",
            reply_items=data,
        )


class S6F11Handler(BaseMessageHandler):
    """S6F11 - Process Program Load Request"""

    def __init__(self):
        super().__init__("S6F11Handler")

    def can_handle(self, message: SECSMessage) -> bool:
        return message.stream == 6 and message.function == 11

    async def handle(self, message: SECSMessage, context: Dict[str, Any]) -> HandlerResult:
        """处理 S6F11"""
        logger.info("Received S6F11: Process Program Load Request")

        return HandlerResult(
            success=True,
            message="S6F11 handled (recipe logic removed)",
            reply_items=[],
        )


class S6HandlerManager(BaseMessageHandler):
    """S6 系列消息管理器"""

    def __init__(self):
        super().__init__("S6HandlerManager")
        self._priority = HandlerPriority.HIGH

        # 创建具体的处理器
        self._s6f1 = S6F1Handler()
        self._s6f3 = S6F3Handler()
        self._s6f5 = S6F5Handler()
        self._s6f11 = S6F11Handler()

        # S-F 到处理器的映射
        self._handler_map = {
            (6, 1): self._s6f1,
            (6, 3): self._s6f3,
            (6, 5): self._s6f5,
            (6, 11): self._s6f11,
        }

    def can_handle(self, message: SECSMessage) -> bool:
        return message.stream == 6

    async def handle(self, message: SECSMessage, context: Dict[str, Any]) -> HandlerResult:
        """分发到对应的处理器"""
        handler = self._handler_map.get((message.stream, message.function))

        if handler is None:
            logger.warning(f"No handler for S6F{message.function}")
            return HandlerResult(
                success=False,
                message=f"No handler for S6F{message.function}",
            )

        return await handler.handle(message, context)

    def register_handlers(self, registry) -> None:
        """注册所有 S6 处理器"""
        registry.register(self._s6f1, stream=6, function=1)
        registry.register(self._s6f3, stream=6, function=3)
        registry.register(self._s6f5, stream=6, function=5)
        registry.register(self._s6f11, stream=6, function=11)
