"""
EAP 配置定义
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class EquipmentConfig:
    """设备配置"""

    name: str = "EAP"
    device_id: int = 0
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
        equipment_config = EquipmentConfig(**config.get("equipment", {}))
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
