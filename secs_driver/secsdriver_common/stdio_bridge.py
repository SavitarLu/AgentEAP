"""
为 Java GUI 提供本地 stdio bridge。
"""

from __future__ import annotations

import asyncio
import sys
from typing import Dict

from src.simulator_core import SimulatorEvent

from .bridge_protocol import BridgeCommand, format_event, format_response, parse_packet
from .service import SECSCommonService


def _bool_value(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class StdioBridgeServer:
    """基于 stdin/stdout 的单实例 bridge。"""

    def __init__(self) -> None:
        self._outbox: "asyncio.Queue[str | None] | None" = None
        self._service = SECSCommonService(self._on_event)
        self._running = True

    def _on_event(self, event: SimulatorEvent) -> None:
        if self._outbox is None:
            return
        self._outbox.put_nowait(
            format_event(
                event.kind,
                {
                    "endpoint": event.endpoint,
                    "status": event.status or "",
                    "timestamp": event.timestamp,
                    "text": event.text,
                },
            )
        )

    async def run(self) -> None:
        self._outbox = asyncio.Queue()
        writer_task = asyncio.create_task(self._writer_loop())
        try:
            while self._running:
                raw_line = await asyncio.to_thread(sys.stdin.readline)
                if not raw_line:
                    break
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    packet = parse_packet(raw_line)
                    if not isinstance(packet, BridgeCommand):
                        raise ValueError("Bridge 只接受 CMD 包")
                    await self._handle_command(packet)
                except Exception as exc:
                    await self._outbox.put(
                        format_response("0", False, {"message": str(exc)})
                    )
        finally:
            self._running = False
            await self._service.stop()
            if self._outbox is not None:
                await self._outbox.put(None)
            await writer_task

    async def _writer_loop(self) -> None:
        if self._outbox is None:
            raise RuntimeError("bridge outbox 尚未初始化")
        while True:
            line = await self._outbox.get()
            if line is None:
                break
            sys.stdout.write(line + "\n")
            sys.stdout.flush()

    async def _handle_command(self, command: BridgeCommand) -> None:
        name = command.name.strip().lower()
        params = command.params

        if name == "ping":
            await self._respond(command.command_id, True, {"message": "pong"})
            return

        if name == "load_templates":
            count = await self._service.load_templates(params.get("path", "").strip())
            await self._respond(command.command_id, True, {"count": count})
            return

        if name == "start":
            started = await self._service.start(
                params.get("mode", "passive"),
                params.get("host", "127.0.0.1"),
                int(params.get("port", "5000")),
                device_id=int(params.get("device_id", "0")),
                auto_reply=_bool_value(params.get("auto_reply", "1"), True),
                auto_reply_payload=params.get("auto_reply_payload", ""),
            )
            await self._respond(command.command_id, True, {"started": "1" if started else "0"})
            return

        if name == "stop":
            await self._service.stop()
            await self._respond(command.command_id, True, {"message": "stopped"})
            return

        if name == "set_auto_reply":
            await self._service.update_auto_reply(
                _bool_value(params.get("enabled", "1"), True),
                params.get("payload", ""),
            )
            await self._respond(command.command_id, True, {"message": "updated"})
            return

        if name == "send":
            reply = await self._service.send(
                params.get("sf", ""),
                params.get("payload", ""),
                wait_reply=_bool_value(params.get("wait_reply", "0"), False),
                timeout=float(params.get("timeout", "10")),
            )
            response: Dict[str, str] = {"message": "sent"}
            if reply is not None:
                response["reply_sf"] = reply.sf
                response["reply_text"] = self._service.render_message(reply)
            await self._respond(command.command_id, True, response)
            return

        if name == "shutdown":
            self._running = False
            await self._service.stop()
            await self._respond(command.command_id, True, {"message": "bye"})
            return

        raise ValueError(f"Unsupported command: {command.name}")

    async def _respond(self, command_id: str, ok: bool, params: Dict[str, object]) -> None:
        await self._outbox.put(format_response(command_id, ok, params))


def main() -> None:
    asyncio.run(StdioBridgeServer().run())


if __name__ == "__main__":
    main()
