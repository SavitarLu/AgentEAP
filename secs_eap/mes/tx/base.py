"""
Shared helpers for Python MES TX codecs.
"""

from collections import OrderedDict
from dataclasses import fields, is_dataclass
from typing import Any, List, get_args, get_origin


def _is_dataclass_type(value: Any) -> bool:
    return isinstance(value, type) and is_dataclass(value)


def _lookup_value(mapping: dict, field_name: str) -> Any:
    if field_name in mapping:
        return mapping[field_name]

    upper_name = field_name.upper()
    if upper_name in mapping:
        return mapping[upper_name]

    return None


def _serialize_value(value: Any) -> Any:
    if is_dataclass(value):
        return _serialize_dataclass(value)
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    return value


def _serialize_dataclass(instance: Any) -> OrderedDict:
    payload = OrderedDict()
    for item in fields(instance):
        if item.name == "raw_payload":
            continue
        payload[item.name] = _serialize_value(getattr(instance, item.name))
    return payload


def _deserialize_value(type_hint: Any, value: Any) -> Any:
    origin = get_origin(type_hint)
    if origin in (list, List):
        item_type = get_args(type_hint)[0] if get_args(type_hint) else Any
        if not isinstance(value, list):
            return []
        return [_deserialize_value(item_type, item) for item in value]

    if _is_dataclass_type(type_hint):
        if isinstance(value, dict):
            return _build_dataclass(type_hint, value)
        return type_hint()

    return value


def _build_dataclass(cls, mapping: Any, raw_payload: str = ""):
    if not isinstance(mapping, dict):
        mapping = {}

    kwargs = {}
    for item in fields(cls):
        if item.name == "raw_payload":
            kwargs[item.name] = raw_payload
            continue

        raw_value = _lookup_value(mapping, item.name)
        if raw_value is None:
            continue
        kwargs[item.name] = _deserialize_value(item.type, raw_value)

    return cls(**kwargs)


def build_tx_dataclass(cls, mapping: Any, raw_payload: str = ""):
    """Public helper for building TX dataclass objects from workflow mappings."""
    return _build_dataclass(cls, mapping, raw_payload=raw_payload)


class TxRequestMixin:
    """Serialize dataclass request objects to transaction JSON payload."""

    def to_payload(self) -> OrderedDict:
        return OrderedDict([("transaction", _serialize_dataclass(self))])


class TxResponseMixin:
    """Deserialize transaction JSON payloads into dataclass responses."""

    @classmethod
    def from_payload(cls, payload: Any, raw_payload: str = ""):
        root = payload.get("transaction", payload) if isinstance(payload, dict) else {}
        return _build_dataclass(cls, root, raw_payload=raw_payload)
