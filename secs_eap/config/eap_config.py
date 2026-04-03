"""
EAP 配置定义
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class PortConfig:
    """单个端口配置"""

    port_id: str = ""
    port_type: str = "loader"
    name: Optional[str] = None
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "port_id": self.port_id,
            "port_type": self.port_type,
            "name": self.name,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PortConfig":
        return cls(
            port_id=str(data.get("port_id", "") or ""),
            port_type=str(data.get("port_type", "loader") or "loader"),
            name=data.get("name"),
            enabled=bool(data.get("enabled", True)),
        )


@dataclass
class EquipmentConfig:
    """设备配置"""

    name: str = "EAP"
    user_id: str = "AGT"
    device_id: int = 0
    port_count: int = 0
    ports: List[PortConfig] = field(default_factory=list)
    # 连接配置
    mode: str = "active"  # "active" 或 "passive"
    host: str = "127.0.0.1"
    port: int = 5000
    timeout: float = 30.0
    retry_interval: float = 5.0
    max_retry: int = 3
    # HSMS 超时配置
    t3_timeout: float = 45.0  # 消息等待超时
    t5_timeout: float = 10.0  # 连接分隔超时
    t6_timeout: float = 5.0  # 控制会话超时
    t7_timeout: float = 10.0  # 不选择超时
    t8_timeout: float = 5.0  # 通信超时
    # 日志配置
    log_level: str = "INFO"
    log_file: Optional[str] = None

    def get_port(self, port_id: str) -> Optional[PortConfig]:
        """根据 port_id 查找端口配置。"""
        target = str(port_id or "").strip()
        if not target:
            return None
        for port in self.ports:
            if str(port.port_id).strip() == target:
                return port
        return None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EquipmentConfig":
        raw_ports = data.get("ports", []) or []
        ports: List[PortConfig] = []
        if isinstance(raw_ports, dict):
            for key, value in raw_ports.items():
                if isinstance(value, PortConfig):
                    ports.append(value)
                    continue
                port_data = dict(value or {})
                port_data.setdefault("port_id", key)
                ports.append(PortConfig.from_dict(port_data))
        else:
            ports = [
                port if isinstance(port, PortConfig) else PortConfig.from_dict(port)
                for port in raw_ports
            ]
        port_count = int(data.get("port_count", 0) or 0)
        if ports and port_count <= 0:
            port_count = len(ports)

        return cls(
            name=data.get("name", "EAP"),
            user_id=str(data.get("user_id", "AGT") or "AGT"),
            device_id=data.get("device_id", 0),
            port_count=port_count,
            ports=ports,
            mode=data.get("mode", "active"),
            host=data.get("host", "127.0.0.1"),
            port=data.get("port", 5000),
            timeout=data.get("timeout", 30.0),
            retry_interval=data.get("retry_interval", 5.0),
            max_retry=data.get("max_retry", 3),
            t3_timeout=data.get("t3_timeout", 45.0),
            t5_timeout=data.get("t5_timeout", 10.0),
            t6_timeout=data.get("t6_timeout", 5.0),
            t7_timeout=data.get("t7_timeout", 10.0),
            t8_timeout=data.get("t8_timeout", 5.0),
            log_level=data.get("log_level", "INFO"),
            log_file=data.get("log_file"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "user_id": self.user_id,
            "device_id": self.device_id,
            "port_count": self.port_count,
            "ports": [port.to_dict() for port in self.ports],
            "mode": self.mode,
            "host": self.host,
            "port": self.port,
            "timeout": self.timeout,
            "retry_interval": self.retry_interval,
            "max_retry": self.max_retry,
            "t3_timeout": self.t3_timeout,
            "t5_timeout": self.t5_timeout,
            "t6_timeout": self.t6_timeout,
            "t7_timeout": self.t7_timeout,
            "t8_timeout": self.t8_timeout,
            "log_level": self.log_level,
            "log_file": self.log_file,
        }


@dataclass
class MessageHandlerConfig:
    """消息处理器配置"""

    # 消息超时配置（秒）
    s1f1_timeout: float = 30.0  # Are You There
    s1f13_timeout: float = 30.0  # Establish Communications Request
    s2f17_timeout: float = 60.0  # Date/Time Request
    s2f29_timeout: float = 60.0  # Variable Attribute Request
    s5f1_timeout: float = 30.0  # Alarm Report
    s6f1_timeout: float = 30.0  # Data Collection
    s6f3_timeout: float = 30.0  # Date/Time Variable Data Request
    s6f5_timeout: float = 30.0  # Variable Collection Request
    s7f1_timeout: float = 120.0  # Process Program Load Inquire
    s7f3_timeout: float = 120.0  # Process Program Send
    s7f5_timeout: float = 60.0  # Process Program Request
    s7f17_timeout: float = 120.0  # Process Program Delete
    s7f19_timeout: float = 180.0  # Process Program List Request
    s7f21_timeout: float = 180.0  # Process Program Attributes Request

    # 启用/禁用特定消息处理
    enabled_messages: Dict[str, bool] = field(default_factory=lambda: {
        "S1F1": True,
        "S1F3": True,
        "S1F13": True,
        "S1F14": True,
        "S1F15": True,
        "S1F17": True,
        "S2F1": True,
        "S2F3": True,
        "S2F5": True,
        "S2F7": True,
        "S2F9": True,
        "S2F11": True,
        "S2F13": True,
        "S2F15": True,
        "S2F17": True,
        "S2F23": True,
        "S2F25": True,
        "S2F29": True,
        "S2F31": True,
        "S2F33": True,
        "S2F35": True,
        "S2F37": True,
        "S2F41": True,
        "S2F43": True,
        "S5F1": True,
        "S5F3": True,
        "S5F5": True,
        "S5F7": True,
        "S6F1": True,
        "S6F3": True,
        "S5": True,
        "S6F5": True,
        "S6F7": True,
        "S6F11": True,
        "S6F13": True,
        "S6F15": True,
        "S6F17": True,
        "S7F1": True,
        "S7F3": True,
        "S7F5": True,
        "S7F17": True,
        "S7F19": True,
        "S7F21": True,
        "S7F23": True,
        "S7F25": True,
        "S7F27": True,
        "S7F29": True,
        "S7F31": True,
        "S7F33": True,
        "S7F35": True,
        "S7F37": True,
        "S7F39": True,
        "S7F41": True,
        "S7F43": True,
        "S7F45": True,
        "S7F47": True,
        "S7F49": True,
        "S7F51": True,
        "S7F53": True,
        "S7F55": True,
        "S7F57": True,
        "S7F59": True,
        "S7F61": True,
        "S7F63": True,
    })


@dataclass
class BusinessLogicConfig:
    """业务逻辑配置"""

    # 报警配置
    alarm_history_size: int = 1000
    auto_acknowledge_alarms: bool = False

    # 数据收集配置
    data_collection_interval: float = 1.0
    trace_data_buffer_size: int = 10000
    collection_events: Dict = field(default_factory=dict)

    # 工艺流程配置
    default_process_sequence: List[str] = field(default_factory=list)
    process_timeout: float = 3600.0  # 1小时
    recipe_directory: Optional[str] = None
    allow_recipe_overwrite: bool = True
    workflow_file: Optional[str] = None
    workflows: List[Dict] = field(default_factory=list)


@dataclass
class EAPConfig:
    """EAP 主配置"""

    equipment: EquipmentConfig = field(default_factory=EquipmentConfig)
    message_handler: MessageHandlerConfig = field(default_factory=MessageHandlerConfig)
    business_logic: BusinessLogicConfig = field(default_factory=BusinessLogicConfig)
    mes_mq: Dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, config: dict) -> "EAPConfig":
        """从字典创建配置"""
        equipment_raw = config.get("equipment", {}) or {}
        equipment_config = (
            equipment_raw
            if isinstance(equipment_raw, EquipmentConfig)
            else EquipmentConfig.from_dict(equipment_raw)
        )
        message_config = MessageHandlerConfig(**config.get("message_handler", {}))
        business_config = BusinessLogicConfig(**config.get("business_logic", {}))

        return cls(
            equipment=equipment_config,
            message_handler=message_config,
            business_logic=business_config,
            mes_mq=config.get("mes_mq", {}) or {},
        )

    @classmethod
    def from_file(cls, filepath: str) -> "EAPConfig":
        """从 YAML/JSON 文件加载配置"""
        import json

        with open(filepath, "r", encoding="utf-8") as f:
            if filepath.endswith(".json"):
                config = json.load(f)
            else:
                import yaml

                config = yaml.safe_load(f)

        return cls.from_dict(config)
