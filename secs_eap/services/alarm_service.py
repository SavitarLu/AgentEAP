"""
报警服务

管理设备报警的提交、确认、列表查询等。
"""

import asyncio
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
from enum import Enum

from secs_driver.src.secs_message import SECSItem


logger = logging.getLogger(__name__)


class AlarmSeverity(Enum):
    """报警严重程度"""

    INFO = 0x00
    WARN = 0x20
    ERROR = 0x40
    FATAL = 0x60


@dataclass
class Alarm:
    """报警信息"""

    alarm_id: int
    alarm_code: int
    alarm_text: str
    severity: AlarmSeverity
    set_time: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
    cleared: bool = False
    clear_time: Optional[datetime] = None

    @property
    def is_active(self) -> bool:
        """是否激活"""
        return not self.cleared

    def to_secs_format(self) -> SECSItem:
        """转换为 SECS 格式"""
        # ALID (4 bytes), ALCD (1 byte), ALTX (up to 120 chars)
        alarm_id_bytes = self.alarm_id.to_bytes(4, byteorder='big')
        alarm_code_byte = bytes([self.alarm_code])

        return SECSItem.list_([
            SECSItem.binary(alarm_id_bytes),
            SECSItem.binary(alarm_code_byte),
            SECSItem.ascii(self.alarm_text[:120]),
        ])


class AlarmService:
    """
    报警服务

    提供：
    - 报警提交
    - 报警确认
    - 报警清除
    - 当前报警列表查询
    - 报警历史记录
    """

    def __init__(self, history_size: int = 1000):
        self._history_size = history_size

        # 当前激活的报警
        self._active_alarms: Dict[int, Alarm] = {}

        # 报警历史 (环形缓冲区)
        self._alarm_history: deque = deque(maxlen=history_size)

        # 报警使能状态
        self._alarm_enabled: Dict[int, bool] = {}

        # 事件回调
        self._on_alarm_set: Optional[callable] = None
        self._on_alarm_cleared: Optional[callable] = None

    def set_callbacks(
        self,
        on_alarm_set: Optional[callable] = None,
        on_alarm_cleared: Optional[callable] = None,
    ) -> None:
        """设置回调函数"""
        self._on_alarm_set = on_alarm_set
        self._on_alarm_cleared = on_alarm_cleared

    async def report_alarm(self, alarm) -> bool:
        """
        报告报警

        Args:
            alarm: AlarmInfo 或 Alarm 对象

        Returns:
            是否成功
        """
        try:
            # 转换为内部格式
            if hasattr(alarm, 'alarm_id'):
                alarm_obj = Alarm(
                    alarm_id=alarm.alarm_id,
                    alarm_code=alarm.alarm_code,
                    alarm_text=alarm.alarm_text,
                    severity=AlarmSeverity[alarm.severity] if hasattr(alarm, 'severity') else AlarmSeverity.ERROR,
                    set_time=getattr(alarm, 'occurred_at', datetime.now()),
                )
            else:
                alarm_obj = alarm

            # 检查是否已存在
            if alarm_obj.alarm_id in self._active_alarms:
                logger.debug(f"Alarm {alarm_obj.alarm_id} already active")
                return True

            # 添加到激活列表
            self._active_alarms[alarm_obj.alarm_id] = alarm_obj

            # 添加到历史
            self._alarm_history.append(alarm_obj)

            logger.info(
                f"Alarm SET: ID={alarm_obj.alarm_id}, "
                f"CODE={alarm_obj.alarm_code:02X}, "
                f"TEXT={alarm_obj.alarm_text}"
            )

            # 触发回调
            if self._on_alarm_set:
                await self._on_alarm_set(alarm_obj)

            return True

        except Exception as e:
            logger.error(f"Failed to report alarm: {e}")
            return False

    async def clear_alarm(self, alarm_id: int) -> bool:
        """
        清除报警

        Args:
            alarm_id: 报警 ID

        Returns:
            是否成功
        """
        if alarm_id not in self._active_alarms:
            logger.warning(f"Alarm {alarm_id} not active")
            return False

        alarm = self._active_alarms[alarm_id]
        alarm.cleared = True
        alarm.clear_time = datetime.now()

        # 从激活列表移除
        del self._active_alarms[alarm_id]

        logger.info(f"Alarm CLEARED: ID={alarm_id}")

        # 触发回调
        if self._on_alarm_cleared:
            await self._on_alarm_cleared(alarm)

        return True

    async def acknowledge_alarm(self, alarm_id: int) -> bool:
        """
        确认报警

        Args:
            alarm_id: 报警 ID

        Returns:
            是否成功
        """
        if alarm_id not in self._active_alarms:
            return False

        self._active_alarms[alarm_id].acknowledged = True
        logger.info(f"Alarm ACKNOWLEDGED: ID={alarm_id}")
        return True

    async def set_alarm_enable(self, alarm_ids: List[int]) -> None:
        """
        设置报警使能

        Args:
            alarm_ids: 报警 ID 列表
        """
        for alarm_id in alarm_ids:
            self._alarm_enabled[alarm_id] = True
            logger.info(f"Alarm {alarm_id} enabled")

    async def set_alarm_disable(self, alarm_ids: List[int]) -> None:
        """
        设置报警禁止

        Args:
            alarm_ids: 报警 ID 列表
        """
        for alarm_id in alarm_ids:
            self._alarm_enabled[alarm_id] = False
            logger.info(f"Alarm {alarm_id} disabled")

    async def get_current_alarms(self) -> List[SECSItem]:
        """
        获取当前激活的报警列表 (S5F5/S5F6)

        Returns:
            报警列表的 SECSItem
        """
        alarms = []

        for alarm in self._active_alarms.values():
            alarms.append(alarm.to_secs_format())

        return [SECSItem.list_(alarms)] if alarms else [SECSItem.list_([])]

    async def get_alarm_history(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Alarm]:
        """
        获取报警历史

        Args:
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回数量限制

        Returns:
            报警列表
        """
        result = []

        for alarm in reversed(self._alarm_history):
            # 时间过滤
            if start_time and alarm.set_time < start_time:
                continue
            if end_time and alarm.set_time > end_time:
                continue

            result.append(alarm)

            if len(result) >= limit:
                break

        return result

    @property
    def active_alarm_count(self) -> int:
        """获取激活报警数量"""
        return len(self._active_alarms)

    def get_active_alarm_ids(self) -> List[int]:
        """获取激活报警 ID 列表"""
        return list(self._active_alarms.keys())

    async def generate_alarm_report(self) -> SECSItem:
        """
        生成报警报告 (S5F1 格式)

        Returns:
            报警报告数据
        """
        return SECSItem.list_(await self.get_current_alarms())
