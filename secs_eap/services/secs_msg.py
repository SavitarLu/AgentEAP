"""
Visual SECS message templates for workflow-driven host commands.
"""

from __future__ import annotations

import logging
import textwrap
from typing import Any, Dict, Optional

from .common import BuiltSecsTemplate, SecsMessageCommonMixin, SecsMessageError


logger = logging.getLogger(__name__)


class SecsMessageService(SecsMessageCommonMixin):
    """Build and send visual SECS message templates from YAML/workflow."""

    TEMPLATES: Dict[str, str] = {
        "S3F17_F18_ProceedWithCarrier": textwrap.dedent(
            """
            "S3F17_F18_ProceedWithCarrier"
            SEND
            { S3F17 W
                L, 5
                    <U2 1>
                    <A 'ProceedWithCarrier'>
                    <A $carrier_id>
                    <U1 $port_id>
                    L, 0
            }
            """
        ).strip(),
        "S3F17_F18_CancelCarrierAtPort": textwrap.dedent(
            """
            "S3F17_F18_CancelCarrierAtPort"
            SEND
            { S3F17 W
                L, 5
                    <U4 1>
                    <A 'CancelCarrierAtPort'>
                    <A ''>
                    <U1 $port_id>
                    L, 0
            }
            """
        ).strip(),
        "S3F17_F18_CancelCarrier": textwrap.dedent(
            """
            "S3F17_F18_CancelCarrier"
            SEND
            { S3F17 W
                L, 5
                    <U4 1>
                    <A 'CancelCarrier'>
                    <A $carrier_id>
                    <U1 $port_id>
                    L, 0
            }
            """
        ).strip(),
        "S16F15_F16_MultipleProcessJobCreate": textwrap.dedent(
            """
            "S16F15_F16_MultipleProcessJobCreate"
            SEND
            { S16F15 W
                L, 2
                    <U4 1>
                    <$multiple_process_job_body>
            }
            """
        ).strip(),
        "S14F9_F10_CreateControlJob": textwrap.dedent(
            """
            "S14F9_F10_CreateControlJob"
            SEND
            { S14F9 W
                L, 3
                    <A 'Equipment'>
                    <A 'ControlJob'>
                    <$create_control_job_body>
            }
            """
        ).strip(),
        "S3F17_F18_ProceedWithSlotMap": textwrap.dedent(
            """
            "S3F17_F18_ProceedWithSlotMap"
            SEND
            { S3F17 W
                L, 5
                    <U4 1>
                    <A 'ProceedWithCarrier'>
                    <A $carrier_id>
                    <U1 $port_id>
                    <$slot_map_body>
            }
            """
        ).strip(),
    }

    async def S3F17_F18_ProceedWithCarrier(
        self,
        carrier_id: str,
        port_id: str,
        *,
        wait_reply: Any = True,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        resolved_carrier_id = str(carrier_id or "").strip()
        resolved_port_id = self._convert_value_by_type("U1", port_id)
        if not resolved_carrier_id:
            raise ValueError("S3F17_F18_ProceedWithCarrier requires carrier_id")

        result = await self.send_secs_template(
            "S3F17_F18_ProceedWithCarrier",
            wait_reply=wait_reply,
            timeout=timeout,
            variables={
                "carrier_id": resolved_carrier_id,
                "port_id": resolved_port_id,
            },
        )
        if self._to_bool(wait_reply, default=True):
            self._ensure_reply_ack_zero("S3F17_F18_ProceedWithCarrier", result.get("reply"))
        return result

    async def S3F17_F18_CancelCarrierAtPort(
        self,
        port_id: str,
        *,
        wait_reply: Any = True,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        resolved_port_id = self._convert_value_by_type("U1", port_id)

        result = await self.send_secs_template(
            "S3F17_F18_CancelCarrierAtPort",
            wait_reply=wait_reply,
            timeout=timeout,
            variables={
                "port_id": resolved_port_id,
            },
        )
        if self._to_bool(wait_reply, default=True):
            self._ensure_reply_ack_zero("S3F17_F18_CancelCarrierAtPort", result.get("reply"))
        return result

    async def S3F17_F18_CancelCarrier(
        self,
        carrier_id: str,
        port_id: str,
        *,
        wait_reply: Any = True,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        resolved_carrier_id = str(carrier_id or "").strip()
        resolved_port_id = self._convert_value_by_type("U1", port_id)
        if not resolved_carrier_id:
            raise ValueError("S3F17_F18_CancelCarrier requires carrier_id")

        result = await self.send_secs_template(
            "S3F17_F18_CancelCarrier",
            wait_reply=wait_reply,
            timeout=timeout,
            variables={
                "carrier_id": resolved_carrier_id,
                "port_id": resolved_port_id,
            },
        )
        if self._to_bool(wait_reply, default=True):
            self._ensure_reply_ack_zero("S3F17_F18_CancelCarrier", result.get("reply"))
        return result

    async def S16F15_F16_MultipleProcessJobCreate(
        self,
        prjob_id: str = "",
        *,
        carrier_id: str = "",
        port_id: str = "",
        eqpt_id: str = "",
        recipe_id: str = "",
        wait_reply: Any = True,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        record = self._resolve_port_context_record(
            method_name="S16F15_F16_MultipleProcessJobCreate",
            eqpt_id=eqpt_id,
            port_id=port_id,
            carrier_id=carrier_id,
            direct_match_mode="soft",
        )
        resolved_prjob_id = str(prjob_id or getattr(record, "prjob_id", "") or "").strip()
        resolved_carrier_id = str(carrier_id or getattr(record, "carrier_id", "") or "").strip()
        resolved_recipe_id = str(recipe_id or getattr(record, "recipe_id", "") or "").strip()
        if not resolved_prjob_id:
            raise SecsMessageError("S16F15_F16_MultipleProcessJobCreate requires prjob_id in port_context")
        if not resolved_carrier_id:
            raise SecsMessageError("S16F15_F16_MultipleProcessJobCreate requires carrier_id")
        if not resolved_recipe_id:
            raise SecsMessageError("S16F15_F16_MultipleProcessJobCreate requires recipe_id in port_context")

        slot_numbers = self._port_context_slot_numbers(record)
        if not slot_numbers:
            raise SecsMessageError(
                "S16F15_F16_MultipleProcessJobCreate requires at least one sheet in port_context"
            )

        logger.info(
            "S16F15_F16_MultipleProcessJobCreate uses port_context: eqpt_id=%s port_id=%s carrier_id=%s recipe_id=%s prjob_id=%s slot_count=%s",
            str(getattr(record, "eqpt_id", "") or "").strip(),
            str(getattr(record, "port_id", "") or "").strip(),
            resolved_carrier_id,
            resolved_recipe_id,
            resolved_prjob_id,
            len(slot_numbers),
        )

        result = await self.send_secs_template(
            "S16F15_F16_MultipleProcessJobCreate",
            wait_reply=wait_reply,
            timeout=timeout,
            variables={
                "multiple_process_job_body": self._build_multiple_process_job_body(
                    prjob_id=resolved_prjob_id,
                    carrier_id=resolved_carrier_id,
                    recipe_id=resolved_recipe_id,
                    slot_numbers=slot_numbers,
                ),
            },
        )
        if self._to_bool(wait_reply, default=True):
            self._ensure_reply_ack_zero("S16F15_F16_MultipleProcessJobCreate", result.get("reply"))
        return result

    async def S14F9_F10_CreateControlJob(
        self,
        cjob_id: str = "",
        prjob_id: str = "",
        *,
        carrier_id: str = "",
        port_id: str = "",
        eqpt_id: str = "",
        wait_reply: Any = True,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        resolved_cjob_id = str(cjob_id or "").strip()
        resolved_prjob_id = str(prjob_id or "").strip()
        resolved_carrier_id = str(carrier_id or "").strip()
        record = None
        if not (resolved_cjob_id and resolved_prjob_id and resolved_carrier_id):
            record = self._resolve_port_context_record(
                method_name="S14F9_F10_CreateControlJob",
                eqpt_id=eqpt_id,
                port_id=port_id,
                carrier_id=carrier_id,
                direct_match_mode="soft",
            )
            if not resolved_cjob_id:
                resolved_cjob_id = str(getattr(record, "cjob_id", "") or "").strip()
            if not resolved_prjob_id:
                resolved_prjob_id = str(getattr(record, "prjob_id", "") or "").strip()
            resolved_carrier_id = str(carrier_id or getattr(record, "carrier_id", "") or "").strip()
        if not resolved_cjob_id:
            raise SecsMessageError("S14F9_F10_CreateControlJob requires cjob_id in port_context")
        if not resolved_prjob_id:
            raise SecsMessageError("S14F9_F10_CreateControlJob requires prjob_id in port_context")
        if not resolved_carrier_id:
            raise SecsMessageError("S14F9_F10_CreateControlJob requires carrier_id")

        logger.info(
            "S14F9_F10_CreateControlJob uses values: carrier_id=%s cjob_id=%s prjob_id=%s port_context=%s",
            resolved_carrier_id,
            resolved_cjob_id,
            resolved_prjob_id,
            "Y" if record is not None else "N",
        )

        result = await self.send_secs_template(
            "S14F9_F10_CreateControlJob",
            wait_reply=wait_reply,
            timeout=timeout,
            variables={
                "create_control_job_body": self._build_create_control_job_body(
                    cjob_id=resolved_cjob_id,
                    carrier_id=resolved_carrier_id,
                    prjob_id=resolved_prjob_id,
                ),
            },
        )
        if self._to_bool(wait_reply, default=True):
            self._ensure_reply_ack_zero("S14F9_F10_CreateControlJob", result.get("reply"))
        return result

    async def S3F17_F18_ProceedWithSlotMap(
        self,
        carrier_id: str,
        port_id: str,
        *,
        eqpt_id: str = "",
        capacity: Any = 25,
        wait_reply: Any = True,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        resolved_carrier_id = str(carrier_id or "").strip()
        resolved_port_id = self._convert_value_by_type("U1", port_id)
        if not resolved_carrier_id:
            raise ValueError("S3F17_F18_ProceedWithSlotMap requires carrier_id")

        record = self._get_port_context_store().find(
            eqpt_id=str(eqpt_id or "").strip(),
            port_id=port_id,
            carrier_id=resolved_carrier_id,
            direct_match_mode="soft",
        )
        if record is None:
            raise SecsMessageError(
                f"S3F17_F18_ProceedWithSlotMap could not resolve port_context for port_id={port_id} carrier_id={resolved_carrier_id}"
            )

        resolved_lot_id = str(getattr(record, "lot_id", "") or "").strip()
        if not resolved_lot_id:
            raise SecsMessageError(
                f"S3F17_F18_ProceedWithSlotMap requires lot_id in port_context for carrier_id={resolved_carrier_id}"
            )

        resolved_capacity = self._convert_value_by_type("U1", capacity)
        ordered_sheets = [
            item
            for _index, item in sorted(
                enumerate(list(getattr(record, "sheets", []) or [])),
                key=lambda pair: self._sheet_sort_key(pair[1], pair[0]),
            )
        ]
        if len(ordered_sheets) < resolved_capacity:
            raise SecsMessageError(
                "S3F17_F18_ProceedWithSlotMap requires at least "
                f"{resolved_capacity} sheets in port_context, current={len(ordered_sheets)}"
            )

        slot_map_body = self._build_slot_map_body(
            lot_id=resolved_lot_id,
            sheets=ordered_sheets,
            capacity=resolved_capacity,
        )

        logger.info(
            "S3F17_F18_ProceedWithSlotMap uses port_context: eqpt_id=%s port_id=%s carrier_id=%s lot_id=%s sheet_count=%s capacity=%s",
            str(getattr(record, "eqpt_id", "") or "").strip(),
            str(getattr(record, "port_id", "") or "").strip(),
            resolved_carrier_id,
            resolved_lot_id,
            len(ordered_sheets),
            resolved_capacity,
        )

        result = await self.send_secs_template(
            "S3F17_F18_ProceedWithSlotMap",
            wait_reply=wait_reply,
            timeout=timeout,
            variables={
                "carrier_id": resolved_carrier_id,
                "port_id": resolved_port_id,
                "slot_map_body": slot_map_body,
            },
        )
        if self._to_bool(wait_reply, default=True):
            self._ensure_reply_ack_zero("S3F17_F18_ProceedWithSlotMap", result.get("reply"))
        return result
