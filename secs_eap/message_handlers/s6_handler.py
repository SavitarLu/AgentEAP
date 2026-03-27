"""
S6 系列消息处理器

S6: Data Collection
"""

import logging
from typing import Dict, Any

from secs_driver.src.secs_message import SECSMessage, SECSItem

from .base_handler import BaseMessageHandler, HandlerResult, StreamHandlerManager


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
    """S6F11 - Event Report Send"""

    def __init__(self):
        super().__init__("S6F11Handler")

    def can_handle(self, message: SECSMessage) -> bool:
        return message.stream == 6 and message.function == 11

    async def handle(self, message: SECSMessage, context: Dict[str, Any]) -> HandlerResult:
        """处理 S6F11"""
        logger.info("Received S6F11: Event Report Send")

        event_payload = None
        data_service = context.get("data_collection_service")
        if data_service:
            try:
                event_payload = await data_service.report_collection_event(message)
            except Exception as e:
                logger.error(f"Failed to parse collection event: {e}")

        if event_payload:
            event_data = event_payload.to_dict()
            context["collection_event"] = event_data
            context["collection_event_payload"] = event_payload
            context["last_collection_event"] = event_data
            logger.info(
                "Resolved S6F11 event: ceid=%s name=%s reports=%d fields=%s",
                event_data["ceid"],
                event_data["name"],
                len(event_data["reports"]),
                list(event_data["fields"].keys()),
            )
        else:
            context.pop("collection_event", None)
            context.pop("collection_event_payload", None)

        return HandlerResult(
            success=True,
            message="S6F11 handled",
            reply_items=[],
            data=event_payload.to_dict() if event_payload else None,
        )


class S6HandlerManager(StreamHandlerManager):
    """S6 系列消息管理器"""

    def __init__(self):
        self._s6f1 = S6F1Handler()
        self._s6f3 = S6F3Handler()
        self._s6f5 = S6F5Handler()
        self._s6f11 = S6F11Handler()
        super().__init__(
            "S6HandlerManager",
            stream=6,
            handler_map={
                (6, 1): self._s6f1,
                (6, 3): self._s6f3,
                (6, 5): self._s6f5,
                (6, 11): self._s6f11,
            },
        )
