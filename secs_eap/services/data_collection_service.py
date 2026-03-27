"""
数据收集服务

收集和报告设备数据。
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import deque

from secs_driver.src.secs_message import SECSItem

from .collection_events import (
    CollectionEventParser,
    CollectionEventPayload,
    CollectionEventSchema,
)


logger = logging.getLogger(__name__)


class DataCollectionService:
    """
    数据收集服务

    提供：
    - 数据收集
    - Trace 数据收集
    - 事件报告
    - 数据查询
    """

    def __init__(
        self,
        buffer_size: int = 10000,
        collection_event_config: Optional[Dict[str, Any]] = None,
    ):
        self._buffer_size = buffer_size

        # 收集的数据缓存
        self._data_buffer: deque = deque(maxlen=buffer_size)

        # Trace 配置
        self._trace_configs: Dict[int, Dict] = {}
        self._trace_data: Dict[int, deque] = {}

        # 事件定义
        self._event_definitions: Dict[int, Dict] = {}

        # S6F11 Collection Event 定义
        self._collection_event_parser = CollectionEventParser(
            CollectionEventSchema.from_dict(collection_event_config)
        )

        # 数据订阅者
        self._subscribers: List[callable] = []

    def subscribe(self, callback: callable) -> None:
        """订阅数据收集"""
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: callable) -> None:
        """取消订阅"""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    async def collect_data(self, data_items: List[SECSItem]) -> None:
        """
        收集数据

        Args:
            data_items: 数据项列表
        """
        timestamp = datetime.now()

        # 保存到缓冲区
        entry = {
            "timestamp": timestamp,
            "data": data_items,
        }
        self._data_buffer.append(entry)

        # 通知订阅者
        for subscriber in self._subscribers:
            try:
                if asyncio.iscoroutinefunction(subscriber):
                    await subscriber(entry)
                else:
                    subscriber(entry)
            except Exception as e:
                logger.error(f"Subscriber error: {e}")

    async def get_date_time_data(self) -> List[SECSItem]:
        """
        获取日期时间相关数据 (S6F3/S6F4)

        Returns:
            日期时间数据
        """
        now = datetime.now()
        time_str = now.strftime("%Y%m%d%H%M%S")

        return [
            SECSItem.ascii(time_str),
            SECSItem.uint2(now.year),
            SECSItem.uint1(now.month),
            SECSItem.uint1(now.day),
            SECSItem.uint1(now.hour),
            SECSItem.uint1(now.minute),
            SECSItem.uint1(now.second),
        ]

    async def get_variable_data(
        self,
        vid_list: List[int],
    ) -> List[SECSItem]:
        """
        获取变量数据 (S6F5/S6F6)

        Args:
            vid_list: Variable ID 列表

        Returns:
            变量数据列表
        """
        # 从设备服务获取变量数据
        # 这里返回空，实际实现需要从 EquipmentService 获取
        return []

    async def configure_trace(
        self,
        trace_id: int,
        sample_period: int,
        vid_list: List[int],
        data_limit: int = 1000,
    ) -> bool:
        """
        配置 Trace 收集

        Args:
            trace_id: Trace ID
            sample_period: 采样周期 (秒)
            vid_list: Variable ID 列表
            data_limit: 数据限制

        Returns:
            是否成功
        """
        config = {
            "trace_id": trace_id,
            "sample_period": sample_period,
            "vid_list": vid_list,
            "data_limit": data_limit,
            "enabled": True,
            "task": None,
        }

        self._trace_configs[trace_id] = config
        self._trace_data[trace_id] = deque(maxlen=data_limit)

        # 启动 trace 任务
        config["task"] = asyncio.create_task(self._trace_loop(trace_id))

        logger.info(f"Trace {trace_id} configured: period={sample_period}s, vars={len(vid_list)}")
        return True

    async def stop_trace(self, trace_id: int) -> bool:
        """
        停止 Trace 收集

        Args:
            trace_id: Trace ID

        Returns:
            是否成功
        """
        if trace_id not in self._trace_configs:
            return False

        config = self._trace_configs[trace_id]
        config["enabled"] = False

        if config["task"]:
            config["task"].cancel()
            try:
                await config["task"]
            except asyncio.CancelledError:
                pass

        logger.info(f"Trace {trace_id} stopped")
        return True

    async def _trace_loop(self, trace_id: int) -> None:
        """Trace 采集循环"""
        config = self._trace_configs.get(trace_id)
        if not config:
            return

        sample_period = config["sample_period"]

        while config["enabled"]:
            try:
                await asyncio.sleep(sample_period)

                if not config["enabled"]:
                    break

                # 采集数据
                timestamp = datetime.now()
                # TODO: 从设备服务获取实际变量值
                trace_entry = {
                    "timestamp": timestamp,
                    "trace_id": trace_id,
                    "data": [],  # 实际变量数据
                }

                self._trace_data[trace_id].append(trace_entry)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Trace {trace_id} error: {e}")

    async def get_trace_data(
        self,
        trace_id: int,
        limit: int = 100,
    ) -> List[Dict]:
        """
        获取 Trace 数据

        Args:
            trace_id: Trace ID
            limit: 返回数量

        Returns:
            Trace 数据列表
        """
        if trace_id not in self._trace_data:
            return []

        data = list(self._trace_data[trace_id])
        return data[-limit:]

    async def define_event(self, event_id: int, definition: Dict) -> None:
        """
        定义事件

        Args:
            event_id: 事件 ID
            definition: 事件定义
        """
        self._event_definitions[event_id] = definition
        logger.info(f"Event {event_id} defined")

    def set_collection_event_schema(self, config: Optional[Dict[str, Any]]) -> None:
        """设置 S6F11 Collection Event 配置。"""
        self._collection_event_parser.set_schema(CollectionEventSchema.from_dict(config))

    def parse_collection_event(self, message) -> Optional[CollectionEventPayload]:
        """解析 S6F11 消息为结构化事件。"""
        return self._collection_event_parser.parse_s6f11(message)

    async def report_collection_event(self, message) -> Optional[CollectionEventPayload]:
        """解析并记录一条 S6F11 Collection Event。"""
        payload = self.parse_collection_event(message)
        if not payload:
            return None

        event_entry = {
            "type": "collection_event",
            "timestamp": datetime.now(),
            "event": payload.to_dict(),
        }
        self._data_buffer.append(event_entry)
        return payload

    async def report_event(self, event_id: int, data: Dict = None) -> None:
        """
        报告事件

        Args:
            event_id: 事件 ID
            data: 事件数据
        """
        if event_id not in self._event_definitions:
            logger.warning(f"Event {event_id} not defined")
            return

        event_entry = {
            "event_id": event_id,
            "timestamp": datetime.now(),
            "data": data or {},
        }

        # 保存事件
        self._data_buffer.append(event_entry)

        logger.debug(f"Event {event_id} reported")

    def get_data_buffer_size(self) -> int:
        """获取数据缓冲区大小"""
        return len(self._data_buffer)

    def get_trace_config(self, trace_id: int) -> Optional[Dict]:
        """获取 Trace 配置"""
        return self._trace_configs.get(trace_id)
