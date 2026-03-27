"""
S5 系列消息处理器

S5: Alarm Management
"""

import logging
from typing import Dict, Any
from dataclasses import dataclass
from datetime import datetime

from secs_driver.src.secs_message import SECSMessage, SECSItem
from secs_driver.src.secs_types import SECSType

from .base_handler import BaseMessageHandler, HandlerResult, StreamHandlerManager


logger = logging.getLogger(__name__)


@dataclass
class AlarmInfo:
    """报警信息"""

    alarm_id: int
    alarm_code: int
    alarm_text: str
    severity: str = "WARN"  # INFO, WARN, ERROR, FATAL
    occurred_at: datetime = None

    def __post_init__(self):
        if self.occurred_at is None:
            self.occurred_at = datetime.now()


class S5F1Handler(BaseMessageHandler):
    """S5F1 - Alarm Report"""

    def __init__(self):
        super().__init__("S5F1Handler")

    def can_handle(self, message: SECSMessage) -> bool:
        return message.stream == 5 and message.function == 1

    async def handle(self, message: SECSMessage, context: Dict[str, Any]) -> HandlerResult:
        """处理 S5F1 报警报告"""
        logger.info("Received S5F1: Alarm Report")

        # 解析报警数据
        alarms = self._parse_alarms(message)

        # 发送到报警服务处理
        alarm_service = context.get("alarm_service")
        if alarm_service:
            try:
                for alarm in alarms:
                    await alarm_service.report_alarm(alarm)
                logger.info(f"Reported {len(alarms)} alarm(s)")
            except Exception as e:
                logger.error(f"Failed to report alarms: {e}")

        return HandlerResult(
            success=True,
            message=f"S5F1 handled, {len(alarms)} alarm(s) reported",
            data=alarms,
        )

    def _parse_alarms(self, message: SECSMessage) -> list:
        """解析报警数据"""
        alarms = []

        for item in message.items:
            if item.type != SECSType.LIST:
                continue

            try:
                alarm_id = 0
                alarm_code = 0
                alarm_text = ""

                # ALID: Alarm ID (4 bytes)
                if len(item.children) > 0 and item.children[0].value:
                    val = item.children[0].value
                    if isinstance(val, (int, bytes)):
                        alarm_id = int.from_bytes(
                            val.to_bytes(4, 'big') if isinstance(val, int) else val[:4],
                            byteorder='big'
                        )

                # ALCD: Alarm Code (1 byte)
                if len(item.children) > 1 and item.children[1].value is not None:
                    alarm_code = item.children[1].value
                    if isinstance(alarm_code, bytes):
                        alarm_code = alarm_code[0] if alarm_code else 0

                # ALTX: Alarm Text (up to 120 chars)
                if len(item.children) > 2 and item.children[2].value:
                    alarm_text = item.children[2].value

                # 判断报警/解除
                if alarm_code & 0x80:  # Set bit indicates alarm set
                    severity = "ERROR"
                else:
                    severity = "INFO"

                alarms.append(AlarmInfo(
                    alarm_id=alarm_id,
                    alarm_code=alarm_code,
                    alarm_text=alarm_text,
                    severity=severity,
                ))

            except Exception as e:
                logger.error(f"Failed to parse alarm item: {e}")

        return alarms


class S5F3Handler(BaseMessageHandler):
    """S5F3 - Alarm Enable/Disable Request"""

    def __init__(self):
        super().__init__("S5F3Handler")

    def can_handle(self, message: SECSMessage) -> bool:
        return message.stream == 5 and message.function == 3

    async def handle(self, message: SECSMessage, context: Dict[str, Any]) -> HandlerResult:
        """处理 S5F3"""
        logger.info("Received S5F3: Alarm Enable/Disable Request")

        # 解析请求
        alarm_ids = []
        if message.items:
            for item in message.items:
                if item.value:
                    alarm_ids.append(item.value)

        # 应用设置
        alarm_service = context.get("alarm_service")
        if alarm_service:
            try:
                await alarm_service.set_alarm_enable(alarm_ids)
            except Exception as e:
                logger.error(f"Failed to set alarm enable: {e}")

        return HandlerResult(
            success=True,
            message="S5F3 handled",
        )


class S5F5Handler(BaseMessageHandler):
    """S5F5 - Alarm List Request"""

    def __init__(self):
        super().__init__("S5F5Handler")

    def can_handle(self, message: SECSMessage) -> bool:
        return message.stream == 5 and message.function == 5

    async def handle(self, message: SECSMessage, context: Dict[str, Any]) -> HandlerResult:
        """处理 S5F5 报警列表请求"""
        logger.info("Received S5F5: Alarm List Request")

        # 从报警服务获取当前报警列表
        alarm_service = context.get("alarm_service")
        alarm_list = []

        if alarm_service:
            try:
                alarm_list = await alarm_service.get_current_alarms()
            except Exception as e:
                logger.error(f"Failed to get alarm list: {e}")

        return HandlerResult(
            success=True,
            message="S5F5 handled",
            reply_items=alarm_list,
        )


class S5HandlerManager(StreamHandlerManager):
    """S5 系列消息管理器"""

    def __init__(self):
        self._s5f1 = S5F1Handler()
        self._s5f3 = S5F3Handler()
        self._s5f5 = S5F5Handler()
        super().__init__(
            "S5HandlerManager",
            stream=5,
            handler_map={
                (5, 1): self._s5f1,
                (5, 3): self._s5f3,
                (5, 5): self._s5f5,
            },
        )
