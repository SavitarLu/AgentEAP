"""
Java GUI 与 Python bridge 共用的轻量文本协议。

格式:
- CMD<TAB>id<TAB>name<TAB>querystring
- RESP<TAB>id<TAB>ok|error<TAB>querystring
- EVENT<TAB>kind<TAB>querystring
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict
from urllib.parse import parse_qsl, urlencode


@dataclass
class BridgeCommand:
    command_id: str
    name: str
    params: Dict[str, str] = field(default_factory=dict)


@dataclass
class BridgeResponse:
    command_id: str
    ok: bool
    params: Dict[str, str] = field(default_factory=dict)


@dataclass
class BridgeEvent:
    kind: str
    params: Dict[str, str] = field(default_factory=dict)


def encode_fields(fields: Dict[str, object]) -> str:
    prepared = {str(key): "" if value is None else str(value) for key, value in fields.items()}
    return urlencode(prepared, doseq=False)


def decode_fields(raw: str) -> Dict[str, str]:
    if not raw:
        return {}
    return {key: value for key, value in parse_qsl(raw, keep_blank_values=True)}


def format_command(command_id: str, name: str, params: Dict[str, object] | None = None) -> str:
    return "\t".join(["CMD", command_id, name, encode_fields(params or {})])


def format_response(command_id: str, ok: bool, params: Dict[str, object] | None = None) -> str:
    status = "ok" if ok else "error"
    return "\t".join(["RESP", command_id, status, encode_fields(params or {})])


def format_event(kind: str, params: Dict[str, object] | None = None) -> str:
    return "\t".join(["EVENT", kind, encode_fields(params or {})])


def parse_packet(line: str) -> BridgeCommand | BridgeResponse | BridgeEvent:
    stripped = line.rstrip("\r\n")
    parts = stripped.split("\t", 3)
    original_len = len(parts)
    while len(parts) < 4:
        parts.append("")

    packet_type = parts[0].upper()
    if packet_type == "CMD":
        return BridgeCommand(parts[1], parts[2], decode_fields(parts[3]))
    if packet_type == "RESP":
        return BridgeResponse(parts[1], parts[2].lower() == "ok", decode_fields(parts[3]))
    if packet_type == "EVENT":
        payload = parts[2] if original_len == 3 else parts[3]
        return BridgeEvent(parts[1], decode_fields(payload))
    raise ValueError(f"Unsupported packet type: {parts[0] or '<empty>'}")
