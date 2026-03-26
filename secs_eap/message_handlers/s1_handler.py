"""
S1 系列消息处理器

S1: Communications
"""

import asyncio
import logging
from typing import Dict, Any
from datetime import datetime

from secs_driver.src.secs_message import SECSMessage, SECSItem, SECSItem as Item
from secs_driver.src.secs_types import SECSType

from .base_handler import BaseMessageHandler, HandlerResult, HandlerPriority
from ..driver_adapter import DriverAdapter


logger = logging.getLogger(__name__)


class S1F1Handler(BaseMessageHandler):
    """S1F1 - Are You There (Request)"""

    def __init__(self, driver_adapter: DriverAdapter):
        super().__init__("S1F1Handler")
        self._driver_adapter = driver_adapter

    def can_handle(self, message: SECSMessage) -> bool:
        return message.stream == 1 and message.function == 1

    async def handle(self, message: SECSMessage, context: Dict[str, Any]) -> HandlerResult:
        """处理 S1F1 请求"""
        logger.info("Received S1F1: Are You There")

        # S1F2: On Line Data
        # MDLN: Model (6 chars)
        # SOFTREV: Software Revision (6 chars)
        mdln = Item.ascii("EAP001")
        softrev = Item.ascii("V1.0.0")

        return HandlerResult(
            success=True,
            message="S1F1 handled",
            reply_items=[mdln, softrev],
        )


class S1F3Handler(BaseMessageHandler):
    """S1F3 - Selected Equipment Status Request"""

    def __init__(self, driver_adapter: DriverAdapter):
        super().__init__("S1F3Handler")
        self._driver_adapter = driver_adapter

    def can_handle(self, message: SECSMessage) -> bool:
        return message.stream == 1 and message.function == 3

    async def handle(self, message: SECSMessage, context: Dict[str, Any]) -> HandlerResult:
        """处理 S1F3 请求"""
        logger.info("Received S1F3: Selected Equipment Status Request")

        # 从业务服务获取设备状态
        equipment_service = context.get("equipment_service")
        status_data = []

        if equipment_service:
            try:
                status_data = await equipment_service.get_status_data()
            except Exception as e:
                logger.error(f"Failed to get status data: {e}")

        return HandlerResult(
            success=True,
            message="S1F3 handled",
            reply_items=status_data,
        )


class S1F13Handler(BaseMessageHandler):
    """S1F13 - Establish Communications Request"""

    def __init__(self, driver_adapter: DriverAdapter):
        super().__init__("S1F13Handler")
        self._driver_adapter = driver_adapter

    def can_handle(self, message: SECSMessage) -> bool:
        return message.stream == 1 and message.function == 13

    async def handle(self, message: SECSMessage, context: Dict[str, Any]) -> HandlerResult:
        """处理 S1F13 请求"""
        logger.info("Received S1F13: Establish Communications Request")

        # 解析请求数据
        comm_state = 0  # 0 = Communications OK
        status = 0  # 0 = OK, 1 = Not OK

        if message.items:
            try:
                if len(message.items) > 0 and message.items[0].type == SECSType.UINT1:
                    comm_state = message.items[0].value or 0
                if len(message.items) > 1 and message.items[1].type == SECSType.UINT1:
                    status = message.items[1].value or 0
            except Exception as e:
                logger.error(f"Failed to parse S1F13 data: {e}")

        # 保存会话信息
        context["comm_state"] = comm_state

        # S1F14: Establish Communications Request Acknowledge
        # COMMACK: Communications Acknowledge (0 = Accept, 1 = Reject)
        # MDLN: Model (6 chars)
        # SOFTREV: Software Revision (6 chars)
        commack = Item.uint1(0)  # Accept
        mdln = Item.ascii("EAP001")
        softrev = Item.ascii("V1.0.0")

        return HandlerResult(
            success=True,
            message="S1F13 handled",
            reply_items=[commack, mdln, softrev],
        )


class S1F17Handler(BaseMessageHandler):
    """S1F17 - Request Off-Line"""

    def __init__(self, driver_adapter: DriverAdapter):
        super().__init__("S1F17Handler")
        self._driver_adapter = driver_adapter

    def can_handle(self, message: SECSMessage) -> bool:
        return message.stream == 1 and message.function == 17

    async def handle(self, message: SECSMessage, context: Dict[str, Any]) -> HandlerResult:
        """处理 S1F17 请求"""
        logger.info("Received S1F17: Request Off-Line")

        # 更新设备状态
        equipment_service = context.get("equipment_service")
        if equipment_service:
            try:
                await equipment_service.set_online_status(False)
            except Exception as e:
                logger.error(f"Failed to set offline status: {e}")

        # S1F18: Request Off-Line Acknowledge
        # OFLACK: Off-Line Acknowledge (0 = OK, 1 = Deny)
        oflack = Item.uint1(0)  # OK

        return HandlerResult(
            success=True,
            message="S1F17 handled",
            reply_items=[oflack],
        )


class S1HandlerManager(BaseMessageHandler):
    """
    S1 系列消息管理器

    统一管理 S1 系列消息处理器，按优先级分发。
    """

    def __init__(self, driver_adapter: DriverAdapter):
        super().__init__("S1HandlerManager")
        self._priority = HandlerPriority.HIGH

        # 创建具体的处理器
        self._s1f1 = S1F1Handler(driver_adapter)
        self._s1f3 = S1F3Handler(driver_adapter)
        self._s1f13 = S1F13Handler(driver_adapter)
        self._s1f17 = S1F17Handler(driver_adapter)

        # S-F 到处理器的映射
        self._handler_map = {
            (1, 1): self._s1f1,
            (1, 3): self._s1f3,
            (1, 13): self._s1f13,
            (1, 17): self._s1f17,
        }

    def can_handle(self, message: SECSMessage) -> bool:
        return message.stream == 1

    async def handle(self, message: SECSMessage, context: Dict[str, Any]) -> HandlerResult:
        """根据具体的 Function 分发到对应的处理器"""
        handler = self._handler_map.get((message.stream, message.function))

        if handler is None:
            logger.warning(f"No handler for S1F{message.function}")
            return HandlerResult(
                success=False,
                message=f"No handler for S1F{message.function}",
            )

        return await handler.handle(message, context)

    def register_handlers(self, registry) -> None:
        """注册所有 S1 处理器"""
        registry.register(self._s1f1, stream=1, function=1)
        registry.register(self._s1f3, stream=1, function=3)
        registry.register(self._s1f13, stream=1, function=13)
        registry.register(self._s1f17, stream=1, function=17)
