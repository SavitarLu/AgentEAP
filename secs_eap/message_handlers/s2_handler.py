"""
S2 系列消息处理器

S2: Equipment Control
"""

import logging
from typing import Dict, Any
from datetime import datetime

from secs_driver.src.secs_message import SECSMessage, SECSItem
from secs_driver.src.secs_types import SECSType

from .base_handler import BaseMessageHandler, HandlerResult, StreamHandlerManager
from ..usecases.s2f41_remote_command import S2F41RemoteCommandUseCase


logger = logging.getLogger(__name__)


class S2F1Handler(BaseMessageHandler):
    """S2F1 - Remote Command"""

    def __init__(self):
        super().__init__("S2F1Handler")

    def can_handle(self, message: SECSMessage) -> bool:
        return message.stream == 2 and message.function == 1

    async def handle(self, message: SECSMessage, context: Dict[str, Any]) -> HandlerResult:
        """处理 S2F1 远程命令"""
        logger.info("Received S2F1: Remote Command")

        # 解析命令数据
        command = None
        if message.items:
            try:
                cmd_item = message.items[0]
                if cmd_item.type == SECSType.LIST and cmd_item.children:
                    command = self._parse_command(cmd_item)
            except Exception as e:
                logger.error(f"Failed to parse S2F1 command: {e}")

        # 从业务服务执行命令
        equipment_service = context.get("equipment_service")
        if equipment_service and command:
            try:
                result = await equipment_service.execute_command(command)
                return HandlerResult(
                    success=True,
                    message=f"Command executed: {command}",
                    data=result,
                )
            except Exception as e:
                logger.error(f"Failed to execute command: {e}")
                return HandlerResult(
                    success=False,
                    message=f"Command failed: {e}",
                )

        # 默认拒绝执行
        return HandlerResult(
            success=True,
            message="Command acknowledged (no execution)",
            reply_items=[SECSItem.uint1(0)],  # ACKC2: 0 = Command accepted
        )

    def _parse_command(self, cmd_item) -> Dict:
        """解析命令数据"""
        command = {"type": None, "params": []}

        try:
            if len(cmd_item.children) > 0:
                cmd_type = cmd_item.children[0]
                if cmd_type.type == SECSType.ASCII:
                    command["type"] = cmd_type.value
                elif cmd_type.type == SECSType.UINT1:
                    command["type"] = chr(cmd_type.value)

            for i in range(1, len(cmd_item.children)):
                command["params"].append(cmd_item.children[i])
        except Exception:
            pass

        return command


class S2F13Handler(BaseMessageHandler):
    """S2F13 - Glass Transfer Parameter Setting"""

    def __init__(self):
        super().__init__("S2F13Handler")

    def can_handle(self, message: SECSMessage) -> bool:
        return message.stream == 2 and message.function == 13

    async def handle(self, message: SECSMessage, context: Dict[str, Any]) -> HandlerResult:
        """处理 S2F13"""
        logger.info("Received S2F13: Glass Transfer Parameter Setting")

        # 解析参数
        params = []
        if message.items:
            for item in message.items:
                params.append(item)

        # 保存到上下文
        context["transfer_params"] = params

        return HandlerResult(
            success=True,
            message="S2F13 handled",
            reply_items=[SECSItem.uint1(0)],  # ACKC13
        )


class S2F17Handler(BaseMessageHandler):
    """S2F17 - Date/Time Request"""

    def __init__(self):
        super().__init__("S2F17Handler")

    def can_handle(self, message: SECSMessage) -> bool:
        return message.stream == 2 and message.function == 17

    async def handle(self, message: SECSMessage, context: Dict[str, Any]) -> HandlerResult:
        """处理 S2F17 时间请求"""
        logger.info("Received S2F17: Date/Time Request")

        # 获取当前时间
        now = datetime.now()
        time_str = now.strftime("%Y%m%d%H%M%S")

        # S2F18: Date/Time Data
        # TIMEDATE: YYYYMMDDHHMMSS
        time_data = SECSItem.ascii(time_str)

        return HandlerResult(
            success=True,
            message="S2F17 handled",
            reply_items=[time_data],
        )


class S2F29Handler(BaseMessageHandler):
    """S2F29 - Variable Attribute Request"""

    def __init__(self):
        super().__init__("S2F29Handler")

    def can_handle(self, message: SECSMessage) -> bool:
        return message.stream == 2 and message.function == 29

    async def handle(self, message: SECSMessage, context: Dict[str, Any]) -> HandlerResult:
        """处理 S2F29"""
        logger.info("Received S2F29: Variable Attribute Request")

        # 从设备服务获取变量属性
        equipment_service = context.get("equipment_service")
        attributes = []

        if equipment_service:
            try:
                attributes = await equipment_service.get_variable_attributes()
            except Exception as e:
                logger.error(f"Failed to get variable attributes: {e}")

        return HandlerResult(
            success=True,
            message="S2F29 handled",
            reply_items=attributes,
        )


class S2F31Handler(BaseMessageHandler):
    """S2F31 - Date/Time Set Request"""

    def __init__(self):
        super().__init__("S2F31Handler")

    def can_handle(self, message: SECSMessage) -> bool:
        return message.stream == 2 and message.function == 31

    async def handle(self, message: SECSMessage, context: Dict[str, Any]) -> HandlerResult:
        """处理 S2F31 时间设置"""
        logger.info("Received S2F31: Date/Time Set Request")

        # 解析时间
        new_time = None
        if message.items:
            try:
                time_item = message.items[0]
                if time_item.type == SECSType.ASCII:
                    new_time = time_item.value
                    logger.info(f"Setting time to: {new_time}")
            except Exception as e:
                logger.error(f"Failed to parse S2F31 time: {e}")

        # 应用时间设置
        equipment_service = context.get("equipment_service")
        if equipment_service and new_time:
            try:
                await equipment_service.set_date_time(new_time)
            except Exception as e:
                logger.error(f"Failed to set date/time: {e}")

        # S2F32: Date/Time Set Acknowledge
        return HandlerResult(
            success=True,
            message="S2F31 handled",
            reply_items=[SECSItem.uint1(0)],  # TIAACK: 0 = OK
        )


class S2F41Handler(BaseMessageHandler):
    """S2F41 - Host Command Send (template style)"""

    def __init__(self):
        super().__init__("S2F41Handler")
        self._usecase = S2F41RemoteCommandUseCase()

    def can_handle(self, message: SECSMessage) -> bool:
        return message.stream == 2 and message.function == 41

    async def handle(self, message: SECSMessage, context: Dict[str, Any]) -> HandlerResult:
        logger.info("Received S2F41: Host Command Send")
        request = self._usecase.parse(message)
        result = await self._usecase.execute(request, context)
        reply_items = self._usecase.build_reply(result)
        return HandlerResult(
            success=True,
            message=f"S2F41 handled, HCACK={result.hcack}, reason={result.reason}",
            reply_items=reply_items,
            data={"rcmd": request.rcmd, "params": request.params, "reason": result.reason},
        )


class S2HandlerManager(StreamHandlerManager):
    """S2 系列消息管理器"""

    def __init__(self):
        self._s2f1 = S2F1Handler()
        self._s2f13 = S2F13Handler()
        self._s2f17 = S2F17Handler()
        self._s2f29 = S2F29Handler()
        self._s2f31 = S2F31Handler()
        self._s2f41 = S2F41Handler()
        super().__init__(
            "S2HandlerManager",
            stream=2,
            handler_map={
                (2, 1): self._s2f1,
                (2, 13): self._s2f13,
                (2, 17): self._s2f17,
                (2, 29): self._s2f29,
                (2, 31): self._s2f31,
                (2, 41): self._s2f41,
            },
        )
