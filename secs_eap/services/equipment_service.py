"""
设备服务

管理设备状态、变量、命令执行等。
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from secs_driver.src.secs_message import SECSItem


logger = logging.getLogger(__name__)


class EquipmentState(Enum):
    """设备状态"""

    INIT = "init"
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    OFFLINE = "offline"


@dataclass
class VariableInfo:
    """变量信息"""

    vid: int  # Variable ID
    name: str
    value: Any
    unit: str = ""
    data_type: str = "ASCII"


class EquipmentService:
    """
    设备服务

    提供：
    - 设备状态管理
    - 变量读写
    - 命令执行
    - 状态数据生成
    """

    def __init__(self):
        self._state = EquipmentState.INIT
        self._online = False
        self._variables: Dict[int, VariableInfo] = {}
        self._status_data_cache: List[SECSItem] = []

        # 初始化默认变量
        self._init_default_variables()

    def _init_default_variables(self) -> None:
        """初始化默认变量"""
        # 常用状态变量示例
        default_vars = [
            (1, "SFST", "1", "", "ASCII"),  # Equipment State
            (2, "SFSTNAME", "IDLE", "", "ASCII"),  # Equipment State Name
            (3, "OPID", "OPERATOR01", "", "ASCII"),  # Operator ID
            (4, "MID", "", "", "ASCII"),  # Carrier/Material ID
            (5, "PCTR", 0, "%", "UINT2"),  # Process Complete Time Remaining
            (6, "PPJRN", 0, "", "UINT1"),  # Process Job Running
            (7, "PPJQ", 0, "", "UINT1"),  # Process Job Queued
        ]

        for vid, name, value, unit, dtype in default_vars:
            self._variables[vid] = VariableInfo(
                vid=vid, name=name, value=value, unit=unit, data_type=dtype
            )

    @property
    def state(self) -> EquipmentState:
        """获取设备状态"""
        return self._state

    @property
    def is_online(self) -> bool:
        """是否在线"""
        return self._online

    async def set_state(self, new_state: EquipmentState) -> None:
        """设置设备状态"""
        if self._state != new_state:
            logger.info(f"Equipment state: {self._state.value} -> {new_state.value}")
            self._state = new_state
            await self._update_status_cache()

    async def set_online_status(self, online: bool) -> None:
        """设置在线状态"""
        self._online = online
        if not online:
            await self.set_state(EquipmentState.OFFLINE)
        await self._update_status_cache()

    async def get_status_data(self) -> List[SECSItem]:
        """
        获取状态数据

        返回 S1F3/S1F4 所需的状态数据列表。
        """
        await self._update_status_cache()
        return self._status_data_cache

    def _build_secs_item(self, data_type: str, value: Any) -> SECSItem:
        """按变量类型生成 SECSItem。"""
        if data_type == "ASCII":
            return SECSItem.ascii(str(value) if value is not None else "")
        if data_type == "UINT1":
            return SECSItem.uint1(int(value or 0))
        if data_type == "UINT2":
            return SECSItem.uint2(int(value or 0))
        if data_type == "UINT4":
            return SECSItem.uint4(int(value or 0))
        if data_type == "BINARY":
            return SECSItem.binary(value or b"")
        return SECSItem.ascii(str(value) if value is not None else "")

    async def _update_status_cache(self) -> None:
        """更新状态数据缓存"""
        self._status_data_cache = []

        for vid, var in sorted(self._variables.items()):
            try:
                self._status_data_cache.append(
                    self._build_secs_item(var.data_type, var.value)
                )
            except Exception as e:
                logger.error(f"Failed to format variable {var.name}: {e}")
                self._status_data_cache.append(SECSItem.ascii(""))

    def get_variable(self, vid: int) -> Optional[VariableInfo]:
        """获取变量"""
        return self._variables.get(vid)

    def set_variable(self, vid: int, value: Any) -> None:
        """设置变量"""
        if vid in self._variables:
            self._variables[vid].value = value
            logger.debug(f"Variable {self._variables[vid].name} = {value}")
        else:
            logger.warning(f"Unknown variable ID: {vid}")

    async def get_variable_data(self, vid_list: List[int]) -> List[SECSItem]:
        """
        获取变量数据

        Args:
            vid_list: Variable ID 列表

        Returns:
            变量值列表
        """
        result = []

        for vid in vid_list:
            var = self._variables.get(vid)
            if var:
                try:
                    result.append(self._build_secs_item(var.data_type, var.value))
                except Exception as e:
                    logger.error(f"Failed to format variable {vid}: {e}")
                    result.append(SECSItem.ascii(""))
            else:
                result.append(SECSItem.ascii(""))

        return result

    async def get_variable_attributes(self) -> List[SECSItem]:
        """
        获取变量属性 (S2F29/S2F30)

        Returns:
            变量属性列表
        """
        attrs = []

        for vid, var in sorted(self._variables.items()):
            try:
                # DVNAMA: Variable Name
                # DVID: Variable ID
                # UNIT: Unit
                # DVTYPE: Data Type
                attr = SECSItem.list_([
                    SECSItem.ascii(var.name),
                    SECSItem.uint2(var.vid),
                    SECSItem.ascii(var.unit),
                    SECSItem.ascii(var.data_type),
                ])
                attrs.append(attr)
            except Exception as e:
                logger.error(f"Failed to format attribute for {var.name}: {e}")

        return [SECSItem.list_(attrs)] if attrs else []

    async def execute_command(self, command: Dict) -> Dict[str, Any]:
        """
        执行远程命令

        Args:
            command: 命令信息，包含 type 和 params

        Returns:
            执行结果
        """
        cmd_type = command.get("type", "")
        params = command.get("params", [])

        logger.info(f"Executing command: {cmd_type}, params: {params}")

        result = {"success": False, "message": ""}

        # 根据命令类型执行
        if cmd_type in ("START", "RUN", "BEGIN"):
            await self.set_state(EquipmentState.RUNNING)
            result = {"success": True, "message": "Started"}
        elif cmd_type in ("STOP", "HALT"):
            await self.set_state(EquipmentState.IDLE)
            result = {"success": True, "message": "Stopped"}
        elif cmd_type in ("PAUSE", "HOLD"):
            await self.set_state(EquipmentState.PAUSED)
            result = {"success": True, "message": "Paused"}
        elif cmd_type in ("RESUME", "CONTINUE"):
            await self.set_state(EquipmentState.RUNNING)
            result = {"success": True, "message": "Resumed"}
        elif cmd_type == "ABORT":
            await self.set_state(EquipmentState.ERROR)
            result = {"success": True, "message": "Aborted"}
        else:
            result = {"success": False, "message": f"Unknown command: {cmd_type}"}

        return result

    async def set_date_time(self, time_str: str) -> None:
        """设置设备时间"""
        logger.info(f"Setting date/time to: {time_str}")
        # 在实际应用中，这里会调用系统时间设置接口
        pass

    def get_state_name(self) -> str:
        """获取状态名称"""
        return self._state.value.upper()
