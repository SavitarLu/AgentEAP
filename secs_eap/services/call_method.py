"""
Workflow-callable business methods.

Keep YAML-exposed methods in one place so EAP orchestration stays small.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from ..mes.tx.apvryope import APVRYOPERequest
from ..mes.tx.apcnlogn import APCNLOGNRequest
from ..mes.tx.apclogon import APCLOGONRequest
from ..mes.tx.apiiteml import APIITEMLRequest
from .common import CallMethodCommonMixin, MesReplyError
from .port_context import normalize_mes_port_id


logger = logging.getLogger(__name__)


class CallMethodService(CallMethodCommonMixin):
    """Container for workflow ``call_method`` targets."""

    async def INQUIRY_PROC_START(
        self,
        port_id: str,
        carrier_id: str = "",
        *,
        load_carrier_id: str = "",
        port_type: str = "",
        eqpt_id: str = "",
        user_id: str = "",
        logon_user_id: str = "",
        apiiteml_enabled: Any = True,
        apclogon_enabled: Any = True,
        rep_unit: str = "L",
        data_pat: str = "P",
        dcop_online: Any = "Y",
        orig_opi_flg: Any = "N",
        force_lgn_flg: Any = "N",
    ) -> Dict[str, Any]:
        """
        Run the process-start inquiry flow based on legacy TAPAPI TX ordering.

        Sequence:
        1. APVRYOPE
        2. capture/log port_context_store
        3. APIITEML when mes_id is available
        4. APCLOGON
        """
        eap_api = self._require_eap_api()
        raw_port_id = str(port_id or "").strip()
        resolved_carrier_id = str(carrier_id or load_carrier_id or "").strip()
        resolved_eqpt_id = self._resolve_inquiry_eqpt_id(eqpt_id)
        store = self._port_context_store
        resolved_port_id = store.resolve_runtime_port_id(resolved_eqpt_id, raw_port_id) if store else raw_port_id
        mes_port_id = normalize_mes_port_id(resolved_port_id or raw_port_id)
        resolved_user_id = self._resolve_method_user_id(user_id)
        resolved_logon_user_id = self._resolve_method_user_id(logon_user_id or resolved_user_id)
        resolved_port_type = (
            store.resolve_port_type(resolved_eqpt_id, resolved_port_id, port_type)
            if store
            else str(port_type or "").strip()
        )

        if not resolved_port_id:
            raise ValueError("inquiry_proc_start requires port_id")
        if not resolved_carrier_id:
            raise ValueError("inquiry_proc_start requires carrier_id or load_carrier_id")

        logger.info(
            "inquiry_proc_start begin: eqpt_id=%s port_id=%s mes_port_id=%s carrier_id=%s port_type=%s "
            "apiiteml_enabled=%s apclogon_enabled=%s",
            resolved_eqpt_id,
            resolved_port_id,
            mes_port_id,
            resolved_carrier_id,
            resolved_port_type,
            self._to_bool(apiiteml_enabled, default=True),
            self._to_bool(apclogon_enabled, default=True),
        )

        if self._port_context_store:
            record = self._port_context_store.get_or_create(
                resolved_eqpt_id,
                resolved_port_id,
                port_type=resolved_port_type or "unknown",
            )
            if resolved_port_type:
                record.port_type = resolved_port_type
            record.carrier_id = resolved_carrier_id
            record.user_id = resolved_user_id
            record.touch("INQUIRY_PROC_START")

        logger.info(
            "inquiry_proc_start sending APVRYOPE: eqpt_id=%s port_id=%s mes_port_id=%s carrier_id=%s user_id=%s",
            resolved_eqpt_id,
            resolved_port_id,
            mes_port_id,
            resolved_carrier_id,
            resolved_user_id,
        )
        apvryope_request = APVRYOPERequest(
            eqpt_id=resolved_eqpt_id,
            port_id=mes_port_id,
            crr_id=resolved_carrier_id,
            user_id=resolved_user_id,
        )
        apvryope_response = await eap_api.execute_mes_tx("APVRYOPE", apvryope_request)
        if self._port_context_store and apvryope_response is not None:
            try:
                self._port_context_store.capture_apvryope(apvryope_request, apvryope_response)
            except Exception as exc:
                logger.warning("Failed to capture APVRYOPE context from inquiry_proc_start: %s", exc)
        self._ensure_tx_success("APVRYOPE", apvryope_response)
        self._log_port_context_snapshot("APVRYOPE")

        mes_id = str(getattr(apvryope_response, "mes_id", "") or "").strip()
        recipe_id = str(getattr(apvryope_response, "recipe_id", "") or "").strip()

        apiiteml_response = None
        if self._to_bool(apiiteml_enabled, default=True):
            if mes_id:
                logger.info(
                    "inquiry_proc_start sending APIITEML: eqpt_id=%s mes_id=%s rep_unit=%s data_pat=%s",
                    resolved_eqpt_id,
                    mes_id,
                    rep_unit,
                    data_pat,
                )
                apiiteml_request = APIITEMLRequest(
                    eqpt_id=resolved_eqpt_id,
                    rep_unit=str(rep_unit or "").strip() or "L",
                    data_pat=str(data_pat or "").strip() or "P",
                    mes_id=mes_id,
                    dcop_online=self._to_yes_no_flag(dcop_online, default="Y"),
                    orig_opi_flg=self._to_yes_no_flag(orig_opi_flg, default="N"),
                )
                apiiteml_response = await eap_api.execute_mes_tx("APIITEML", apiiteml_request)
                self._ensure_tx_success("APIITEML", apiiteml_response)

                if self._port_context_store:
                    self._port_context_store.update(
                        resolved_eqpt_id,
                        resolved_port_id,
                        last_tx_name="APIITEML",
                        apiiteml_rtn_code=getattr(apiiteml_response, "rtn_code", ""),
                        apiiteml_rtn_mesg=getattr(apiiteml_response, "rtn_mesg", ""),
                        apiiteml_mes_id=mes_id,
                        apiiteml_item_count=len(getattr(apiiteml_response, "oary", []) or []),
                        apiiteml_items=self._plain_object(getattr(apiiteml_response, "oary", []) or []),
                    )
            else:
                logger.info(
                    "inquiry_proc_start skip APIITEML: mes_id is blank for eqpt_id=%s port_id=%s",
                    resolved_eqpt_id,
                    resolved_port_id,
                )

        apclogon_response = None
        if self._to_bool(apclogon_enabled, default=True):
            logger.info(
                "inquiry_proc_start sending APCLOGON: eqpt_id=%s port_id=%s carrier_id=%s recipe_id=%s user_id=%s",
                resolved_eqpt_id,
                mes_port_id,
                resolved_carrier_id,
                recipe_id,
                resolved_logon_user_id,
            )
            apclogon_request = APCLOGONRequest(
                orig_opi_flg=self._to_yes_no_flag(orig_opi_flg, default="N"),
                crr_id=resolved_carrier_id,
                eqpt_id=resolved_eqpt_id,
                port_id=mes_port_id,
                user_id=resolved_logon_user_id,
                ds_recipe_id=recipe_id,
                ac_recipe_id=recipe_id,
                force_lgn_flg=self._to_yes_no_flag(force_lgn_flg, default="N"),
            )
            apclogon_response = await eap_api.execute_mes_tx("APCLOGON", apclogon_request)
            self._ensure_tx_success("APCLOGON", apclogon_response)

            if self._port_context_store:
                self._port_context_store.update(
                    resolved_eqpt_id,
                    resolved_port_id,
                    last_tx_name="APCLOGON",
                    apclogon_rtn_code=getattr(apclogon_response, "rtn_code", ""),
                    apclogon_rtn_mesg=getattr(apclogon_response, "rtn_mesg", ""),
                )

        result = {
            "result": 0,
            "eqpt_id": resolved_eqpt_id,
            "port_id": resolved_port_id,
            "mes_port_id": mes_port_id,
            "port_type": resolved_port_type,
            "carrier_id": resolved_carrier_id,
            "user_id": resolved_user_id,
            "logon_user_id": resolved_logon_user_id,
            "lot_id": str(getattr(apvryope_response, "lot_id", "") or "").strip(),
            "recipe_id": recipe_id,
            "mes_id": mes_id,
            "apvryope": apvryope_response,
            "apiiteml": apiiteml_response,
            "apclogon": apclogon_response,
        }

        if self._port_context_store:
            record = self._port_context_store.get(resolved_eqpt_id, resolved_port_id)
            if record:
                result["port_context"] = record.to_dict()

        logger.info(
            "inquiry_proc_start completed: eqpt_id=%s port_id=%s carrier_id=%s lot_id=%s recipe_id=%s mes_id=%s",
            resolved_eqpt_id,
            resolved_port_id,
            resolved_carrier_id,
            result["lot_id"],
            recipe_id,
            mes_id,
        )
        return result

    async def PROCESS_START_CANCEL(
        self,
        carrier_id: str,
        lot_id: str = "",
        *,
        port_id: str = "",
        eqpt_id: str = "",
        user_id: str = "",
        sht_ope_msg: str = "",
    ) -> Dict[str, Any]:
        """
        TAPAPI-compatible cancel operation start flow.

        Reference behavior from PROCESS_START_CANCEL.cpp:
        - identify carrier/lot context
        - send APCNLOGN with one sheet entry
        """
        resolved_eqpt_id = self._resolve_inquiry_eqpt_id(eqpt_id)
        resolved_carrier_id = str(carrier_id or "").strip()
        resolved_lot_id = str(lot_id or "").strip()
        if not resolved_carrier_id:
            raise ValueError("process_start_cancel requires carrier_id")

        store = self._port_context_store
        record = (
            store.find(
                eqpt_id=resolved_eqpt_id,
                port_id=port_id,
                carrier_id=resolved_carrier_id,
                lot_id=resolved_lot_id,
                direct_match_mode="any",
            )
            if store
            else None
        )
        if record is None:
            raise ValueError(
                f"process_start_cancel could not resolve port context for carrier_id={resolved_carrier_id}"
            )

        resolved_port_id = str(getattr(record, "port_id", "") or "").strip()
        resolved_lot_id = resolved_lot_id or str(getattr(record, "lot_id", "") or "").strip()

        sheet_items = list(getattr(record, "sheets", []) or [])
        if not sheet_items:
            raise ValueError(
                f"process_start_cancel requires at least one sheet in port context for carrier_id={resolved_carrier_id}"
            )

        selected_sheet = sheet_items[0]
        if len(sheet_items) > 1:
            logger.info(
                "process_start_cancel uses first sheet from port context: carrier_id=%s lot_id=%s selected_sht_id=%s total_sheets=%d",
                resolved_carrier_id,
                resolved_lot_id,
                str(getattr(selected_sheet, 'sht_id', '') or '').strip(),
                len(sheet_items),
            )

        selected_iary = [{
            "sht_id": str(getattr(selected_sheet, "sht_id", "") or "").strip(),
            "slot_no": self._normalize_slot_no(getattr(selected_sheet, "slot_no", "") or "001") or "001",
        }]
        if not selected_iary[0]["sht_id"]:
            raise ValueError(
                f"process_start_cancel requires sheet sht_id in port context for carrier_id={resolved_carrier_id}"
            )

        logger.info(
            "process_start_cancel begin: eqpt_id=%s port_id=%s carrier_id=%s lot_id=%s sht_id=%s",
            resolved_eqpt_id,
            resolved_port_id,
            resolved_carrier_id,
            resolved_lot_id,
            selected_iary[0]["sht_id"],
        )

        eap_api = self._require_eap_api()
        resolved_user_id = self._resolve_method_user_id(user_id or resolved_eqpt_id)
        resolved_sht_ope_msg = str(sht_ope_msg or "").strip()
        iary_items = self._build_apcnlogn_iary(selected_iary)

        logger.info(
            "apcnlogn begin: eqpt_id=%s port_id=%s carrier_id=%s sht_cnt=%s sht_ope_msg=%s",
            resolved_eqpt_id,
            resolved_port_id,
            resolved_carrier_id,
            "1",
            resolved_sht_ope_msg,
        )
        request = APCNLOGNRequest(
            crr_id=resolved_carrier_id,
            eqpt_id=resolved_eqpt_id,
            sht_ope_msg=resolved_sht_ope_msg,
            user_id=resolved_user_id,
            sht_cnt="1",
            iary=iary_items,
        )
        response = await eap_api.execute_mes_tx("APCNLOGN", request)
        self._ensure_tx_success("APCNLOGN", response)

        if self._port_context_store:
            self._port_context_store.update(
                resolved_eqpt_id,
                resolved_port_id,
                last_tx_name="APCNLOGN",
                apcnlogn_rtn_code=getattr(response, "rtn_code", ""),
                apcnlogn_rtn_mesg=getattr(response, "rtn_mesg", ""),
                apcnlogn_sht_ope_msg=resolved_sht_ope_msg,
            )

        result = {
            "result": 0,
            "eqpt_id": resolved_eqpt_id,
            "port_id": resolved_port_id,
            "carrier_id": resolved_carrier_id,
            "user_id": resolved_user_id,
            "sht_ope_msg": resolved_sht_ope_msg,
            "sht_cnt": "1",
            "iary": self._plain_object(iary_items),
            "apcnlogn": response,
        }
        result["lot_id"] = resolved_lot_id
        result["process_start_cancel"] = True
        result["selected_sheet"] = dict(selected_iary[0])
        self._attach_port_context(result, resolved_eqpt_id, resolved_port_id)

        logger.info(
            "process_start_cancel completed: eqpt_id=%s port_id=%s carrier_id=%s lot_id=%s sht_id=%s",
            resolved_eqpt_id,
            resolved_port_id,
            resolved_carrier_id,
            resolved_lot_id,
            selected_iary[0]["sht_id"],
        )
        return result

    async def UPDATE_EQP_MODE_STATUS(
        self,
        mode: str,
        stat: str,
    ) -> Dict[str, Any]:
        """
        Legacy TAPAPI-compatible equipment mode/status update.
        """
        allowed_modes = {
            "",
            "MANU",
            "SEMI",
            "SEMI2",
            "SEMI2A",
            "SEMI3",
            "SEMI4",
            "FULL2",
            "AUTO",
            "FULL",
        }

        resolved_mode = self._normalize_upper_text(mode)
        resolved_stat = self._normalize_upper_text(stat)
        if resolved_mode not in allowed_modes:
            raise ValueError(f"Unknown equipment mode: {mode}")

        resolved_eqpt_id = self._resolve_inquiry_eqpt_id("")
        previous_mode = self._resolve_current_eqpt_mode(resolved_eqpt_id)
        effective_mode = resolved_mode or previous_mode

        logger.info(
            "update_eqp_mode_status begin: eqpt_id=%s previous_mode=%s mode=%s stat=%s",
            resolved_eqpt_id,
            previous_mode,
            resolved_mode,
            resolved_stat,
        )

        mode_response = None
        if resolved_mode and resolved_mode != previous_mode:
            logger.info(
                "update_eqp_mode_status sending APCEQPST mode report: eqpt_id=%s mode=%s",
                resolved_eqpt_id,
                resolved_mode,
            )
            mode_response = await self._execute_apceqpst(
                clm_eqst_typ="A",
                orig_opi_flg="N",
                user_id=self._resolve_method_user_id(""),
                eqpt_id=resolved_eqpt_id,
                eqpt_mode=resolved_mode,
                eqpt_stat="",
            )

        status_response = None
        if resolved_stat:
            logger.info(
                "update_eqp_mode_status sending APCEQPST status report: eqpt_id=%s mode=%s stat=%s",
                resolved_eqpt_id,
                effective_mode,
                resolved_stat,
            )
            status_response = await self._execute_apceqpst(
                clm_eqst_typ="D",
                orig_opi_flg="N",
                user_id=resolved_eqpt_id,
                eqpt_id=resolved_eqpt_id,
                eqpt_mode=effective_mode,
                eqpt_stat=resolved_stat,
                eqpt_sub_stat=self._resolve_eqpt_sub_stat(resolved_stat),
            )

        self._update_runtime_eqpt_mode_status(resolved_mode, resolved_stat)
        self._refresh_eqpt_port_contexts(
            resolved_eqpt_id,
            eqpt_mode=effective_mode,
            eqpt_status=resolved_stat,
            reset_for_manual=(resolved_mode == "MANU"),
        )

        result = {
            "result": 0,
            "eqpt_id": resolved_eqpt_id,
            "previous_mode": previous_mode,
            "mode": effective_mode,
            "stat": resolved_stat,
            "mode_report_sent": bool(mode_response is not None),
            "status_report_sent": bool(status_response is not None),
            "mode_response": mode_response,
            "status_response": status_response,
        }
        logger.info(
            "update_eqp_mode_status completed: eqpt_id=%s mode=%s stat=%s mode_report_sent=%s status_report_sent=%s",
            resolved_eqpt_id,
            effective_mode,
            resolved_stat,
            result["mode_report_sent"],
            result["status_report_sent"],
        )
        return result

    async def LOAD_COMP(
        self,
        port_type: str = "",
        port_id: str = "",
        carrier_id: str = "",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Load complete report.
        """
        resolved_args = self._resolve_port_call_args(
            port_type=port_type,
            port_id=port_id,
            carrier_id=carrier_id,
            kwargs=kwargs,
        )
        port_type = resolved_args["port_type"]
        port_id = resolved_args["port_id"]
        carrier_id = resolved_args["carrier_id"]

        resolved_eqpt_id = self._resolve_inquiry_eqpt_id("")
        store = self._port_context_store
        resolved_port_id = store.resolve_runtime_port_id(resolved_eqpt_id, port_id) if store else str(port_id or "").strip()
        mes_port_id = normalize_mes_port_id(resolved_port_id or port_id)
        resolved_port_type = (
            store.resolve_port_type(resolved_eqpt_id, resolved_port_id, port_type)
            if store
            else str(port_type or "").strip()
        ) or str(port_type or "").strip()
        resolved_carrier_id = str(carrier_id or "").strip()
        current_mode = self._resolve_current_eqpt_mode(resolved_eqpt_id)

        if not resolved_port_type:
            raise ValueError("load_comp requires port_type")
        if not resolved_port_id:
            raise ValueError("load_comp requires port_id")

        logger.info(
            "load_comp begin: eqpt_id=%s port_type=%s port_id=%s mes_port_id=%s carrier_id=%s current_mode=%s",
            resolved_eqpt_id,
            resolved_port_type,
            resolved_port_id,
            mes_port_id,
            resolved_carrier_id,
            current_mode,
        )

        if self._port_context_store:
            record = self._port_context_store.get_or_create(
                resolved_eqpt_id,
                resolved_port_id,
                port_type=resolved_port_type or "unknown",
            )
            record.port_type = resolved_port_type or record.port_type
            record.port_status = "LC"
            if resolved_carrier_id:
                record.carrier_id = resolved_carrier_id
            record.update_from_mapping(
                {
                    "eqpt_mode": current_mode,
                    "eqpt_status": self._runtime_eqpt_status,
                },
                source="LOAD_COMP",
                allow_empty=True,
            )

        apceqpst_response = None
        tx_sent = False
        if current_mode and current_mode != "AUTO":
            logger.info(
                "load_comp skip APCEQPST port status report: eqpt_id=%s current_mode=%s port_id=%s",
                resolved_eqpt_id,
                current_mode,
                mes_port_id,
            )
        else:
            logger.info(
                "load_comp sending APCEQPST port status report: eqpt_id=%s port_id=%s mes_port_id=%s port_stat=LDCM",
                resolved_eqpt_id,
                resolved_port_id,
                mes_port_id,
            )
            apceqpst_response = await self._execute_apceqpst(
                clm_eqst_typ="P",
                orig_opi_flg="N",
                user_id=resolved_eqpt_id,
                eqpt_id=resolved_eqpt_id,
                port_id=mes_port_id,
                port_stat="LDCM",
            )
            tx_sent = True

            if self._port_context_store:
                self._port_context_store.update(
                    resolved_eqpt_id,
                    resolved_port_id,
                    last_tx_name="LOAD_COMP",
                    load_comp_rtn_code=getattr(apceqpst_response, "rtn_code", ""),
                    load_comp_rtn_mesg=getattr(apceqpst_response, "rtn_mesg", ""),
                )

        result = {
            "result": 0,
            "eqpt_id": resolved_eqpt_id,
            "port_type": resolved_port_type,
            "port_id": resolved_port_id,
            "mes_port_id": mes_port_id,
            "carrier_id": resolved_carrier_id,
            "current_mode": current_mode,
            "tx_sent": tx_sent,
            "apceqpst": apceqpst_response,
        }
        logger.info(
            "load_comp completed: eqpt_id=%s port_id=%s current_mode=%s tx_sent=%s",
            resolved_eqpt_id,
            resolved_port_id,
            current_mode,
            tx_sent,
        )
        return result

    async def LOAD_REQ(
        self,
        port_type: str = "",
        port_id: str = "",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Legacy TAPAPI-compatible load request.
        """
        resolved_args = self._resolve_port_call_args(
            port_type=port_type,
            port_id=port_id,
            kwargs=kwargs,
        )
        port_type = resolved_args["port_type"]
        port_id = resolved_args["port_id"]

        resolved_eqpt_id = self._resolve_inquiry_eqpt_id("")
        store = self._port_context_store
        resolved_port_id = store.resolve_runtime_port_id(resolved_eqpt_id, port_id) if store else str(port_id or "").strip()
        mes_port_id = normalize_mes_port_id(resolved_port_id or port_id)
        resolved_port_type = (
            store.resolve_port_type(resolved_eqpt_id, resolved_port_id, port_type)
            if store
            else str(port_type or "").strip()
        ) or str(port_type or "").strip()
        current_mode = self._resolve_current_eqpt_mode(resolved_eqpt_id)

        if not resolved_port_type:
            raise ValueError("load_req requires port_type")
        if not resolved_port_id:
            raise ValueError("load_req requires port_id")

        logger.info(
            "load_req begin: eqpt_id=%s port_type=%s port_id=%s mes_port_id=%s current_mode=%s",
            resolved_eqpt_id,
            resolved_port_type,
            resolved_port_id,
            mes_port_id,
            current_mode,
        )

        if self._port_context_store:
            record = self._port_context_store.get_or_create(
                resolved_eqpt_id,
                resolved_port_id,
                port_type=resolved_port_type or "unknown",
            )
            record.port_type = resolved_port_type or record.port_type
            self._clear_port_material_context(record)
            record.port_status = "LR"
            record.update_from_mapping(
                {
                    "eqpt_mode": current_mode,
                    "eqpt_status": self._runtime_eqpt_status,
                },
                source="LOAD_REQ",
                allow_empty=True,
            )

        logger.info(
            "load_req sending APCEQPST port status report: eqpt_id=%s port_id=%s mes_port_id=%s port_stat=LDRQ",
            resolved_eqpt_id,
            resolved_port_id,
            mes_port_id,
        )
        apceqpst_response = await self._execute_apceqpst(
            clm_eqst_typ="P",
            orig_opi_flg="N",
            user_id=resolved_eqpt_id,
            eqpt_id=resolved_eqpt_id,
            port_id=mes_port_id,
            port_stat="LDRQ",
        )

        if self._port_context_store:
            self._port_context_store.update(
                resolved_eqpt_id,
                resolved_port_id,
                last_tx_name="LOAD_REQ",
                load_req_rtn_code=getattr(apceqpst_response, "rtn_code", ""),
                load_req_rtn_mesg=getattr(apceqpst_response, "rtn_mesg", ""),
            )

        result = {
            "result": 0,
            "eqpt_id": resolved_eqpt_id,
            "port_type": resolved_port_type,
            "port_id": resolved_port_id,
            "mes_port_id": mes_port_id,
            "current_mode": current_mode,
            "tx_sent": True,
            "apceqpst": apceqpst_response,
        }
        self._attach_port_context(result, resolved_eqpt_id, resolved_port_id)
        logger.info(
            "load_req completed: eqpt_id=%s port_id=%s current_mode=%s",
            resolved_eqpt_id,
            resolved_port_id,
            current_mode,
        )
        return result

    async def UNLOAD_REQ(
        self,
        port_type: str = "",
        port_id: str = "",
        carrier_id: str = "",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Legacy TAPAPI-compatible unload request.
        """
        resolved_args = self._resolve_port_call_args(
            port_type=port_type,
            port_id=port_id,
            carrier_id=carrier_id,
            kwargs=kwargs,
        )
        port_type = resolved_args["port_type"]
        port_id = resolved_args["port_id"]
        carrier_id = resolved_args["carrier_id"]

        resolved_eqpt_id = self._resolve_inquiry_eqpt_id("")
        store = self._port_context_store
        resolved_port_id = store.resolve_runtime_port_id(resolved_eqpt_id, port_id) if store else str(port_id or "").strip()
        mes_port_id = normalize_mes_port_id(resolved_port_id or port_id)
        resolved_port_type = (
            store.resolve_port_type(resolved_eqpt_id, resolved_port_id, port_type)
            if store
            else str(port_type or "").strip()
        ) or str(port_type or "").strip()
        current_mode = self._resolve_current_eqpt_mode(resolved_eqpt_id)
        resolved_carrier_id = str(carrier_id or "").strip()

        if not resolved_port_type:
            raise ValueError("unload_req requires port_type")
        if not resolved_port_id:
            raise ValueError("unload_req requires port_id")

        existing_record = None
        if self._port_context_store:
            existing_record = self._port_context_store.get(resolved_eqpt_id, resolved_port_id)
        if existing_record and existing_record.carrier_id:
            if resolved_carrier_id and existing_record.carrier_id != resolved_carrier_id:
                logger.warning(
                    "unload_req carrier mismatch: eqpt_id=%s port_id=%s runtime_carrier_id=%s input_carrier_id=%s",
                    resolved_eqpt_id,
                    resolved_port_id,
                    existing_record.carrier_id,
                    resolved_carrier_id,
                )
            if not resolved_carrier_id:
                resolved_carrier_id = existing_record.carrier_id

        logger.info(
            "unload_req begin: eqpt_id=%s port_type=%s port_id=%s mes_port_id=%s carrier_id=%s current_mode=%s",
            resolved_eqpt_id,
            resolved_port_type,
            resolved_port_id,
            mes_port_id,
            resolved_carrier_id,
            current_mode,
        )

        if self._port_context_store:
            record = self._port_context_store.get_or_create(
                resolved_eqpt_id,
                resolved_port_id,
                port_type=resolved_port_type or "unknown",
            )
            record.port_type = resolved_port_type or record.port_type
            record.port_status = "UR"
            if resolved_carrier_id:
                record.carrier_id = resolved_carrier_id
            record.update_from_mapping(
                {
                    "eqpt_mode": current_mode,
                    "eqpt_status": self._runtime_eqpt_status,
                },
                source="UNLOAD_REQ",
                allow_empty=True,
            )

        logger.info(
            "unload_req sending APCEQPST port status report: eqpt_id=%s port_id=%s mes_port_id=%s port_stat=UDRQ",
            resolved_eqpt_id,
            resolved_port_id,
            mes_port_id,
        )
        apceqpst_response = await self._execute_apceqpst(
            clm_eqst_typ="P",
            orig_opi_flg="N",
            user_id=resolved_eqpt_id,
            eqpt_id=resolved_eqpt_id,
            port_id=mes_port_id,
            port_stat="UDRQ",
        )

        if self._port_context_store:
            self._port_context_store.update(
                resolved_eqpt_id,
                resolved_port_id,
                last_tx_name="UNLOAD_REQ",
                unload_req_rtn_code=getattr(apceqpst_response, "rtn_code", ""),
                unload_req_rtn_mesg=getattr(apceqpst_response, "rtn_mesg", ""),
            )

        result = {
            "result": 0,
            "eqpt_id": resolved_eqpt_id,
            "port_type": resolved_port_type,
            "port_id": resolved_port_id,
            "mes_port_id": mes_port_id,
            "carrier_id": resolved_carrier_id,
            "current_mode": current_mode,
            "tx_sent": True,
            "apceqpst": apceqpst_response,
        }
        self._attach_port_context(result, resolved_eqpt_id, resolved_port_id)
        logger.info(
            "unload_req completed: eqpt_id=%s port_id=%s carrier_id=%s current_mode=%s",
            resolved_eqpt_id,
            resolved_port_id,
            resolved_carrier_id,
            current_mode,
        )
        return result

    async def UNLOAD_COMP(
        self,
        port_type: str = "",
        port_id: str = "",
        carrier_id: str = "",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Legacy TAPAPI-compatible unload complete report.
        """
        resolved_args = self._resolve_port_call_args(
            port_type=port_type,
            port_id=port_id,
            carrier_id=carrier_id,
            kwargs=kwargs,
        )
        port_type = resolved_args["port_type"]
        port_id = resolved_args["port_id"]
        carrier_id = resolved_args["carrier_id"]

        resolved_eqpt_id = self._resolve_inquiry_eqpt_id("")
        store = self._port_context_store
        resolved_port_id = store.resolve_runtime_port_id(resolved_eqpt_id, port_id) if store else str(port_id or "").strip()
        mes_port_id = normalize_mes_port_id(resolved_port_id or port_id)
        resolved_port_type = (
            store.resolve_port_type(resolved_eqpt_id, resolved_port_id, port_type)
            if store
            else str(port_type or "").strip()
        ) or str(port_type or "").strip()
        current_mode = self._resolve_current_eqpt_mode(resolved_eqpt_id)
        resolved_carrier_id = str(carrier_id or "").strip()

        if not resolved_port_type:
            raise ValueError("unload_comp requires port_type")
        if not resolved_port_id:
            raise ValueError("unload_comp requires port_id")

        existing_record = None
        if self._port_context_store:
            existing_record = self._port_context_store.get(resolved_eqpt_id, resolved_port_id)
        if existing_record and existing_record.carrier_id:
            if resolved_carrier_id and existing_record.carrier_id != resolved_carrier_id:
                logger.warning(
                    "unload_comp carrier mismatch: eqpt_id=%s port_id=%s runtime_carrier_id=%s input_carrier_id=%s",
                    resolved_eqpt_id,
                    resolved_port_id,
                    existing_record.carrier_id,
                    resolved_carrier_id,
                )
            if not resolved_carrier_id:
                resolved_carrier_id = existing_record.carrier_id

        next_port_status = "UC"

        logger.info(
            "unload_comp begin: eqpt_id=%s port_type=%s port_id=%s mes_port_id=%s carrier_id=%s current_mode=%s",
            resolved_eqpt_id,
            resolved_port_type,
            resolved_port_id,
            mes_port_id,
            resolved_carrier_id,
            current_mode,
        )

        if self._port_context_store:
            record = self._port_context_store.get_or_create(
                resolved_eqpt_id,
                resolved_port_id,
                port_type=resolved_port_type or "unknown",
            )
            record.port_type = resolved_port_type or record.port_type
            record.port_status = next_port_status
            if resolved_carrier_id:
                record.carrier_id = resolved_carrier_id
            record.update_from_mapping(
                {
                    "eqpt_mode": current_mode,
                    "eqpt_status": self._runtime_eqpt_status,
                },
                source="UNLOAD_COMP",
                allow_empty=True,
            )

        logger.info(
            "unload_comp sending APCEQPST port status report: eqpt_id=%s port_id=%s mes_port_id=%s port_stat=UDCM",
            resolved_eqpt_id,
            resolved_port_id,
            mes_port_id,
        )
        apceqpst_response = await self._execute_apceqpst(
            clm_eqst_typ="P",
            orig_opi_flg="N",
            user_id=resolved_eqpt_id,
            eqpt_id=resolved_eqpt_id,
            port_id=mes_port_id,
            port_stat="UDCM",
        )

        if self._port_context_store:
            self._port_context_store.update(
                resolved_eqpt_id,
                resolved_port_id,
                last_tx_name="UNLOAD_COMP",
                unload_comp_rtn_code=getattr(apceqpst_response, "rtn_code", ""),
                unload_comp_rtn_mesg=getattr(apceqpst_response, "rtn_mesg", ""),
            )

        result = {
            "result": 0,
            "eqpt_id": resolved_eqpt_id,
            "port_type": resolved_port_type,
            "port_id": resolved_port_id,
            "mes_port_id": mes_port_id,
            "carrier_id": resolved_carrier_id,
            "current_mode": current_mode,
            "tx_sent": True,
            "apceqpst": apceqpst_response,
            "port_status": next_port_status,
        }
        self._attach_port_context(result, resolved_eqpt_id, resolved_port_id)
        logger.info(
            "unload_comp completed: eqpt_id=%s port_id=%s carrier_id=%s port_status=%s",
            resolved_eqpt_id,
            resolved_port_id,
            resolved_carrier_id,
            next_port_status,
        )
        return result
