"""
EAP 主程序

Equipment Automation Program - 设备自动化程序

整合驱动适配层、消息处理层和业务逻辑层，
提供完整的 SECS/EAP 功能。
"""

import asyncio
import logging
import signal
from typing import Optional, Dict, Any

from secs_driver.src.logging_utils import RuntimeLogFormatter

from .config import EAPConfig, EquipmentConfig
from .driver_adapter import DriverAdapter, ConnectionState
from .message_handlers import MessageDispatcher, MessageHandlerRegistry
from .message_handlers.s1_handler import S1HandlerManager
from .message_handlers.s2_handler import S2HandlerManager
from .message_handlers.s5_handler import S5HandlerManager
from .message_handlers.s6_handler import S6HandlerManager
from .services import (
    EquipmentService,
    AlarmService,
    DataCollectionService,
    ProcessService,
    WorkflowEngine,
)
from .mes import (
    MesMqConfig,
    MesMqService,
    APVRYOPERequest,
    APVRYOPEResponse,
    TxRoute,
    get_tx_route,
    list_tx_routes,
    reload_tx_routes,
)


logger = logging.getLogger(__name__)


class EAP:
    """
    EAP 主类

    整合所有组件，协调消息流和业务逻辑。
    """

    def __init__(self, config: EAPConfig = None):
        """
        初始化 EAP

        Args:
            config: EAP 配置
        """
        self._config = config or EAPConfig()
        self._running = False

        # 组件
        self._driver_adapter: Optional[DriverAdapter] = None
        self._dispatcher: Optional[MessageDispatcher] = None
        self._registry: Optional[MessageHandlerRegistry] = None

        # 业务服务
        self._equipment_service: Optional[EquipmentService] = None
        self._alarm_service: Optional[AlarmService] = None
        self._data_service: Optional[DataCollectionService] = None
        self._process_service: Optional[ProcessService] = None
        self._workflow_engine: Optional[WorkflowEngine] = None
        self._mes_mq_service: Optional[MesMqService] = None
        self._mes_mq_connect_error: Optional[str] = None

        # 消息处理器管理器
        self._s1_manager: Optional[S1HandlerManager] = None
        self._s2_manager: Optional[S2HandlerManager] = None
        self._s5_manager: Optional[S5HandlerManager] = None
        self._s6_manager: Optional[S6HandlerManager] = None

        # 回调
        self._on_started: Optional[callable] = None
        self._on_stopped: Optional[callable] = None
        self._on_error: Optional[callable] = None

        # 初始化
        self._setup_logging()
        self._init_components()

    def _setup_logging(self) -> None:
        """配置日志"""
        log_config = self._config.equipment
        level = getattr(logging, log_config.log_level.upper(), logging.INFO)

        # 创建日志格式
        formatter = RuntimeLogFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # 配置根日志器
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        root_logger.handlers.clear()

        # 控制台输出
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # 文件输出
        if log_config.log_file:
            try:
                from logging.handlers import TimedRotatingFileHandler

                file_handler = TimedRotatingFileHandler(
                    log_config.log_file,
                    when="midnight",
                    interval=1,
                    backupCount=30,
                    encoding="utf-8",
                )
                file_handler.suffix = "%Y-%m-%d"
                file_handler.setFormatter(formatter)
                root_logger.addHandler(file_handler)
            except Exception as e:
                logger.warning(f"Failed to setup file logging: {e}")

    def _init_components(self) -> None:
        """初始化组件"""
        logger.info("Initializing EAP components...")

        # 初始化业务服务
        self._equipment_service = EquipmentService()
        self._alarm_service = AlarmService(
            self._config.business_logic.alarm_history_size
        )
        self._data_service = DataCollectionService(
            self._config.business_logic.trace_data_buffer_size,
            collection_event_config=self._config.business_logic.collection_events,
        )
        self._process_service = ProcessService(
            self._config.business_logic.process_timeout
        )
        self._workflow_engine = WorkflowEngine(
            workflow_file=self._config.business_logic.workflow_file,
            inline_workflows=self._config.business_logic.workflows,
        )
        self._init_mes_mq()

        # 设置服务依赖
        self._process_service.set_equipment_service(self._equipment_service)

        # 初始化驱动适配器
        self._driver_adapter = DriverAdapter(self._config.equipment)

        # 初始化消息分发器
        self._dispatcher = MessageDispatcher(self._driver_adapter)
        self._registry = self._dispatcher.registry

        # 初始化消息处理器管理器
        self._s1_manager = S1HandlerManager(self._driver_adapter)
        self._s2_manager = S2HandlerManager()
        self._s5_manager = S5HandlerManager()
        self._s6_manager = S6HandlerManager()

        # 注册处理器
        self._register_handlers()

        # 设置分发器上下文
        for key, value in {
            "equipment_service": self._equipment_service,
            "alarm_service": self._alarm_service,
            "data_collection_service": self._data_service,
            "collection_event_config": self._config.business_logic.collection_events,
            "process_service": self._process_service,
            "workflow_engine": self._workflow_engine,
            "eap_api": self,
        }.items():
            self._dispatcher.set_context(key, value)

        # 设置分发器回调
        self._dispatcher.set_callbacks(
            on_message_handled=self._on_message_handled,
            on_no_handler=self._on_no_handler,
        )

        logger.info("EAP components initialized")

    def _init_mes_mq(self) -> None:
        """初始化 MES MQ（可选）"""
        mq_cfg = self._config.mes_mq or {}
        if not mq_cfg.get("enabled"):
            return

        self._mes_mq_service = MesMqService(MesMqConfig.from_dict(mq_cfg))

    def _register_handlers(self) -> None:
        """注册消息处理器"""
        for stream, manager in (
            (1, self._s1_manager),
            (2, self._s2_manager),
            (5, self._s5_manager),
            (6, self._s6_manager),
        ):
            self._registry.register(manager, stream=stream)

        logger.info(
            f"Registered {self._registry.get_handler_count()} message handlers"
        )

    def set_callbacks(
        self,
        on_started: Optional[callable] = None,
        on_stopped: Optional[callable] = None,
        on_error: Optional[callable] = None,
    ) -> None:
        """设置回调函数"""
        self._on_started = on_started
        self._on_stopped = on_stopped
        self._on_error = on_error

    async def _invoke_callback(self, callback: Optional[callable], *args) -> None:
        """统一处理同步/异步回调，避免回调类型不匹配导致崩溃。"""
        if not callback:
            return

        result = callback(*args)
        if asyncio.iscoroutine(result):
            await result

    async def start(self) -> bool:
        """
        启动 EAP

        Returns:
            是否启动成功
        """
        if self._running:
            logger.warning("EAP already running")
            return True

        logger.info("Starting EAP...")

        try:
            # 启动消息分发器
            await self._dispatcher.start()

            # 连接设备
            connected = await self._driver_adapter.connect()

            if not connected:
                logger.error("Failed to connect to equipment")
                await self._dispatcher.stop()
                return False

            self._running = True

            if self._mes_mq_service:
                try:
                    self._mes_mq_connect_error = None
                    self._mes_mq_service.connect()
                except Exception as mq_exc:
                    self._mes_mq_connect_error = str(mq_exc)
                    logger.warning(
                        "MES MQ connect failed (workflow MQ steps will be skipped): %s",
                        mq_exc,
                    )

            # 触发回调
            await self._invoke_callback(self._on_started)

            logger.info("EAP started successfully")
            return True

        except Exception as e:
            logger.exception(f"Failed to start EAP: {e}")
            await self._invoke_callback(self._on_error, e)
            return False

    async def stop(self) -> None:
        """停止 EAP"""
        if not self._running:
            return

        logger.info("Stopping EAP...")

        try:
            # 断开连接
            await self._driver_adapter.disconnect()

            if self._mes_mq_service:
                self._mes_mq_service.close()

            # 停止分发器
            await self._dispatcher.stop()

            self._running = False

            # 触发回调
            await self._invoke_callback(self._on_stopped)

            logger.info("EAP stopped")

        except Exception as e:
            logger.exception(f"Error stopping EAP: {e}")
            await self._invoke_callback(self._on_error, e)

    async def _on_message_handled(
        self,
        message,
        result,
        success: bool = True,
    ) -> None:
        """消息处理完成回调"""
        status = "OK" if success else "FAIL"
        logger.debug(f"Message {message.sf} handled: {status}")

    def _on_no_handler(self, message) -> None:
        """无处理器回调"""
        logger.warning(f"No handler for message: {message.sf}")

    # ==================== 业务操作 API ====================

    async def send_message(
        self,
        stream: int,
        function: int,
        items: list = None,
        wait_reply: bool = True,
        timeout: float = None,
    ):
        """
        发送 SECS 消息

        Args:
            stream: Stream 编号
            function: Function 编号
            items: 消息数据项
            wait_reply: 是否等待回复
            timeout: 超时时间

        Returns:
            回复消息
        """
        return await self._driver_adapter.send_message(
            stream=stream,
            function=function,
            items=items,
            wait_reply=wait_reply,
            timeout=timeout,
        )

    async def get_equipment_status(self) -> Dict[str, Any]:
        """获取设备状态"""
        return {
            "state": self._equipment_service.state.value if self._equipment_service else "unknown",
            "online": self._equipment_service.is_online if self._equipment_service else False,
            "connection": self._driver_adapter.state.value if self._driver_adapter else "disconnected",
            "selected": self._driver_adapter.is_selected if self._driver_adapter else False,
        }

    async def get_active_alarms(self) -> list:
        """获取当前报警"""
        return self._alarm_service.get_active_alarm_ids()

    async def clear_alarm(self, alarm_id: int) -> bool:
        """清除报警"""
        return await self._alarm_service.clear_alarm(alarm_id)

    async def get_current_job(self) -> Optional[Dict]:
        """获取当前作业"""
        job = self._process_service.get_current_job()
        if job:
            return {
                "job_id": job.job_id,
                "recipe_id": job.recipe_id,
                "state": job.state.value,
                "progress": job.progress,
            }
        return None

    async def submit_process_job(
        self,
        recipe_id: str,
        carrier_id: str = "",
        lot_id: str = "",
    ) -> bool:
        """提交工艺作业"""
        job = await self._process_service.create_job(recipe_id, carrier_id, lot_id)
        return await self._process_service.submit_job(job)

    async def abort_process(self) -> bool:
        """中止工艺"""
        return await self._process_service.abort_job()

    async def query_lot_by_apvryope(
        self,
        eqpt_id: str,
        port_id: str,
        crr_id: str,
        user_id: str,
        trx_id: str = "APVRYOPE",
    ) -> APVRYOPEResponse:
        """
        Use APVRYOPE TX to query lot info from MES via IBM MQ.
        """
        if not self._mes_mq_service:
            raise RuntimeError("MES MQ is not enabled")

        # Try lazy reconnect once in case startup connect failed.
        if not self._mes_mq_service.is_connected:
            self._mes_mq_service.connect()

        req = APVRYOPERequest(
            trx_id=trx_id,
            eqpt_id=eqpt_id,
            port_id=port_id,
            crr_id=crr_id,
            user_id=user_id,
        )
        # MQ client is synchronous; offload to a thread to avoid blocking asyncio loop.
        return await self.execute_mes_tx("APVRYOPE", req)

    async def execute_mes_tx(self, tx_name: str, request: Any) -> Any:
        """Execute one registered MES TX with a Python request codec object."""
        if not self._mes_mq_service:
            raise RuntimeError("MES MQ is not enabled")

        if not self._mes_mq_service.is_connected:
            self._mes_mq_service.connect()

        return await asyncio.to_thread(self._mes_mq_service.execute_tx, tx_name, request)

    def is_mes_mq_ready(self) -> bool:
        # Workflow steps may use a fresh connection per TX, so "configured/enabled"
        # is a better readiness signal than "already connected".
        return bool(self._mes_mq_service)

    def mes_mq_ready_reason(self) -> str:
        if not self._mes_mq_service:
            return "MES MQ not enabled in config"
        if self._mes_mq_service.is_connected:
            return "connected"
        if self._mes_mq_connect_error:
            return self._mes_mq_connect_error
        return "MQ client not connected"

    def get_registered_tx_routes(self) -> Dict[str, TxRoute]:
        """Return all TX routes discovered from secs_eap/mes/tx."""
        return {route.tx_name: route for route in list_tx_routes()}

    def get_registered_tx_route(self, tx_name: str) -> TxRoute:
        """Return one TX route discovered from secs_eap/mes/tx."""
        return get_tx_route(tx_name)

    def reload_registered_tx_routes(self) -> Dict[str, TxRoute]:
        """Reload TX routes after tx/ source files change."""
        return dict(reload_tx_routes())

    # ==================== 属性 ====================

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running

    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._driver_adapter.is_connected if self._driver_adapter else False

    @property
    def is_selected(self) -> bool:
        """会话是否已选中"""
        return self._driver_adapter.is_selected if self._driver_adapter else False

    @property
    def equipment_service(self) -> EquipmentService:
        """获取设备服务"""
        return self._equipment_service

    @property
    def alarm_service(self) -> AlarmService:
        """获取报警服务"""
        return self._alarm_service

    @property
    def data_service(self) -> DataCollectionService:
        """获取数据收集服务"""
        return self._data_service

    @property
    def process_service(self) -> ProcessService:
        """获取工艺流程服务"""
        return self._process_service


# ==================== 便捷入口 ====================


async def run_eap(config: EAPConfig = None) -> None:
    """
    运行 EAP（带信号处理）

    Args:
        config: EAP 配置
    """
    eap = EAP(config)

    # 信号处理
    loop = asyncio.get_event_loop()

    def signal_handler():
        logger.info("Received shutdown signal")
        asyncio.create_task(eap.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    # 启动
    started = await eap.start()

    if not started:
        logger.error("EAP failed to start")
        return

    # 保持运行
    try:
        while eap.is_running:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        await eap.stop()


def main() -> None:
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="SECS EAP - Equipment Automation Program")
    parser.add_argument("--config", "-c", help="Config file path")
    parser.add_argument("--host", default="127.0.0.1", help="Equipment host")
    parser.add_argument("--port", type=int, default=5000, help="Equipment port")
    parser.add_argument("--mode", choices=["active", "passive"], default="active", help="Connection mode")
    parser.add_argument("--device-id", type=int, default=0, help="Device ID")
    parser.add_argument("--log-level", default="INFO", help="Log level")
    parser.add_argument("--log-file", default=None, help="Log file path (optional)")

    args = parser.parse_args()

    # 创建配置
    if args.config:
        config = EAPConfig.from_file(args.config)
    else:
        config = EAPConfig(
            equipment=EquipmentConfig(
                host=args.host,
                port=args.port,
                mode=args.mode,
                device_id=args.device_id,
                log_level=args.log_level,
                log_file=args.log_file,
            ),
        )
    # 运行
    try:
        asyncio.run(run_eap(config))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
