"""
工艺流程服务

管理生产流程、批次处理等。
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


logger = logging.getLogger(__name__)


class ProcessState(Enum):
    """工艺状态"""

    IDLE = "idle"
    LOADING = "loading"
    PROCESSING = "processing"
    UNLOADING = "unloading"
    COMPLETED = "completed"
    ABORTED = "aborted"
    ERROR = "error"


@dataclass
class ProcessJob:
    """工艺作业"""

    job_id: str
    recipe_id: str
    carrier_id: str = ""
    lot_id: str = ""
    state: ProcessState = ProcessState.IDLE
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    progress: float = 0.0  # 0.0 - 1.0
    parameters: Dict[str, Any] = field(default_factory=dict)
    results: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""


class ProcessService:
    """
    工艺流程服务

    提供：
    - 工艺作业管理
    - 流程控制
    - 批次跟踪
    - 工艺参数管理
    """

    def __init__(self, timeout: float = 3600.0):
        self._timeout = timeout

        # 当前作业
        self._current_job: Optional[ProcessJob] = None

        # 作业队列
        self._job_queue: List[ProcessJob] = []

        # 作业历史
        self._job_history: List[ProcessJob] = []

        # 事件回调
        self._on_job_started: Optional[Callable] = None
        self._on_job_completed: Optional[Callable] = None
        self._on_job_aborted: Optional[Callable] = None
        self._on_process_event: Optional[Callable] = None

        # 设备服务引用
        self._equipment_service = None

    def set_equipment_service(self, service) -> None:
        """设置设备服务"""
        self._equipment_service = service

    def set_callbacks(
        self,
        on_job_started: Optional[Callable] = None,
        on_job_completed: Optional[Callable] = None,
        on_job_aborted: Optional[Callable] = None,
        on_process_event: Optional[Callable] = None,
    ) -> None:
        """设置回调函数"""
        self._on_job_started = on_job_started
        self._on_job_completed = on_job_completed
        self._on_job_aborted = on_job_aborted
        self._on_process_event = on_process_event

    async def _invoke_callback(self, callback: Optional[Callable], *args) -> None:
        """统一处理同步/异步回调。"""
        if not callback:
            return

        result = callback(*args)
        if asyncio.iscoroutine(result):
            await result

    async def create_job(
        self,
        recipe_id: str,
        carrier_id: str = "",
        lot_id: str = "",
        parameters: Dict[str, Any] = None,
    ) -> ProcessJob:
        """
        创建工艺作业

        Args:
            recipe_id: 配方 ID
            carrier_id: 载具 ID
            lot_id: 批次 ID
            parameters: 作业参数

        Returns:
            工艺作业
        """
        job = ProcessJob(
            job_id=f"JOB_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            recipe_id=recipe_id,
            carrier_id=carrier_id,
            lot_id=lot_id,
            parameters=parameters or {},
        )

        logger.info(f"Job created: {job.job_id}, recipe={recipe_id}")
        return job

    async def submit_job(self, job: ProcessJob) -> bool:
        """
        提交作业

        Args:
            job: 工艺作业

        Returns:
            是否成功
        """
        if self._current_job and self._current_job.state == ProcessState.PROCESSING:
            # 当前有作业在运行，加入队列
            self._job_queue.append(job)
            logger.info(f"Job {job.job_id} queued (position {len(self._job_queue)})")
        else:
            # 直接启动作业
            await self._start_job(job)

        return True

    async def _start_job(self, job: ProcessJob) -> None:
        """启动作业"""
        job.state = ProcessState.LOADING
        self._current_job = job

        logger.info(f"Job started: {job.job_id}")

        # 更新设备状态
        if self._equipment_service:
            from .equipment_service import EquipmentState

            await self._equipment_service.set_state(EquipmentState.RUNNING)

        # 触发回调
        await self._invoke_callback(self._on_job_started, job)

        # 启动作业处理
        asyncio.create_task(self._process_job(job))

    async def _process_job(self, job: ProcessJob) -> None:
        """处理作业（异步执行）"""
        try:
            # 加载阶段
            job.state = ProcessState.LOADING
            await self._emit_event("LOADING", {"job_id": job.job_id})
            await asyncio.sleep(1)  # 模拟加载时间

            # 加工阶段
            job.state = ProcessState.PROCESSING
            job.start_time = datetime.now()

            await self._emit_event("PROCESS_START", {
                "job_id": job.job_id,
                "recipe": job.recipe_id,
            })

            # 模拟加工过程
            for i in range(10):
                await asyncio.sleep(0.5)
                job.progress = (i + 1) / 10.0

                if job.state == ProcessState.ABORTED:
                    break

            if job.state == ProcessState.PROCESSING:
                # 完成加工
                job.state = ProcessState.COMPLETED
                job.end_time = datetime.now()
                job.progress = 1.0

                await self._emit_event("PROCESS_COMPLETE", {
                    "job_id": job.job_id,
                })
                await self._invoke_callback(self._on_job_completed, job)

                logger.info(f"Job completed: {job.job_id}")

        except Exception as e:
            job.state = ProcessState.ERROR
            job.error_message = str(e)
            job.end_time = datetime.now()

            logger.error(f"Job error: {job.job_id}, error={e}")

        finally:
            # 解锁设备
            if self._equipment_service:
                from .equipment_service import EquipmentState

                await self._equipment_service.set_state(EquipmentState.IDLE)

            # 移动到历史
            self._job_history.append(job)
            self._current_job = None

            # 处理下一个作业
            if self._job_queue:
                next_job = self._job_queue.pop(0)
                await self._start_job(next_job)

    async def abort_job(self, job_id: str = None) -> bool:
        """
        中止作业

        Args:
            job_id: 作业 ID (None 表示当前作业)

        Returns:
            是否成功
        """
        job = self._current_job
        if job_id:
            if not job or job.job_id != job_id:
                job = None
                for q_job in self._job_queue:
                    if q_job.job_id == job_id:
                        self._job_queue.remove(q_job)
                        job = q_job
                        break

        if not job:
            return False

        job.state = ProcessState.ABORTED
        job.end_time = datetime.now()

        logger.info(f"Job aborted: {job.job_id}")

        await self._invoke_callback(self._on_job_aborted, job)

        return True

    async def pause_job(self) -> bool:
        """暂停当前作业"""
        if not self._current_job:
            return False

        if self._current_job.state == ProcessState.PROCESSING:
            self._current_job.state = ProcessState.IDLE  # 实际应该 PAUSED
            logger.info(f"Job paused: {self._current_job.job_id}")
            return True

        return False

    async def resume_job(self) -> bool:
        """恢复作业"""
        if not self._current_job:
            return False

        if self._current_job.state == ProcessState.IDLE:
            self._current_job.state = ProcessState.PROCESSING
            logger.info(f"Job resumed: {self._current_job.job_id}")
            return True

        return False

    async def _emit_event(self, event_name: str, data: Dict) -> None:
        """发送流程事件"""
        await self._invoke_callback(self._on_process_event, event_name, data)

    def get_current_job(self) -> Optional[ProcessJob]:
        """获取当前作业"""
        return self._current_job

    def get_queue_size(self) -> int:
        """获取队列大小"""
        return len(self._job_queue)

    def get_job_history(self, limit: int = 100) -> List[ProcessJob]:
        """获取作业历史"""
        return self._job_history[-limit:]

    @property
    def is_processing(self) -> bool:
        """是否正在处理"""
        return self._current_job is not None and self._current_job.state == ProcessState.PROCESSING

    @property
    def completed_job_count(self) -> int:
        """已完成作业数"""
        return sum(1 for j in self._job_history if j.state == ProcessState.COMPLETED)
