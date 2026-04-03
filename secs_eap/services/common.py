"""
Shared helpers for workflow-callable service modules.
"""

from __future__ import annotations

import json
import logging
import re
import textwrap
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from secs_driver.src.secs_message import SECSItem, SECSMessage
from secs_driver.src.secs_types import SECSType, SECSTypeInfo

from ..config import EAPConfig
from ..mes.tx.apceqpst import APCEQPSTRequest
from ..mes.tx.apcnlogn import ApcnlogniA
from .port_context import PortContextStore
from .reply_meanings import format_reply_ack, is_reply_ack_accepted


class MesReplyError(RuntimeError):
    """Business-level MES reply failure with valid transport-level response."""


class SecsMessageError(RuntimeError):
    """Business-level SECS message build/send failure."""

    def __init__(
        self,
        message: str,
        *,
        reply: Optional[SECSMessage] = None,
        error_text: str = "",
    ):
        super().__init__(message)
        self.reply = reply
        self.error_text = str(error_text or "").strip()


@dataclass
class BuiltSecsTemplate:
    template_name: str
    direction: str
    stream: int
    function: int
    wait_reply: bool
    items: List[SECSItem]
    rendered_text: str


class EapApiBoundMixin:
    """Shared EAP binding helpers."""

    def __init__(self) -> None:
        self._eap_api: Any = None

    def bind_eap_api(self, eap_api: Any) -> None:
        self._eap_api = eap_api

    def _require_eap_api(self) -> Any:
        if self._eap_api is None:
            raise RuntimeError(f"{self.__class__.__name__} is not bound to EAP")
        return self._eap_api

    def _get_service_logger(self) -> logging.Logger:
        return logging.getLogger(self.__class__.__module__)

    @staticmethod
    def _to_bool(value: Any, default: bool = False) -> bool:
        if value in (None, ""):
            return default
        if isinstance(value, bool):
            return value

        text = str(value).strip().upper()
        if text in {"Y", "YES", "TRUE", "1", "ON"}:
            return True
        if text in {"N", "NO", "FALSE", "0", "OFF"}:
            return False
        return bool(value)


class CallMethodCommonMixin(EapApiBoundMixin):
    """Shared helper methods for workflow ``call_method`` services."""

    def __init__(
        self,
        config: EAPConfig,
        port_context_store: Optional[PortContextStore] = None,
        mes_equipment_id: str = "",
    ):
        super().__init__()
        self._config = config
        self._port_context_store = port_context_store
        self._mes_equipment_id = str(mes_equipment_id or "").strip()
        self._runtime_eqpt_mode: str = ""
        self._runtime_eqpt_status: str = ""

    @staticmethod
    def _to_yes_no_flag(value: Any, default: str = "N") -> str:
        if value in (None, ""):
            return default
        if isinstance(value, bool):
            return "Y" if value else "N"

        text = str(value).strip().upper()
        if not text:
            return default
        if text in {"Y", "YES", "TRUE", "1", "ON"}:
            return "Y"
        if text in {"N", "NO", "FALSE", "0", "OFF"}:
            return "N"
        return text

    @staticmethod
    def _normalize_upper_text(value: Any) -> str:
        return str(value or "").strip().upper()

    @staticmethod
    def _is_zero_code(value: Any) -> bool:
        text = str(value or "").strip()
        if not text:
            return True
        return text.strip("0") == ""

    @classmethod
    def _plain_object(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: cls._plain_object(item) for key, item in value.items()}
        if isinstance(value, list):
            return [cls._plain_object(item) for item in value]
        if hasattr(value, "__dict__"):
            return {
                key: cls._plain_object(item)
                for key, item in vars(value).items()
                if not key.startswith("_")
            }
        return value

    def _resolve_method_user_id(self, user_id: str = "") -> str:
        resolved = str(user_id or "").strip()
        if resolved:
            return resolved
        return str(self._config.equipment.user_id or "").strip()

    def _resolve_inquiry_eqpt_id(self, eqpt_id: str = "") -> str:
        resolved = str(eqpt_id or "").strip()
        if resolved:
            return resolved
        return self._mes_equipment_id or str(self._config.equipment.name or "").strip()

    @staticmethod
    def _resolve_port_call_args(
        *,
        port_type: str = "",
        port_id: str = "",
        carrier_id: str = "",
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        params = dict(kwargs or {})
        return {
            "port_type": str(port_type or params.get("port_type") or "").strip(),
            "port_id": str(port_id or params.get("port_id") or "").strip(),
            "carrier_id": str(carrier_id or params.get("carrier_id") or "").strip(),
        }

    def _resolve_current_eqpt_mode(self, eqpt_id: str = "") -> str:
        if self._runtime_eqpt_mode:
            return self._runtime_eqpt_mode

        if not self._port_context_store:
            return ""

        target_eqpt_id = str(eqpt_id or "").strip()
        for record in self._port_context_store.list_all():
            if target_eqpt_id and record.eqpt_id != target_eqpt_id:
                continue
            current = self._normalize_upper_text(record.extra.get("eqpt_mode"))
            if current:
                return current
        return ""

    @staticmethod
    def _resolve_eqpt_sub_stat(eqpt_stat: str) -> str:
        mapping = {
            "RUN": "1000",
            "IDLE": "2000",
            "DOWN": "5000",
        }
        return mapping.get(str(eqpt_stat or "").strip().upper(), "")

    @classmethod
    def _ensure_tx_success(cls, tx_name: str, response: Any) -> None:
        if response is None:
            raise RuntimeError(f"{tx_name} returned no response")

        if hasattr(response, "rtn_code"):
            rtn_code = str(getattr(response, "rtn_code", "") or "").strip()
            if not cls._is_zero_code(rtn_code):
                rtn_mesg = str(getattr(response, "rtn_mesg", "") or "").strip()
                raise MesReplyError(
                    f"{tx_name} failed: rtn_code={rtn_code} rtn_mesg={rtn_mesg or '-'}"
                )

    async def _execute_apceqpst(self, **payload: Any) -> Any:
        eap_api = self._require_eap_api()
        request = APCEQPSTRequest(**payload)
        response = await eap_api.execute_mes_tx("APCEQPST", request)
        self._ensure_tx_success("APCEQPST", response)
        return response

    def _update_runtime_eqpt_mode_status(self, mode: str = "", stat: str = "") -> None:
        resolved_mode = self._normalize_upper_text(mode)
        resolved_stat = self._normalize_upper_text(stat)
        if resolved_mode:
            self._runtime_eqpt_mode = resolved_mode
        if resolved_stat:
            self._runtime_eqpt_status = resolved_stat

    def _refresh_eqpt_port_contexts(
        self,
        eqpt_id: str,
        *,
        eqpt_mode: str = "",
        eqpt_status: str = "",
        reset_for_manual: bool = False,
    ) -> None:
        if not self._port_context_store:
            return

        if reset_for_manual:
            self._port_context_store.clear_equipment(eqpt_id=eqpt_id, reason="manual_mode")

        port_ids = {
            str(port.port_id or "").strip()
            for port in (self._config.equipment.ports or [])
            if str(port.port_id or "").strip()
        }
        for record in self._port_context_store.list_all():
            if record.eqpt_id != eqpt_id:
                continue
            if record.port_id:
                port_ids.add(record.port_id)

        for port_id in sorted(port_ids):
            port_type = self._port_context_store.resolve_port_type(eqpt_id, port_id, "")
            record = self._port_context_store.get_or_create(
                eqpt_id,
                port_id,
                port_type=port_type or "unknown",
            )
            if port_type:
                record.port_type = port_type

            if reset_for_manual:
                for field_name in (
                    "rtn_code",
                    "rtn_mesg",
                    "carrier_id",
                    "lot_id",
                    "splt_id",
                    "product_id",
                    "ec_code",
                    "user_id",
                    "nx_route_id",
                    "nx_route_ver",
                    "nx_proc_id",
                    "nx_ope_no",
                    "nx_ope_ver",
                    "nx_ope_dsc",
                    "nx_ope_id",
                    "prty",
                    "sht_cnt",
                    "pnl_cnt",
                    "recipe_id",
                    "prjob_id",
                    "cjob_id",
                    "rwk_cnt",
                    "max_rwk_cnt",
                    "ppbody",
                    "logof_eqpt_id",
                    "logof_port_id",
                    "logof_recipe_id",
                    "sgr_id",
                    "use_pfc_flg",
                    "mtrl_product_id",
                    "max_sht_cnt",
                    "ary_sht_cnt",
                ):
                    setattr(record, field_name, "")
                record.sheets = []
                record.port_status = "UN"

            record.update_from_mapping(
                {
                    "eqpt_mode": eqpt_mode,
                    "eqpt_status": eqpt_status,
                },
                source="UPDATE_EQP_MODE_STATUS",
                allow_empty=True,
            )

    def _log_port_context_snapshot(self, reason: str) -> None:
        if not self._port_context_store:
            return

        logger = self._get_service_logger()
        try:
            snapshot = self._port_context_store.snapshot()
            logger.info(
                "Port context snapshot after %s:\n%s",
                reason,
                json.dumps(snapshot, ensure_ascii=False, indent=2),
            )
        except Exception as exc:
            logger.warning("Failed to dump port_context_store after %s: %s", reason, exc)

    @staticmethod
    def _clear_port_material_context(record: Any) -> None:
        for field_name in (
            "rtn_code",
            "rtn_mesg",
            "carrier_id",
            "lot_id",
            "splt_id",
            "product_id",
            "ec_code",
            "user_id",
            "nx_route_id",
            "nx_route_ver",
            "nx_proc_id",
            "nx_ope_no",
            "nx_ope_ver",
            "nx_ope_dsc",
            "nx_ope_id",
            "prty",
            "sht_cnt",
            "pnl_cnt",
            "recipe_id",
            "prjob_id",
            "cjob_id",
            "rwk_cnt",
            "max_rwk_cnt",
            "ppbody",
            "logof_eqpt_id",
            "logof_port_id",
            "logof_recipe_id",
            "sgr_id",
            "use_pfc_flg",
            "mtrl_product_id",
            "max_sht_cnt",
            "ary_sht_cnt",
        ):
            setattr(record, field_name, "")
        record.sheets = []

    def _attach_port_context(
        self,
        result: Dict[str, Any],
        eqpt_id: str,
        port_id: str,
    ) -> None:
        if not self._port_context_store:
            return
        record = self._port_context_store.get(eqpt_id, port_id)
        if record:
            result["port_context"] = record.to_dict()

    @staticmethod
    def _normalize_slot_no(slot_no: Any) -> str:
        text = str(slot_no or "").strip()
        if not text:
            return ""
        if text.isdigit():
            return str(int(text)).zfill(3)
        return text

    @classmethod
    def _build_apcnlogn_iary(
        cls,
        sheet_items: Any,
    ) -> list[ApcnlogniA]:
        result: list[ApcnlogniA] = []
        for item in sheet_items or []:
            data = cls._plain_object(item)
            sht_id = str(data.get("sht_id", "") or "").strip()
            slot_no = cls._normalize_slot_no(data.get("slot_no", ""))
            if not sht_id and not slot_no:
                continue
            result.append(
                ApcnlogniA(
                    sht_id=sht_id,
                    slot_no=slot_no,
                )
            )
        return result

    @classmethod
    def _normalize_slot_map_text(cls, slot_map: Any) -> str:
        if slot_map is None:
            return ""
        if isinstance(slot_map, (list, tuple)):
            return "".join(cls._normalize_slot_map_text(item) for item in slot_map)
        if isinstance(slot_map, bool):
            return "1" if slot_map else "0"

        text = str(slot_map).strip()
        if not text:
            return ""

        ignored_chars = {" ", ",", ";", "|", "-", "_", "\t", "\r", "\n"}
        return "".join(char for char in text if char not in ignored_chars)

    @classmethod
    def _parse_slot_map(cls, slot_map: Any) -> Tuple[str, List[int]]:
        normalized_text = cls._normalize_slot_map_text(slot_map)
        occupied_slots: List[int] = []
        normalized_flags: List[str] = []

        for index, char in enumerate(normalized_text, start=1):
            token = char.upper()
            if token in {"1", "Y", "T", "X"}:
                normalized_flags.append("1")
                occupied_slots.append(index)
                continue
            if token in {"0", "N", "F"}:
                normalized_flags.append("0")
                continue
            raise ValueError(f"Unsupported slot_map flag at position {index}: {char!r}")

        return "".join(normalized_flags), occupied_slots

    @classmethod
    def _build_expected_slot_map_from_port_context(
        cls,
        record: Any,
        *,
        capacity_hint: int = 0,
    ) -> Tuple[str, List[int], int]:
        expected_slots: List[int] = []
        for index, sheet in enumerate(list(getattr(record, "sheets", []) or []), start=1):
            slot_text = cls._normalize_slot_no(getattr(sheet, "slot_no", "") or "")
            slot_no = int(slot_text) if slot_text.isdigit() else index
            if slot_no > 0:
                expected_slots.append(slot_no)

        unique_slots = sorted(set(expected_slots))
        max_slot = max(unique_slots) if unique_slots else 0

        capacity = 0
        for candidate in (
            capacity_hint,
            int(str(getattr(record, "max_sht_cnt", "") or "0")) if str(getattr(record, "max_sht_cnt", "") or "").isdigit() else 0,
            int(str(getattr(record, "ary_sht_cnt", "") or "0")) if str(getattr(record, "ary_sht_cnt", "") or "").isdigit() else 0,
            max_slot,
        ):
            if candidate > capacity:
                capacity = candidate

        if capacity <= 0:
            return "", unique_slots, 0

        flags = ["0"] * capacity
        for slot_no in unique_slots:
            if slot_no > capacity:
                raise ValueError(
                    f"Port context slot_no={slot_no} exceeds slot_map capacity={capacity}"
                )
            flags[slot_no - 1] = "1"
        return "".join(flags), unique_slots, capacity

    def VERIFY_SLOT_MAP_MATCHES_PORT_CONTEXT(
        self,
        port_id: str,
        slot_map: Any,
        *,
        carrier_id: str = "",
        eqpt_id: str = "",
        lot_id: str = "",
    ) -> Dict[str, Any]:
        """
        Verify event slot_map matches the MES-backed in-memory port context.

        This method is workflow-callable through ``call_method``.
        It raises ``ValueError`` when the physical slot map and port context differ.
        """
        store = self._port_context_store
        if not store:
            raise RuntimeError("verify_slot_map_matches_port_context requires port_context_store")

        resolved_eqpt_id = self._resolve_inquiry_eqpt_id(eqpt_id)
        raw_port_id = str(port_id or "").strip()
        resolved_port_id = store.resolve_runtime_port_id(resolved_eqpt_id, raw_port_id)
        resolved_carrier_id = str(carrier_id or "").strip()
        resolved_lot_id = str(lot_id or "").strip()

        if not resolved_port_id:
            raise ValueError("verify_slot_map_matches_port_context requires port_id")

        actual_slot_map, actual_slots = self._parse_slot_map(slot_map)
        if not actual_slot_map:
            raise ValueError("verify_slot_map_matches_port_context requires non-empty slot_map")

        record = store.find(
            eqpt_id=resolved_eqpt_id,
            port_id=resolved_port_id,
            carrier_id=resolved_carrier_id,
            lot_id=resolved_lot_id,
            direct_match_mode="soft",
        )
        if record is None:
            raise ValueError(
                "verify_slot_map_matches_port_context could not resolve "
                f"port_context for eqpt_id={resolved_eqpt_id} port_id={resolved_port_id} "
                f"carrier_id={resolved_carrier_id or '-'}"
            )

        expected_slot_map, expected_slots, capacity = self._build_expected_slot_map_from_port_context(
            record,
            capacity_hint=len(actual_slot_map),
        )
        if not expected_slots:
            raise ValueError(
                "verify_slot_map_matches_port_context requires at least one sheet "
                f"in port_context for carrier_id={resolved_carrier_id or getattr(record, 'carrier_id', '')}"
            )

        if len(actual_slot_map) != capacity:
            raise ValueError(
                "slot_map capacity mismatch: "
                f"actual_len={len(actual_slot_map)} expected_len={capacity} "
                f"actual={actual_slot_map} expected={expected_slot_map}"
            )

        matched = actual_slot_map == expected_slot_map
        result = {
            "result": 0 if matched else 1,
            "matched": matched,
            "eqpt_id": resolved_eqpt_id,
            "port_id": str(getattr(record, "port_id", "") or "").strip(),
            "carrier_id": str(getattr(record, "carrier_id", "") or "").strip(),
            "lot_id": str(getattr(record, "lot_id", "") or "").strip(),
            "actual_slot_map": actual_slot_map,
            "expected_slot_map": expected_slot_map,
            "actual_slots": actual_slots,
            "expected_slots": expected_slots,
            "capacity": capacity,
            "port_context": record.to_dict() if hasattr(record, "to_dict") else {},
        }

        logger = self._get_service_logger()
        logger.info(
            "verify_slot_map_matches_port_context: eqpt_id=%s port_id=%s carrier_id=%s "
            "actual=%s expected=%s matched=%s",
            result["eqpt_id"],
            result["port_id"],
            result["carrier_id"],
            actual_slot_map,
            expected_slot_map,
            matched,
        )

        if not matched:
            raise ValueError(
                "slot_map mismatch with port_context: "
                f"actual={actual_slot_map} expected={expected_slot_map} "
                f"actual_slots={actual_slots} expected_slots={expected_slots}"
            )
        return result


class SecsMessageCommonMixin(EapApiBoundMixin):
    """Shared helper methods for workflow SECS template services."""

    TEMPLATES: Dict[str, str] = {}
    _HEADER_RE = re.compile(
        r"^S(?P<stream>\d+)F(?P<function>\d+)(?:\s+(?P<wbit>W))?$",
        re.IGNORECASE,
    )
    _ACK_ITEM_PATHS: Dict[str, Tuple[int, ...]] = {
        "S1F14": (1, 1),
        "S1F18": (1,),
        "S2F16": (1,),
        "S2F32": (1,),
        "S2F34": (1,),
        "S2F36": (1,),
        "S2F38": (1,),
        "S2F42": (1, 1),
        "S2F44": (1, 1),
        "S2F46": (1, 1),
        "S2F50": (1, 1),
        "S3F18": (1, 1),
        "S3F20": (1, 1),
        "S3F22": (1, 1),
        "S3F24": (1, 1),
        "S3F26": (1, 1),
        "S3F28": (1, 1),
        "S3F30": (1, 1),
        "S3F32": (1, 1),
        "S5F4": (1,),
        "S6F24": (1,),
        "S14F2": (1, 2, 1),
        "S14F4": (1, 2, 1),
        "S14F6": (1, 2, 1),
        "S14F8": (1, 2, 1),
        "S14F10": (1, 3, 1),
        "S14F12": (1, 2, 1),
        "S14F14": (1, 3, 1),
        "S14F16": (1, 2, 1),
        "S14F18": (1, 2, 1),
        "S14F26": (1, 2, 1),
        "S14F28": (1, 2, 1),
        "S16F12": (1, 2, 1),
        "S16F16": (1, 2, 1),
    }

    @staticmethod
    def _is_numeric_text(value: str) -> bool:
        text = str(value or "").strip()
        if not text:
            return False
        if text[0] in {"+", "-"}:
            return text[1:].isdigit()
        return text.isdigit()

    @classmethod
    def _build_auto_item(cls, value: Any) -> SECSItem:
        if isinstance(value, SECSItem):
            return value
        if isinstance(value, bool):
            return SECSItem.boolean(value)
        if isinstance(value, int):
            if value < 0:
                return SECSItem.int4(value)
            return SECSItem.uint4(value)
        if isinstance(value, float):
            return SECSItem.float4(value)
        if isinstance(value, bytes):
            return SECSItem.binary(value)

        text = "" if value is None else str(value).strip()
        return SECSItem.ascii(text)

    @staticmethod
    def _parse_binary_value(raw: Any) -> bytes:
        if isinstance(raw, bytes):
            return raw
        text = str(raw or "").strip()
        if not text:
            return b""
        parts = text.replace(",", " ").split()
        data = bytearray()
        for part in parts:
            token = part.strip()
            if not token:
                continue
            if token.lower().startswith("0x"):
                token = token[2:]
            data.append(int(token, 16))
        return bytes(data)

    @classmethod
    def _convert_value_by_type(cls, item_type: str, raw_value: Any) -> Any:
        type_name = str(item_type or "").strip().upper()
        if type_name in {"A", "ASCII"}:
            return "" if raw_value is None else str(raw_value)
        if type_name in {"J", "JIS8"}:
            return "" if raw_value is None else str(raw_value)
        if type_name in {"BOOLEAN", "BOOL", "BL"}:
            if isinstance(raw_value, str):
                return raw_value.strip().upper() in {"1", "T", "TRUE", "Y", "YES", "ON"}
            return bool(raw_value)
        if type_name == "U1":
            text = str(raw_value or "").strip()
            if not text:
                raise SecsMessageError("U1 value is blank")
            if not text.isdigit():
                raise SecsMessageError(f"U1 value must be numeric: {raw_value}")
            value = int(text)
            if value < 0 or value > 255:
                raise SecsMessageError(f"U1 value out of range: {raw_value}")
            return value
        if type_name == "U2":
            return int(raw_value or 0)
        if type_name == "U4":
            return int(raw_value or 0)
        if type_name == "U8":
            return int(raw_value or 0)
        if type_name == "I1":
            return int(raw_value or 0)
        if type_name == "I2":
            return int(raw_value or 0)
        if type_name == "I4":
            return int(raw_value or 0)
        if type_name == "I8":
            return int(raw_value or 0)
        if type_name == "F4":
            return float(raw_value or 0)
        if type_name == "F8":
            return float(raw_value or 0)
        if type_name == "B":
            return cls._parse_binary_value(raw_value)
        raise SecsMessageError(f"Unsupported SECS item type in template: {item_type}")

    @classmethod
    def _build_typed_item(cls, item_type: str, raw_value: Any) -> SECSItem:
        type_name = str(item_type or "").strip().upper()
        converted_value = cls._convert_value_by_type(type_name, raw_value)
        if type_name in {"A", "ASCII"}:
            return SECSItem.ascii(converted_value)
        if type_name in {"J", "JIS8"}:
            return SECSItem.jis8(converted_value)
        if type_name in {"BOOLEAN", "BOOL", "BL"}:
            return SECSItem.boolean(converted_value)
        if type_name == "U1":
            return SECSItem.uint1(converted_value)
        if type_name == "U2":
            return SECSItem.uint2(converted_value)
        if type_name == "U4":
            return SECSItem.uint4(converted_value)
        if type_name == "U8":
            return SECSItem.uint8(converted_value)
        if type_name == "I1":
            return SECSItem.int1(converted_value)
        if type_name == "I2":
            return SECSItem.int2(converted_value)
        if type_name == "I4":
            return SECSItem.int4(converted_value)
        if type_name == "I8":
            return SECSItem.int8(converted_value)
        if type_name == "F4":
            return SECSItem.float4(converted_value)
        if type_name == "F8":
            return SECSItem.float8(converted_value)
        if type_name == "B":
            return SECSItem.binary(converted_value)
        raise SecsMessageError(f"Unsupported SECS item type in template: {item_type}")

    @staticmethod
    def _parse_scalar_literal(raw_value: str) -> Any:
        text = str(raw_value or "").strip()
        if not text:
            return ""
        if (text.startswith("'") and text.endswith("'")) or (
            text.startswith('"') and text.endswith('"')
        ):
            return text[1:-1]
        return text

    @staticmethod
    def _render_atom(item: SECSItem) -> str:
        item_type = SECSTypeInfo.get_name(item.type)
        if item.type == SECSType.ASCII:
            value = str(item.value or "").replace("'", "\\'")
            return f"<{item_type} '{value}'>"
        if item.type == SECSType.JIS8:
            value = str(item.value or "").replace("'", "\\'")
            return f"<{item_type} '{value}'>"
        if item.type == SECSType.BOOLEAN:
            return f"<{item_type} {'TRUE' if bool(item.value) else 'FALSE'}>"
        if item.type == SECSType.BINARY:
            value = " ".join(f"0x{byte:02X}" for byte in (item.value or b""))
            return f"<{item_type} {value}>".rstrip()
        return f"<{item_type} {item.value}>"

    @classmethod
    def _render_items(cls, items: List[SECSItem], indent: int = 4) -> List[str]:
        lines: List[str] = []
        prefix = " " * indent
        for item in items:
            if item.type == SECSType.LIST:
                lines.append(f"{prefix}L, {len(item.children)}")
                lines.extend(cls._render_items(item.children, indent=indent + 4))
            else:
                lines.append(f"{prefix}{cls._render_atom(item)}")
        return lines

    @staticmethod
    def _split_atom_content(content: str) -> Tuple[str, str]:
        text = str(content or "").strip()
        if not text:
            raise SecsMessageError("Empty SECS atom definition")
        parts = text.split(None, 1)
        if len(parts) == 1:
            return parts[0], ""
        return parts[0], parts[1]

    @staticmethod
    def _resolve_variable(name: str, variables: Dict[str, Any]) -> Any:
        if name in variables:
            return variables[name]
        raise SecsMessageError(f"Missing SECS template variable: {name}")

    @staticmethod
    def _reply_item_by_path(reply: Optional[SECSMessage], path: Tuple[int, ...]) -> Optional[SECSItem]:
        if not reply or not reply.items or not path:
            return None

        current: Optional[SECSItem] = None
        for depth, index_1based in enumerate(path):
            index = index_1based - 1
            if depth == 0:
                if index < 0 or index >= len(reply.items):
                    return None
                current = reply.items[index]
                continue

            if current is None or current.type != SECSType.LIST:
                return None
            if index < 0 or index >= len(current.children):
                return None
            current = current.children[index]
        return current

    @staticmethod
    def _extract_ack_from_item(item: Optional[SECSItem]) -> Optional[int]:
        if item is None:
            return None
        if item.type == SECSType.LIST:
            for child in item.children or []:
                ack_code = SecsMessageCommonMixin._extract_ack_from_item(child)
                if ack_code is not None:
                    return ack_code
            return None

        value = item.value
        try:
            if item.type == SECSType.BOOLEAN:
                return 1 if bool(value) else 0
            if isinstance(value, bytes):
                return value[0] if value else 0
            if isinstance(value, bool):
                return 1 if value else 0
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return int(value)
        except Exception:
            return None
        return None

    @classmethod
    def _extract_ack_code(cls, reply: Optional[SECSMessage]) -> Optional[int]:
        if not reply or not reply.items:
            return None
        reply_sf = str(getattr(reply, "sf", "") or "").upper()
        ack_path = cls._ACK_ITEM_PATHS.get(reply_sf)
        if ack_path:
            ack_item = cls._reply_item_by_path(reply, ack_path)
            ack_code = cls._extract_ack_from_item(ack_item)
            if ack_code is not None:
                return ack_code
        for item in reply.items:
            ack_code = cls._extract_ack_from_item(item)
            if ack_code is not None:
                return ack_code
        return None

    @classmethod
    def _flatten_item_texts(cls, item: Optional[SECSItem]) -> List[str]:
        if item is None:
            return []
        if item.type == SECSType.LIST:
            texts: List[str] = []
            for child in item.children or []:
                texts.extend(cls._flatten_item_texts(child))
            return texts

        value = item.value
        if value is None:
            return []
        if isinstance(value, bytes):
            text = value.hex().upper()
        else:
            text = str(value).strip()
        return [text] if text else []

    @classmethod
    def _extract_reply_error_text(
        cls,
        reply: Optional[SECSMessage],
        ack_text: str = "",
    ) -> str:
        if not reply:
            return str(ack_text or "no reply").strip()

        detail_texts: List[str] = []
        for item in (reply.items or [])[1:]:
            detail_texts.extend(cls._flatten_item_texts(item))

        normalized_details = [text for text in detail_texts if text]
        if normalized_details:
            return " | ".join(normalized_details)
        return str(ack_text or reply.sf).strip()

    @classmethod
    def _ensure_reply_ack_zero(cls, template_name: str, reply: Optional[SECSMessage]) -> None:
        ack_code = cls._extract_ack_code(reply)
        reply_sf = reply.sf if reply else ""
        ack_text = format_reply_ack(reply_sf, ack_code)
        if not is_reply_ack_accepted(reply_sf, ack_code):
            error_text = cls._extract_reply_error_text(reply, ack_text)
            raise SecsMessageError(
                f"SECS template {template_name} failed: {error_text}",
                reply=reply,
                error_text=error_text,
            )

    @classmethod
    def _parse_atom(cls, content: str, variables: Dict[str, Any]) -> SECSItem:
        text = str(content or "").strip()
        if text.startswith("$"):
            variable_name = text[1:]
            return cls._build_auto_item(cls._resolve_variable(variable_name, variables))

        item_type, raw_value = cls._split_atom_content(text)
        raw_value = str(raw_value or "").strip()
        if raw_value.startswith("$"):
            value = cls._resolve_variable(raw_value[1:], variables)
        else:
            value = cls._parse_scalar_literal(raw_value)
        return cls._build_typed_item(item_type, value)

    @classmethod
    def _parse_items_block(
        cls,
        lines: List[str],
        start_index: int,
        current_indent: Optional[int],
        variables: Dict[str, Any],
    ) -> Tuple[List[SECSItem], int]:
        items: List[SECSItem] = []
        index = start_index
        indent_level = current_indent

        while index < len(lines):
            raw_line = lines[index]
            if not raw_line.strip():
                index += 1
                continue

            indent = len(raw_line) - len(raw_line.lstrip(" "))
            if indent_level is None:
                indent_level = indent
            if indent < indent_level:
                break
            if indent > indent_level:
                raise SecsMessageError(
                    f"Unexpected SECS template indentation: {raw_line.strip()}"
                )

            line = raw_line.strip()
            if line.upper().startswith("L,"):
                try:
                    declared_count = int(line.split(",", 1)[1].strip())
                except Exception as exc:
                    raise SecsMessageError(f"Invalid LIST definition: {line}") from exc

                index += 1
                children: List[SECSItem] = []
                if index < len(lines):
                    next_indent = len(lines[index]) - len(lines[index].lstrip(" "))
                    if next_indent > indent:
                        children, index = cls._parse_items_block(
                            lines,
                            index,
                            next_indent,
                            variables,
                        )

                if declared_count != len(children):
                    raise SecsMessageError(
                        "SECS LIST size mismatch: "
                        f"declared={declared_count} actual={len(children)} line={line}"
                    )
                items.append(SECSItem.list_(children))
                continue

            if line.startswith("<") and line.endswith(">"):
                items.append(cls._parse_atom(line[1:-1], variables))
                index += 1
                continue

            raise SecsMessageError(f"Unsupported SECS template line: {line}")

        return items, index

    @classmethod
    def _normalize_script(cls, script: str) -> List[str]:
        return [
            line.rstrip()
            for line in textwrap.dedent(str(script or "")).splitlines()
            if line.strip()
        ]

    @classmethod
    def build_from_script(
        cls,
        script: str,
        *,
        template_name: str = "",
        variables: Optional[Dict[str, Any]] = None,
    ) -> BuiltSecsTemplate:
        lines = cls._normalize_script(script)
        if not lines:
            raise SecsMessageError("Empty SECS template script")

        index = 0
        resolved_name = str(template_name or "").strip()

        first_line = lines[index].strip()
        if (first_line.startswith('"') and first_line.endswith('"')) or (
            first_line.startswith("'") and first_line.endswith("'")
        ):
            resolved_name = resolved_name or first_line[1:-1]
            index += 1

        if index >= len(lines):
            raise SecsMessageError("SECS template missing direction/header")

        direction = lines[index].strip().upper()
        if direction not in {"SEND", "RECV"}:
            raise SecsMessageError(
                f"SECS template missing SEND/RECV line: {lines[index].strip()}"
            )
        index += 1

        if index >= len(lines):
            raise SecsMessageError("SECS template missing message header")

        header_line = lines[index].strip()
        if not header_line.startswith("{"):
            raise SecsMessageError(
                f"SECS template header must start with '{{': {header_line}"
            )
        header = header_line[1:].strip()
        index += 1

        if not header:
            if index >= len(lines):
                raise SecsMessageError("SECS template missing SxFy header after '{'")
            header = lines[index].strip()
            index += 1

        if index >= len(lines) or lines[-1].strip() != "}":
            raise SecsMessageError("SECS template must end with '}'")

        match = cls._HEADER_RE.match(header)
        if not match:
            raise SecsMessageError(f"Invalid SECS header: {header}")

        stream = int(match.group("stream"))
        function = int(match.group("function"))
        wait_reply = bool(match.group("wbit"))

        body_lines = lines[index:-1]
        items: List[SECSItem] = []
        if body_lines:
            items, next_index = cls._parse_items_block(
                body_lines,
                0,
                None,
                dict(variables or {}),
            )
            if next_index != len(body_lines):
                raise SecsMessageError(
                    "SECS template parsing did not consume all body lines"
                )

        rendered_lines = [
            f'"{resolved_name}"' if resolved_name else None,
            direction,
            f"{{ S{stream}F{function}{' W' if wait_reply else ''}",
        ]
        rendered_lines = [line for line in rendered_lines if line]
        rendered_lines.extend(cls._render_items(items, indent=4))
        rendered_lines.append("}")

        return BuiltSecsTemplate(
            template_name=resolved_name or f"S{stream}F{function}",
            direction=direction,
            stream=stream,
            function=function,
            wait_reply=wait_reply,
            items=items,
            rendered_text="\n".join(rendered_lines),
        )

    @classmethod
    def _collect_template_variables(
        cls,
        variables: Optional[Dict[str, Any]] = None,
        extra_kwargs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        merged = dict(variables or {})
        for key, value in (extra_kwargs or {}).items():
            if key in {"template_name", "script", "variables", "wait_reply", "timeout"}:
                continue
            merged[key] = value
        return merged

    @classmethod
    def _get_template_script(cls, template_name: str) -> str:
        template = cls.TEMPLATES.get(str(template_name or "").strip())
        if not template:
            raise SecsMessageError(f"Unknown SECS template: {template_name}")
        return template

    def _get_port_context_store(self) -> PortContextStore:
        eap_api = self._require_eap_api()
        store = getattr(eap_api, "port_context_store", None)
        if store is None:
            raise SecsMessageError("port_context_store is not available")
        return store

    @staticmethod
    def _sheet_sort_key(sheet: Any, index: int) -> Tuple[int, Any, int]:
        slot_no = str(getattr(sheet, "slot_no", "") or "").strip()
        if slot_no.isdigit():
            return (0, int(slot_no), index)
        if slot_no:
            return (1, slot_no, index)
        return (2, index, index)

    def _build_slot_map_body(
        self,
        *,
        lot_id: str,
        sheets: List[Any],
        capacity: int,
    ) -> SECSItem:
        content_map_entries: List[SECSItem] = []
        for sheet in sheets[:capacity]:
            sht_id = str(getattr(sheet, "sht_id", "") or "").strip()
            if not sht_id:
                raise SecsMessageError("Slot map contains blank sht_id in port_context")
            content_map_entries.append(
                SECSItem.list_([
                    SECSItem.ascii(lot_id),
                    SECSItem.ascii(sht_id),
                ])
            )

        return SECSItem.list_([
            SECSItem.list_([
                SECSItem.ascii("Capacity"),
                SECSItem.uint1(capacity),
            ]),
            SECSItem.list_([
                SECSItem.ascii("ContentMap"),
                SECSItem.list_(content_map_entries),
            ]),
        ])

    def _ordered_port_context_sheets(self, record: Any) -> List[Any]:
        return [
            item
            for index, item in sorted(
                enumerate(list(getattr(record, "sheets", []) or [])),
                key=lambda pair: self._sheet_sort_key(pair[1], pair[0]),
            )
        ]

    def _resolve_port_context_record(
        self,
        *,
        method_name: str,
        eqpt_id: str = "",
        port_id: str = "",
        carrier_id: str = "",
        lot_id: str = "",
        direct_match_mode: str = "soft",
    ) -> Any:
        record = self._get_port_context_store().find(
            eqpt_id=str(eqpt_id or "").strip(),
            port_id=port_id,
            carrier_id=str(carrier_id or "").strip(),
            lot_id=str(lot_id or "").strip(),
            direct_match_mode=direct_match_mode,
        )
        if record is None:
            raise SecsMessageError(
                f"{method_name} could not resolve port_context for "
                f"port_id={port_id} carrier_id={str(carrier_id or '').strip() or '-'}"
            )
        return record

    def _port_context_slot_numbers(self, record: Any) -> List[int]:
        slot_numbers: List[int] = []
        for index, sheet in enumerate(self._ordered_port_context_sheets(record), start=1):
            slot_text = str(getattr(sheet, "slot_no", "") or "").strip()
            if slot_text.isdigit():
                slot_no = int(slot_text)
            else:
                slot_no = index
            if slot_no <= 0 or slot_no > 255:
                raise SecsMessageError(f"Invalid slot_no in port_context: {slot_text or slot_no}")
            slot_numbers.append(slot_no)
        return slot_numbers

    def _build_slot_no_list_item(self, slot_numbers: List[int]) -> SECSItem:
        return SECSItem.list_([SECSItem.uint1(slot_no) for slot_no in slot_numbers])

    def _build_multiple_process_job_body(
        self,
        *,
        prjob_id: str,
        carrier_id: str,
        recipe_id: str,
        slot_numbers: List[int],
    ) -> SECSItem:
        return SECSItem.list_([
            SECSItem.list_([
                SECSItem.ascii(prjob_id),
                SECSItem.binary(b"\x0D"),
                SECSItem.list_([
                    SECSItem.list_([
                        SECSItem.ascii(carrier_id),
                        self._build_slot_no_list_item(slot_numbers),
                    ]),
                ]),
                SECSItem.list_([
                    SECSItem.uint1(1),
                    SECSItem.ascii(recipe_id),
                    SECSItem.list_([]),
                ]),
                SECSItem.boolean(True),
                SECSItem.list_([]),
            ])
        ])

    def _build_create_control_job_body(
        self,
        *,
        cjob_id: str,
        carrier_id: str,
        prjob_id: str,
    ) -> SECSItem:
        return SECSItem.list_([
            SECSItem.list_([
                SECSItem.ascii("ObjID"),
                SECSItem.ascii(cjob_id),
            ]),
            SECSItem.list_([
                SECSItem.ascii("ProcessOrderMgmt"),
                SECSItem.uint1(1),
            ]),
            SECSItem.list_([
                SECSItem.ascii("StartMethod"),
                SECSItem.boolean(True),
            ]),
            SECSItem.list_([
                SECSItem.ascii("CarrierInputSpec"),
                SECSItem.list_([
                    SECSItem.ascii(carrier_id),
                ]),
            ]),
            SECSItem.list_([
                SECSItem.ascii("MtrlOutSpec"),
                SECSItem.list_([]),
            ]),
            SECSItem.list_([
                SECSItem.ascii("ProcessingCtrlSpec"),
                SECSItem.list_([
                    SECSItem.list_([
                        SECSItem.ascii(prjob_id),
                        SECSItem.list_([]),
                        SECSItem.list_([]),
                    ]),
                ]),
            ]),
            SECSItem.list_([
                SECSItem.ascii("PauseEvent"),
                SECSItem.list_([]),
            ]),
        ])

    def list_templates(self) -> Dict[str, str]:
        return dict(self.TEMPLATES)

    def render_secs_template(
        self,
        template_name: str,
        *,
        variables: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> str:
        template = self._get_template_script(template_name)
        built = self.build_from_script(
            template,
            template_name=str(template_name or "").strip(),
            variables=self._collect_template_variables(variables, kwargs),
        )
        return built.rendered_text

    def build_secs_template(
        self,
        template_name: str,
        *,
        variables: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        template = self._get_template_script(template_name)
        built = self.build_from_script(
            template,
            template_name=str(template_name or "").strip(),
            variables=self._collect_template_variables(variables, kwargs),
        )
        return {
            "template_name": built.template_name,
            "direction": built.direction,
            "stream": built.stream,
            "function": built.function,
            "wait_reply": built.wait_reply,
            "items": built.items,
            "rendered_text": built.rendered_text,
        }

    async def send_secs_script(
        self,
        script: str,
        *,
        template_name: str = "",
        variables: Optional[Dict[str, Any]] = None,
        wait_reply: Any = None,
        timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        eap_api = self._require_eap_api()
        built = self.build_from_script(
            script,
            template_name=str(template_name or "").strip(),
            variables=self._collect_template_variables(variables, kwargs),
        )
        if built.direction != "SEND":
            raise SecsMessageError(f"SECS script is not SEND direction: {built.direction}")

        resolved_wait_reply = (
            built.wait_reply
            if wait_reply in (None, "")
            else self._to_bool(wait_reply, built.wait_reply)
        )
        reply = await eap_api.send_message(
            stream=built.stream,
            function=built.function,
            items=built.items,
            wait_reply=resolved_wait_reply,
            timeout=timeout,
        )

        if resolved_wait_reply:
            expected_sf = f"S{built.stream}F{built.function + 1}"
            if reply is None:
                raise SecsMessageError(
                    f"SECS template {built.template_name} failed: no reply for {expected_sf}",
                    reply=reply,
                    error_text=f"no reply for {expected_sf}",
                )
            if reply.sf != expected_sf:
                raise SecsMessageError(
                    f"SECS template {built.template_name} failed: expected {expected_sf}, got {reply.sf}",
                    reply=reply,
                    error_text=f"expected {expected_sf}, got {reply.sf}",
                )

        return {
            "template_name": built.template_name,
            "stream": built.stream,
            "function": built.function,
            "wait_reply": resolved_wait_reply,
            "rendered_text": built.rendered_text,
            "reply": reply,
        }

    async def send_secs_template(
        self,
        template_name: str,
        *,
        variables: Optional[Dict[str, Any]] = None,
        wait_reply: Any = None,
        timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        template = self._get_template_script(template_name)
        return await self.send_secs_script(
            template,
            template_name=str(template_name or "").strip(),
            variables=variables,
            wait_reply=wait_reply,
            timeout=timeout,
            **kwargs,
        )
