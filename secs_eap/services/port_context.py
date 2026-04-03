"""
Port runtime context store.

This module keeps the in-memory lifecycle data used during a carrier flow.
The store is intentionally lightweight and keyed by (eqpt_id, port_id).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime
from enum import Enum
from threading import RLock
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ..config import PortConfig


logger = logging.getLogger(__name__)


class PortType(str, Enum):
    """Supported port types."""

    LOADER = "loader"
    UNLOADER = "unloader"
    UNKNOWN = "unknown"

    @classmethod
    def from_value(cls, value: Any) -> "PortType":
        text = str(value or "").strip().lower()
        for item in cls:
            if item.value == text:
                return item
        return cls.UNKNOWN


class PortLifecycleState(str, Enum):
    """Lifecycle state of a port context."""

    ACTIVE = "active"
    OFFLINE = "offline"
    REMOVED = "removed"


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_port_key(value: Any) -> str:
    text = _normalize_text(value)
    if text.isdigit():
        return str(int(text))
    return text


def _job_id_timestamp(at: Optional[datetime] = None) -> str:
    current = at or datetime.now()
    return current.strftime("%Y%m%d%H%M%S%f")


def _build_job_id_pair(at: Optional[datetime] = None) -> Tuple[str, str]:
    token = _job_id_timestamp(at)
    return f"pj_{token}", f"cj_{token}"


def normalize_runtime_port_id(value: Any) -> str:
    """Normalize a runtime port id used by in-memory port contexts."""
    return _normalize_port_key(value)


def normalize_mes_port_id(value: Any) -> str:
    """Normalize a MES-facing port id."""
    text = _normalize_text(value)
    if text.isdigit():
        return str(int(text)).zfill(2)
    return text


def _build_port_id_candidates(value: Any) -> List[str]:
    raw_value = _normalize_text(value)
    candidates: List[str] = []
    for candidate in (
        raw_value,
        normalize_runtime_port_id(raw_value),
        normalize_mes_port_id(raw_value),
    ):
        if candidate and candidate not in candidates:
            candidates.append(candidate)
    return candidates


def _matches_expected_value(
    actual: Any,
    expected: Any,
    *,
    blank_is_match: bool = False,
) -> bool:
    expected_text = _normalize_text(expected)
    if not expected_text:
        return True

    actual_text = _normalize_text(actual)
    if not actual_text:
        return blank_is_match
    return actual_text == expected_text


def _first_non_empty(*values: Any) -> str:
    for value in values:
        text = _normalize_text(value)
        if text:
            return text
    return ""


def _object_to_dict(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if is_dataclass(value):
        result: Dict[str, Any] = {}
        for item in fields(value):
            result[item.name] = getattr(value, item.name)
        return result
    if hasattr(value, "__dict__"):
        return {
            key: attr
            for key, attr in vars(value).items()
            if not key.startswith("_")
        }
    return {}


def _payload_root(value: Any) -> Dict[str, Any]:
    """Return the most complete transaction mapping available."""
    payload = _object_to_dict(value)
    raw_payload = _normalize_text(payload.get("raw_payload"))
    if raw_payload:
        try:
            parsed = json.loads(raw_payload)
            if isinstance(parsed, dict):
                root = parsed.get("transaction", parsed)
                if isinstance(root, dict):
                    return dict(root)
        except Exception:
            pass

    root = payload.get("transaction", payload)
    if isinstance(root, dict):
        return dict(root)
    return payload


def _normalize_field_name(name: str) -> str:
    key = str(name or "").strip().lower()
    aliases = {
        "crr_id": "carrier_id",
        "port_typ": "port_type",
    }
    return aliases.get(key, key)


def _build_sheet_record(item: Any) -> "PortSheetContext":
    data = _object_to_dict(item)
    return PortSheetContext.from_mapping(data)


@dataclass
class PortSheetContext:
    """Per-sheet context embedded in APVRYOPE response."""

    slot_no: str = ""
    sht_id: str = ""
    product_id: str = ""
    sgr_id: str = ""
    vry_ope_proc_flg: str = ""
    rwk_cnt: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    def update_from_mapping(self, mapping: Dict[str, Any]) -> None:
        for key, value in mapping.items():
            field_name = _normalize_field_name(key)
            if field_name in {"slot_no", "sht_id", "product_id", "sgr_id", "vry_ope_proc_flg", "rwk_cnt"}:
                setattr(self, field_name, _normalize_text(value))
            elif field_name not in {"raw_payload", "transaction"}:
                self.extra[field_name] = value

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "slot_no": self.slot_no,
            "sht_id": self.sht_id,
            "product_id": self.product_id,
            "sgr_id": self.sgr_id,
            "vry_ope_proc_flg": self.vry_ope_proc_flg,
            "rwk_cnt": self.rwk_cnt,
        }
        if self.extra:
            payload["extra"] = dict(self.extra)
        return payload

    @classmethod
    def from_mapping(cls, mapping: Dict[str, Any]) -> "PortSheetContext":
        record = cls()
        record.update_from_mapping(mapping)
        return record


@dataclass
class PortRuntimeContext:
    """Runtime context for one equipment port."""

    eqpt_id: str = ""
    port_id: str = ""
    port_type: str = PortType.UNKNOWN.value
    lifecycle_state: str = PortLifecycleState.ACTIVE.value

    rtn_code: str = ""
    rtn_mesg: str = ""
    carrier_id: str = ""
    lot_id: str = ""
    splt_id: str = ""
    product_id: str = ""
    ec_code: str = ""
    user_id: str = ""

    nx_route_id: str = ""
    nx_route_ver: str = ""
    nx_proc_id: str = ""
    nx_ope_no: str = ""
    nx_ope_ver: str = ""
    nx_ope_dsc: str = ""
    nx_ope_id: str = ""

    prty: str = ""
    sht_cnt: str = ""
    pnl_cnt: str = ""
    recipe_id: str = ""
    prjob_id: str = ""
    cjob_id: str = ""
    rwk_cnt: str = ""
    max_rwk_cnt: str = ""
    ppbody: str = ""

    logof_eqpt_id: str = ""
    logof_port_id: str = ""
    logof_recipe_id: str = ""
    sgr_id: str = ""
    use_pfc_flg: str = ""
    mtrl_product_id: str = ""
    max_sht_cnt: str = ""
    ary_sht_cnt: str = ""

    lot_status: str = ""
    port_status: str = ""
    carrier_status: str = ""
    eqpt_status: str = ""

    last_tx_name: str = ""
    last_source: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    removed_at: Optional[datetime] = None

    sheets: List[PortSheetContext] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.ensure_job_ids()

    def key(self) -> Tuple[str, str]:
        return _normalize_text(self.eqpt_id), _normalize_text(self.port_id)

    def _has_job_id_context(self) -> bool:
        return bool(
            _normalize_text(self.carrier_id)
            or _normalize_text(self.lot_id)
            or _normalize_text(self.recipe_id)
            or list(self.sheets or [])
        )

    def ensure_job_ids(self) -> None:
        prjob_id = _normalize_text(self.prjob_id)
        cjob_id = _normalize_text(self.cjob_id)

        if not self._has_job_id_context():
            self.prjob_id = ""
            self.cjob_id = ""
            return

        if prjob_id and cjob_id:
            self.prjob_id = prjob_id
            self.cjob_id = cjob_id
            return

        suffix = ""
        if prjob_id.startswith("pj_") and len(prjob_id) > 3:
            suffix = prjob_id[3:]
        elif cjob_id.startswith("cj_") and len(cjob_id) > 3:
            suffix = cjob_id[3:]

        if not suffix:
            generated_prjob_id, generated_cjob_id = _build_job_id_pair()
            if not prjob_id:
                prjob_id = generated_prjob_id
            if not cjob_id:
                cjob_id = generated_cjob_id
        else:
            if not prjob_id:
                prjob_id = f"pj_{suffix}"
            if not cjob_id:
                cjob_id = f"cj_{suffix}"

        self.prjob_id = prjob_id
        self.cjob_id = cjob_id

    def touch(self, source: str = "") -> None:
        self.ensure_job_ids()
        self.updated_at = datetime.now()
        if source:
            self.last_source = source

    def update_from_mapping(
        self,
        mapping: Dict[str, Any],
        *,
        source: str = "",
        allow_empty: bool = True,
    ) -> None:
        for key, value in mapping.items():
            field_name = _normalize_field_name(key)
            if field_name in {"raw_payload", "transaction", "oary1"}:
                continue

            if hasattr(self, field_name):
                if value is None and not allow_empty:
                    continue
                setattr(self, field_name, _normalize_text(value))
            else:
                if value is not None or allow_empty:
                    self.extra[field_name] = value

        if source:
            self.last_tx_name = source
        self.ensure_job_ids()
        self.touch(source)

    def set_sheets(self, sheet_items: Iterable[Any]) -> None:
        self.sheets = [_build_sheet_record(item) for item in sheet_items]
        self.touch(self.last_tx_name)

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "eqpt_id": self.eqpt_id,
            "port_id": self.port_id,
            "port_type": self.port_type,
            "lifecycle_state": self.lifecycle_state,
            "rtn_code": self.rtn_code,
            "rtn_mesg": self.rtn_mesg,
            "carrier_id": self.carrier_id,
            "lot_id": self.lot_id,
            "splt_id": self.splt_id,
            "product_id": self.product_id,
            "ec_code": self.ec_code,
            "user_id": self.user_id,
            "nx_route_id": self.nx_route_id,
            "nx_route_ver": self.nx_route_ver,
            "nx_proc_id": self.nx_proc_id,
            "nx_ope_no": self.nx_ope_no,
            "nx_ope_ver": self.nx_ope_ver,
            "nx_ope_dsc": self.nx_ope_dsc,
            "nx_ope_id": self.nx_ope_id,
            "prty": self.prty,
            "sht_cnt": self.sht_cnt,
            "pnl_cnt": self.pnl_cnt,
            "recipe_id": self.recipe_id,
            "prjob_id": self.prjob_id,
            "cjob_id": self.cjob_id,
            "rwk_cnt": self.rwk_cnt,
            "max_rwk_cnt": self.max_rwk_cnt,
            "ppbody": self.ppbody,
            "logof_eqpt_id": self.logof_eqpt_id,
            "logof_port_id": self.logof_port_id,
            "logof_recipe_id": self.logof_recipe_id,
            "sgr_id": self.sgr_id,
            "use_pfc_flg": self.use_pfc_flg,
            "mtrl_product_id": self.mtrl_product_id,
            "max_sht_cnt": self.max_sht_cnt,
            "ary_sht_cnt": self.ary_sht_cnt,
            "lot_status": self.lot_status,
            "port_status": self.port_status,
            "carrier_status": self.carrier_status,
            "eqpt_status": self.eqpt_status,
            "last_tx_name": self.last_tx_name,
            "last_source": self.last_source,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "removed_at": self.removed_at.isoformat() if self.removed_at else None,
            "sheets": [sheet.to_dict() for sheet in self.sheets],
        }
        if self.extra:
            payload["extra"] = dict(self.extra)
        return payload

    @classmethod
    def from_mapping(
        cls,
        mapping: Dict[str, Any],
        *,
        eqpt_id: str = "",
        port_id: str = "",
        port_type: str = PortType.UNKNOWN.value,
        source: str = "",
    ) -> "PortRuntimeContext":
        record = cls(
            eqpt_id=_first_non_empty(mapping.get("eqpt_id"), mapping.get("EQPT_ID"), eqpt_id),
            port_id=_first_non_empty(mapping.get("port_id"), mapping.get("PORT_ID"), port_id),
            port_type=_first_non_empty(mapping.get("port_type"), mapping.get("PORT_TYPE"), port_type),
        )
        record.update_from_mapping(mapping, source=source)
        if "oary1" in mapping and isinstance(mapping.get("oary1"), list):
            record.set_sheets(mapping.get("oary1", []))
        return record


class PortContextStore:
    """In-memory store keyed by eqpt_id + port_id."""

    def __init__(
        self,
        port_configs: Optional[Iterable[PortConfig]] = None,
        default_eqpt_id: str = "",
    ):
        self._default_eqpt_id = _normalize_text(default_eqpt_id)
        self._lock = RLock()
        self._records: Dict[Tuple[str, str], PortRuntimeContext] = {}
        self._port_configs: Dict[Tuple[str, str], PortConfig] = {}

        if port_configs:
            self.register_ports(self._default_eqpt_id, port_configs)

    @property
    def default_eqpt_id(self) -> str:
        return self._default_eqpt_id

    @staticmethod
    def _key(eqpt_id: str, port_id: str) -> Tuple[str, str]:
        return _normalize_text(eqpt_id), _normalize_port_key(port_id)

    def register_ports(
        self,
        eqpt_id: str,
        port_configs: Iterable[PortConfig],
    ) -> None:
        eqpt_id = _normalize_text(eqpt_id)
        with self._lock:
            for config in port_configs:
                if not config.port_id:
                    continue
                self._port_configs[(eqpt_id, _normalize_port_key(config.port_id))] = config

    def get_port_config(self, eqpt_id: str, port_id: str) -> Optional[PortConfig]:
        key = self._key(eqpt_id, port_id)
        with self._lock:
            config = self._port_configs.get(key)
            if config:
                return config
            if self._default_eqpt_id:
                return self._port_configs.get((self._default_eqpt_id, key[1]))
            return None

    def get(self, eqpt_id: str, port_id: str) -> Optional[PortRuntimeContext]:
        with self._lock:
            record = self._records.get(self._key(eqpt_id, port_id))
            if record is not None:
                record.ensure_job_ids()
            return record

    def resolve_runtime_port_id(self, eqpt_id: str, port_id: Any) -> str:
        raw_port_id = _normalize_text(port_id)
        if not raw_port_id:
            return ""

        resolved_eqpt_id = _normalize_text(eqpt_id) or self._default_eqpt_id
        if self.get_port_config(resolved_eqpt_id, raw_port_id):
            return raw_port_id

        for candidate in _build_port_id_candidates(raw_port_id):
            if candidate == raw_port_id:
                continue
            if self.get_port_config(resolved_eqpt_id, candidate):
                return candidate
            if resolved_eqpt_id and self.get(resolved_eqpt_id, candidate):
                return candidate
        return raw_port_id

    def resolve_port_type(self, eqpt_id: str, port_id: str, port_type: str = "") -> str:
        resolved_port_type = _normalize_text(port_type)
        if resolved_port_type:
            return resolved_port_type
        if not _normalize_text(port_id):
            return ""

        port_config = self.get_port_config(eqpt_id, port_id)
        if port_config and port_config.port_type:
            return _normalize_text(port_config.port_type)

        record = self.find(eqpt_id=eqpt_id, port_id=port_id, direct_match_mode="any")
        if record and record.port_type:
            return _normalize_text(record.port_type)
        return ""

    def find(
        self,
        *,
        eqpt_id: str = "",
        port_id: str = "",
        carrier_id: str = "",
        lot_id: str = "",
        direct_match_mode: str = "strict",
    ) -> Optional[PortRuntimeContext]:
        """
        Find one port context by port/carrier/lot.

        ``direct_match_mode`` controls how the initial direct port lookup treats
        carrier/lot filters:
        - ``any``: ignore carrier/lot once the port is resolved.
        - ``soft``: allow blank carrier/lot on the matched record.
        - ``strict``: require carrier/lot to match when provided.
        """
        resolved_eqpt_id = _normalize_text(eqpt_id) or self._default_eqpt_id
        resolved_carrier_id = _normalize_text(carrier_id)
        resolved_lot_id = _normalize_text(lot_id)
        candidate_port_ids = _build_port_id_candidates(port_id)
        normalized_port_keys = {
            _normalize_port_key(candidate_port_id)
            for candidate_port_id in candidate_port_ids
            if candidate_port_id
        }

        direct_mode = _normalize_text(direct_match_mode).lower() or "strict"
        allow_blank_direct = direct_mode == "soft"
        check_direct_fields = direct_mode != "any"

        if candidate_port_ids and resolved_eqpt_id:
            for candidate_port_id in candidate_port_ids:
                record = self.get(resolved_eqpt_id, candidate_port_id)
                if record is None:
                    continue
                if check_direct_fields:
                    if not _matches_expected_value(
                        record.carrier_id,
                        resolved_carrier_id,
                        blank_is_match=allow_blank_direct,
                    ):
                        continue
                    if not _matches_expected_value(
                        record.lot_id,
                        resolved_lot_id,
                        blank_is_match=allow_blank_direct,
                    ):
                        continue
                return record

        for record in self.list_all():
            if resolved_eqpt_id and _normalize_text(record.eqpt_id) != resolved_eqpt_id:
                continue
            if normalized_port_keys and _normalize_port_key(record.port_id) not in normalized_port_keys:
                continue
            if not _matches_expected_value(record.carrier_id, resolved_carrier_id):
                continue
            if not _matches_expected_value(record.lot_id, resolved_lot_id):
                continue
            return record
        return None

    def list_all(self) -> List[PortRuntimeContext]:
        with self._lock:
            records = list(self._records.values())
            for record in records:
                record.ensure_job_ids()
            return records

    def snapshot(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            snapshot: Dict[str, Dict[str, Any]] = {}
            for (eqpt_id, port_id), record in self._records.items():
                record.ensure_job_ids()
                snapshot[f"{eqpt_id}:{port_id}"] = record.to_dict()
            return snapshot

    def get_or_create(
        self,
        eqpt_id: str,
        port_id: str,
        *,
        port_type: str = PortType.UNKNOWN.value,
    ) -> PortRuntimeContext:
        key = self._key(eqpt_id, port_id)
        with self._lock:
            record = self._records.get(key)
            if record is None:
                record = PortRuntimeContext(
                    eqpt_id=key[0],
                    port_id=key[1],
                    port_type=_normalize_text(port_type) or PortType.UNKNOWN.value,
                )
                self._records[key] = record
            else:
                record.ensure_job_ids()
            return record

    def upsert(self, record: PortRuntimeContext) -> PortRuntimeContext:
        key = self._key(record.eqpt_id, record.port_id)
        with self._lock:
            self._records[key] = record
            return record

    def update(self, eqpt_id: str, port_id: str, **changes: Any) -> Optional[PortRuntimeContext]:
        with self._lock:
            record = self._records.get(self._key(eqpt_id, port_id))
            if record is None:
                return None
            record.update_from_mapping(changes, source=changes.get("last_tx_name", ""), allow_empty=True)
            return record

    def capture_apvryope(self, request: Any, response: Any) -> PortRuntimeContext:
        request_map = _payload_root(request)
        response_map = _payload_root(response)

        eqpt_id = _first_non_empty(
            response_map.get("eqpt_id"),
            response_map.get("EQPT_ID"),
            request_map.get("eqpt_id"),
            request_map.get("EQPT_ID"),
            self._default_eqpt_id,
        )
        port_id = _first_non_empty(
            response_map.get("port_id"),
            response_map.get("PORT_ID"),
            request_map.get("port_id"),
            request_map.get("PORT_ID"),
        )
        port_cfg = self.get_port_config(eqpt_id, port_id)
        record = self.get_or_create(
            eqpt_id,
            port_id,
            port_type=port_cfg.port_type if port_cfg else PortType.UNKNOWN.value,
        )

        # Keep the APVRYOPE payload as the initial snapshot for later TX updates.
        record.eqpt_id = eqpt_id
        record.port_id = port_id
        if port_cfg:
            record.port_type = port_cfg.port_type
        record.update_from_mapping(response_map, source="APVRYOPE", allow_empty=True)
        record.carrier_id = _first_non_empty(
            response_map.get("crr_id"),
            response_map.get("carrier_id"),
            request_map.get("crr_id"),
            request_map.get("carrier_id"),
            record.carrier_id,
        )
        record.user_id = _first_non_empty(response_map.get("user_id"), request_map.get("user_id"), record.user_id)
        record.set_sheets(response_map.get("oary1", []) or [])
        record.lifecycle_state = PortLifecycleState.ACTIVE.value
        record.removed_at = None
        record.touch("APVRYOPE")
        return record

    def remove(self, eqpt_id: str, port_id: str, reason: str = "carrier_remove") -> Optional[PortRuntimeContext]:
        key = self._key(eqpt_id, port_id)
        with self._lock:
            record = self._records.pop(key, None)
            if record is None:
                return None
            record.lifecycle_state = PortLifecycleState.REMOVED.value
            record.last_tx_name = reason
            record.removed_at = datetime.now()
            record.touch(reason)
            return record

    def clear_by_carrier(self, carrier_id: str) -> List[PortRuntimeContext]:
        carrier_id = _normalize_text(carrier_id)
        if not carrier_id:
            return []

        removed: List[PortRuntimeContext] = []
        with self._lock:
            for key, record in list(self._records.items()):
                if record.carrier_id != carrier_id:
                    continue
                removed.append(self._records.pop(key))

        for record in removed:
            record.lifecycle_state = PortLifecycleState.REMOVED.value
            record.last_tx_name = "carrier_remove"
            record.removed_at = datetime.now()
            record.touch("carrier_remove")
        return removed

    def clear_equipment(self, eqpt_id: str = "", reason: str = "offline") -> List[PortRuntimeContext]:
        eqpt_id = _normalize_text(eqpt_id)
        removed: List[PortRuntimeContext] = []

        with self._lock:
            for key, record in list(self._records.items()):
                if eqpt_id and record.eqpt_id != eqpt_id:
                    continue
                removed.append(self._records.pop(key))

        for record in removed:
            record.lifecycle_state = PortLifecycleState.OFFLINE.value if reason == "offline" else PortLifecycleState.REMOVED.value
            record.last_tx_name = reason
            record.removed_at = datetime.now()
            record.touch(reason)
        return removed
