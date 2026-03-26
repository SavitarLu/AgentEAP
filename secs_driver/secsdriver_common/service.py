"""
对外复用的 SECS common service。
"""

from __future__ import annotations

from typing import Callable, Dict, Optional

from src.model_templates import load_model_templates
from src.secs_message import SECSMessage
from src.simulator_core import SimulatorEndpoint, SimulatorEvent, message_to_text


class SECSCommonService:
    """为 GUI / bridge 提供稳定的高层入口。"""

    def __init__(self, event_sink: Callable[[SimulatorEvent], None]):
        self._event_sink = event_sink
        self._endpoint: Optional[SimulatorEndpoint] = None
        self._template_replies: Dict[str, str] = {}
        self._template_path: str = ""
        self._mode: str = "passive"

    @property
    def is_running(self) -> bool:
        return self._endpoint is not None

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def template_path(self) -> str:
        return self._template_path

    async def load_templates(self, xml_path: str) -> int:
        templates = load_model_templates(xml_path)
        self._template_path = xml_path
        self._template_replies = {
            template.sf.upper(): template.secondary_text
            for template in templates
            if template.secondary_text.strip()
        }
        if self._endpoint is not None:
            await self._endpoint.update_auto_reply_templates(self._template_replies)
        return len(templates)

    async def start(
        self,
        mode: str,
        host: str,
        port: int,
        *,
        device_id: int = 0,
        auto_reply: bool = True,
        auto_reply_payload: str = "",
    ) -> bool:
        normalized_mode, endpoint_mode = self._normalize_mode(mode)
        await self.stop()

        endpoint = SimulatorEndpoint("service", endpoint_mode, self._event_sink)
        self._endpoint = endpoint
        self._mode = normalized_mode
        return await endpoint.start(
            host,
            port,
            device_id=device_id,
            auto_reply=auto_reply,
            auto_reply_payload=auto_reply_payload,
            auto_reply_templates=self._template_replies,
        )

    async def stop(self) -> None:
        endpoint = self._endpoint
        self._endpoint = None
        if endpoint is not None:
            await endpoint.stop()

    async def send(
        self,
        sf: str,
        payload_text: str = "",
        *,
        wait_reply: bool = False,
        timeout: float = 10.0,
    ) -> Optional[SECSMessage]:
        if self._endpoint is None:
            raise RuntimeError("SECS service 尚未启动")
        return await self._endpoint.send(
            sf,
            payload_text,
            wait_reply=wait_reply,
            timeout=timeout,
        )

    async def update_auto_reply(
        self,
        enabled: bool,
        payload_text: str = "",
    ) -> None:
        if self._endpoint is None:
            raise RuntimeError("SECS service 尚未启动")
        await self._endpoint.update_auto_reply(
            enabled,
            payload_text,
            self._template_replies,
        )

    @staticmethod
    def render_message(message: SECSMessage) -> str:
        return message_to_text(message)

    @staticmethod
    def _normalize_mode(mode: str) -> tuple[str, str]:
        normalized = mode.strip().lower()
        if normalized in {"passive", "server"}:
            return "passive", "passive"
        if normalized in {"host", "active", "client"}:
            return "host", "active"
        raise ValueError(f"Unsupported mode: {mode}")
