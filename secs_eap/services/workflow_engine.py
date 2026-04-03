"""
Lightweight workflow engine prototype.

Purpose:
- Trigger follow-up SECS actions after specific incoming messages.
- Keep beginner customization in YAML instead of Python code.
"""

import logging
import asyncio
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from secs_driver.src.secs_message import SECSItem, SECSMessage
from secs_driver.src.secs_types import SECSType

from ..mes.tx.base import build_tx_dataclass
from ..mes.tx_registry import get_tx_request_type
from .call_method import MesReplyError
from .common import SecsMessageCommonMixin
from .event_report_setup import EventReportSetupBuilder
from .reply_meanings import format_reply_ack
from .secs_msg import SecsMessageError


logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Simple YAML-driven workflow runner."""

    _STEP_CONTROL_KEYS = {
        "action",
        "method",
        "args",
        "params",
        "kwargs",
        "save_as",
        "on_error",
    }

    def __init__(
        self,
        workflow_file: Optional[str] = None,
        inline_workflows: Optional[List[Dict[str, Any]]] = None,
    ):
        self._workflow_file = workflow_file
        self._inline_workflows = inline_workflows or []
        self._workflows: List[Dict[str, Any]] = list(self._inline_workflows)
        if workflow_file:
            self.reload()
        elif self._inline_workflows:
            logger.info("Loaded %d inline workflow(s)", len(self._inline_workflows))

    def reload(self) -> None:
        """Reload workflow definitions from file."""
        self._workflows = list(self._inline_workflows)
        if not self._workflow_file:
            return

        workflow_path = Path(self._workflow_file)
        if not workflow_path.exists():
            logger.warning("Workflow file not found: %s", workflow_path)
            return

        try:
            import yaml

            content = yaml.safe_load(workflow_path.read_text(encoding="utf-8")) or {}
            file_workflows = content.get("workflows", []) or []
            self._workflows.extend(file_workflows)
            logger.info(
                "Loaded %d workflow(s) total (inline=%d, file=%d) from %s",
                len(self._workflows),
                len(self._inline_workflows),
                len(file_workflows),
                workflow_path,
            )
        except Exception as exc:
            logger.error("Failed to load workflows: %s", exc)

    async def handle_message(
        self,
        message: SECSMessage,
        context: Dict[str, Any],
    ) -> None:
        """Run matched workflows for one incoming message."""
        if not self._workflows:
            return

        variables = self._extract_variables(message, context)
        for workflow in self._workflows:
            trigger = workflow.get("trigger", {})
            if trigger.get("sf") != message.sf:
                continue
            if not self._trigger_matches(trigger, variables):
                continue

            logger.info("Workflow matched: %s (trigger=%s)", workflow.get("name", "unnamed"), message.sf)
            await self._run_steps(workflow.get("steps", []), message, context, variables=variables)

    async def _run_steps(
        self,
        steps: List[Dict[str, Any]],
        message: SECSMessage,
        context: Dict[str, Any],
        variables: Optional[Dict[str, Any]] = None,
        state: Optional[Dict[str, Any]] = None,
    ) -> bool:
        eap_api = context.get("eap_api")
        if not eap_api:
            logger.warning("Workflow skipped: eap_api not available in context")
            return False

        variables = variables or self._extract_variables(message, context)
        state = state or {
            "last_reply": None,
            "last_error": None,
            "last_mq_response": None,
        }
        self._sync_state_variables(variables, state)

        for idx, step in enumerate(steps, start=1):
            action = step.get("action")
            if action == "send_message":
                ok = await self._step_send_message(idx, step, eap_api, variables, state)
                if not ok:
                    return await self._handle_step_failure(idx, step, message, context, variables, state)
                self._sync_state_variables(variables, state)
                continue

            if action == "send_secs_msg":
                ok = await self._step_send_secs_msg(idx, step, eap_api, variables, state)
                if not ok:
                    return await self._handle_step_failure(idx, step, message, context, variables, state)
                self._sync_state_variables(variables, state)
                continue

            if action == "call_method":
                ok = await self._step_call_method(idx, step, eap_api, variables, state)
                if not ok:
                    return await self._handle_step_failure(idx, step, message, context, variables, state)
                self._sync_state_variables(variables, state)
                continue

            if isinstance(action, str) and action.startswith("mes_"):
                ok = await self._step_mes_tx(idx, step, eap_api, context, variables, state)
                if not ok:
                    return await self._handle_step_failure(idx, step, message, context, variables, state)
                self._sync_state_variables(variables, state)
                continue

            if action == "configure_collection_events":
                ok = await self._step_configure_collection_events(idx, step, eap_api, context, state)
                if not ok:
                    return await self._handle_step_failure(idx, step, message, context, variables, state)
                self._sync_state_variables(variables, state)
                continue

            if action == "if_hcack":
                await self._step_if_hcack(step, message, context, variables, state)
                continue

            if action == "wait_reply":
                self._step_wait_reply(idx, step, state)
                continue

            logger.warning("Unsupported workflow action at step %d: %s", idx, action)
        self._sync_state_variables(variables, state)
        return True

    async def _handle_step_failure(
        self,
        idx: int,
        step: Dict[str, Any],
        message: SECSMessage,
        context: Dict[str, Any],
        variables: Dict[str, Any],
        state: Dict[str, Any],
    ) -> bool:
        self._sync_state_variables(variables, state)
        variables["error_message"] = variables.get("last_error_message", "")
        variables["error_type"] = variables.get("last_error_type", "")
        variables["error_reply_sf"] = variables.get("last_reply_sf", "")
        variables["error_reply_ack"] = variables.get("last_reply_ack", "")
        variables["error_reply_text"] = variables.get("last_reply_text", "")
        variables["error_reply_error_text"] = variables.get("last_reply_error_text", "")
        on_error_steps = step.get("on_error") or []
        if not on_error_steps:
            return False
        if not isinstance(on_error_steps, list):
            logger.error(
                "Workflow step %d on_error ignored: on_error must be a list, got %s",
                idx,
                type(on_error_steps).__name__,
            )
            return False

        logger.info(
            "Workflow step %d failed, running on_error flow with %d step(s)",
            idx,
            len(on_error_steps),
        )
        await self._run_steps(
            on_error_steps,
            message,
            context,
            variables=variables,
            state=state,
        )
        self._sync_state_variables(variables, state)
        return False

    @staticmethod
    def _reply_to_text(reply: Optional[SECSMessage]) -> str:
        if not reply:
            return ""
        return repr(reply)

    def _extract_reply_error_text(self, reply: Optional[SECSMessage]) -> str:
        if not reply:
            return ""

        detail_texts: List[str] = []
        for item in (reply.items or [])[1:]:
            detail_texts.extend(self._flatten_item_texts(item))
        return " | ".join(text for text in detail_texts if text)

    def _flatten_item_texts(self, item: Optional[SECSItem]) -> List[str]:
        if item is None:
            return []
        if item.type == SECSType.LIST:
            texts: List[str] = []
            for child in item.children or []:
                texts.extend(self._flatten_item_texts(child))
            return texts
        value = item.value
        if value is None:
            return []
        if isinstance(value, bytes):
            text = value.hex().upper()
        else:
            text = str(value).strip()
        return [text] if text else []

    def _sync_state_variables(
        self,
        variables: Dict[str, Any],
        state: Dict[str, Any],
    ) -> None:
        last_error = state.get("last_error")
        last_reply = state.get("last_reply")
        last_mq_response = state.get("last_mq_response")
        last_method_result = state.get("last_method_result")

        variables["last_error_message"] = str(last_error or "").strip()
        variables["last_error_type"] = type(last_error).__name__ if last_error else ""
        variables["last_reply_sf"] = last_reply.sf if isinstance(last_reply, SECSMessage) else ""
        ack_code = self._extract_ack_code(last_reply) if isinstance(last_reply, SECSMessage) else None
        variables["last_reply_ack"] = "" if ack_code is None else ack_code
        variables["last_reply_text"] = self._reply_to_text(last_reply if isinstance(last_reply, SECSMessage) else None)
        variables["last_reply_error_text"] = ""

        if isinstance(last_error, SecsMessageError):
            reply = getattr(last_error, "reply", None)
            if isinstance(reply, SECSMessage):
                state["last_reply"] = reply
                variables["last_reply_sf"] = reply.sf
                ack_code = self._extract_ack_code(reply)
                variables["last_reply_ack"] = "" if ack_code is None else ack_code
                variables["last_reply_text"] = self._reply_to_text(reply)

            error_text = str(getattr(last_error, "error_text", "") or "").strip()
            variables["last_reply_error_text"] = error_text or self._extract_reply_error_text(reply)
        elif isinstance(last_reply, SECSMessage):
            variables["last_reply_error_text"] = self._extract_reply_error_text(last_reply)

        if last_mq_response is not None:
            variables["last_mq_response"] = last_mq_response
        if last_method_result is not None:
            variables["last_method_result"] = last_method_result

    async def _step_mes_tx(
        self,
        idx: int,
        step: Dict[str, Any],
        eap_api: Any,
        context: Dict[str, Any],
        variables: Dict[str, Any],
        state: Dict[str, Any],
    ) -> bool:
        action = str(step.get("action") or "")
        tx = self._substitute_workflow_value(step.get("transaction", {}) or {}, variables)
        tx = self._normalize_mes_tx_fields(tx)
        tx_name = self._resolve_mes_tx_name(action, tx)
        if not tx_name:
            state["last_error"] = RuntimeError(
                f"Workflow step {idx} MES TX failed: missing trx_id for action={action}"
            )
            logger.warning("%s", state["last_error"])
            return False
        tx.setdefault("trx_id", tx_name)
        request_type = get_tx_request_type(tx_name)
        if request_type is None:
            state["last_error"] = RuntimeError(f"Workflow step {idx} MES TX failed: unknown tx={tx_name}")
            logger.warning("%s", state["last_error"])
            return False

        if tx_name == "APCEQPST":
            try:
                tx = self._build_apceqpst_transaction(step, tx, context, variables)
            except Exception as exc:
                state["last_error"] = exc
                logger.warning("Workflow step %d MES TX failed: %s", idx, exc)
                return False

        tx = self._apply_default_user_id(tx, context)

        logger.info(
            "Workflow step %d: MES MQ TX %s (%s)",
            idx,
            tx_name,
            self._format_mes_tx_fields(tx),
        )

        if hasattr(eap_api, "is_mes_mq_ready") and not eap_api.is_mes_mq_ready():
            reason = None
            if hasattr(eap_api, "mes_mq_ready_reason"):
                try:
                    reason = eap_api.mes_mq_ready_reason()
                except Exception:
                    reason = None
            logger.warning(
                "Workflow step %d skipped: MES MQ not connected. "
                "Reason=%s. Please install ibmmq and IBM MQ client, then restart EAP.",
                idx,
                reason,
            )
            return True

        try:
            request = self._build_mes_tx_request(tx_name, request_type, tx)
            resp = await eap_api.execute_mes_tx(tx_name, request)
            state["last_mq_response"] = resp
            state["last_error"] = None
            raw = getattr(resp, "raw_payload", "") or ""
            if raw:
                logger.info("Workflow MES MQ reply(raw): %s", raw)
            else:
                logger.info("Workflow MES MQ reply: %s", resp)

            if tx_name == "APVRYOPE":
                port_context_store = context.get("port_context_store")
                if port_context_store:
                    try:
                        record = port_context_store.capture_apvryope(request, resp)
                        logger.info(
                            "Port context captured: eqpt_id=%s port_id=%s carrier_id=%s lot_id=%s recipe_id=%s",
                            record.eqpt_id,
                            record.port_id,
                            record.carrier_id,
                            record.lot_id,
                            record.recipe_id,
                        )
                    except Exception as exc:
                        logger.warning("Failed to capture APVRYOPE port context: %s", exc)
            return True
        except Exception as exc:
            state["last_error"] = exc
            logger.warning("Workflow step %d MES MQ failed: %s", idx, exc)
            return False

    def _build_apceqpst_transaction(
        self,
        step: Dict[str, Any],
        tx: Dict[str, Any],
        context: Dict[str, Any],
        variables: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Normalize the fixed APCEQPST payload so YAML can stay compact."""
        merged: Dict[str, Any] = dict(tx or {})
        step_tx = step.get("transaction") if isinstance(step.get("transaction"), dict) else {}

        def _pick(key: str) -> Any:
            if key in merged and merged.get(key) not in (None, ""):
                return merged.get(key)
            if key in step_tx and step_tx.get(key) not in (None, ""):
                return self._substitute_workflow_value(step_tx.get(key), variables)
            if key in step and step.get(key) not in (None, ""):
                return self._substitute_workflow_value(step.get(key), variables)
            return None

        eqpt_mode = str(_pick("eqpt_mode") or "").strip().upper()
        if eqpt_mode not in {"AUTO", "MANU"}:
            raise RuntimeError(
                "Workflow step APCEQPST requires eqpt_mode=AUTO or eqpt_mode=MANU"
            )

        eqpt_id = str(
            _pick("eqpt_id")
            or context.get("equipment_id")
            or context.get("mes_equipment_id")
            or ""
        ).strip()
        if not eqpt_id:
            raise RuntimeError("Workflow step APCEQPST requires an equipment id")

        merged.update(
            {
                "trx_id": "APCEQPST",
                "type_id": "I",
                "eqpt_id": eqpt_id,
                "eqpt_mode": eqpt_mode,
                "user_id": str(_pick("user_id") or "").strip(),
                "orig_opi_flg": str(_pick("orig_opi_flg") or "N").strip() or "N",
                "clm_eqst_typ": str(_pick("clm_eqst_typ") or "A").strip() or "A",
                "eqpt_stat": "" if _pick("eqpt_stat") is None else str(_pick("eqpt_stat")),
            }
        )
        return merged

    def _apply_default_user_id(self, tx: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(tx, dict):
            return tx

        if str(tx.get("user_id", "") or "").strip():
            return tx

        default_user_id = str(
            context.get("equipment_user_id")
            or context.get("user_id")
            or ""
        ).strip()
        if not default_user_id:
            return tx

        merged = dict(tx)
        merged["user_id"] = default_user_id
        return merged

    def _build_mes_tx_request(self, tx_name: str, request_type: Any, tx: Dict[str, Any]) -> Any:
        try:
            if is_dataclass(request_type):
                self._validate_mes_tx_fields(tx_name, request_type, tx)
                return build_tx_dataclass(request_type, tx)
            return request_type(**tx)
        except TypeError as exc:
            allowed = self._describe_request_fields(request_type)
            if allowed:
                raise RuntimeError(
                    f"Invalid fields for MES TX {tx_name}: {exc}. Allowed fields: {allowed}"
                ) from exc
            raise RuntimeError(f"Invalid fields for MES TX {tx_name}: {exc}") from exc

    def _validate_mes_tx_fields(self, tx_name: str, request_type: Any, tx: Dict[str, Any]) -> None:
        allowed_fields = {field.name.lower(): field.name for field in fields(request_type)}
        unknown_fields = [
            key for key in tx.keys()
            if str(key).lower() not in allowed_fields
        ]
        if unknown_fields:
            allowed = ", ".join(allowed_fields[name] for name in sorted(allowed_fields))
            unknown = ", ".join(str(key) for key in unknown_fields)
            raise RuntimeError(
                f"Invalid fields for MES TX {tx_name}: {unknown}. Allowed fields: {allowed}"
            )

    def _describe_request_fields(self, request_type: Any) -> str:
        if is_dataclass(request_type):
            return ", ".join(field.name for field in fields(request_type))
        return ""

    def _resolve_mes_tx_name(self, action: str, tx: Dict[str, Any]) -> str:
        tx_name = str(tx.get("trx_id", "") or "").strip().upper()
        if tx_name:
            return tx_name
        normalized_action = str(action or "").strip().lower()
        if normalized_action.startswith("mes_") and normalized_action != "mes_tx":
            return normalized_action[4:].upper()
        return ""

    def _normalize_mes_port_id(self, value: Any) -> Any:
        if value is None:
            return value
        text = str(value).strip()
        if text.isdigit():
            return str(int(text)).zfill(2)
        return value

    def _normalize_mes_tx_fields(self, value: Any) -> Any:
        if isinstance(value, list):
            return [self._normalize_mes_tx_fields(item) for item in value]
        if isinstance(value, dict):
            normalized: Dict[str, Any] = {}
            for key, item in value.items():
                normalized_item = self._normalize_mes_tx_fields(item)
                key_text = str(key or "").strip().lower()
                if key_text in {"port_id", "eqp_port_id", "logof_port_id"}:
                    normalized_item = self._normalize_mes_port_id(normalized_item)
                normalized[key] = normalized_item
            return normalized
        return value

    def _format_mes_tx_fields(self, tx: Dict[str, Any]) -> str:
        parts = []
        for key, value in tx.items():
            if key == "trx_id" or value in (None, ""):
                continue
            parts.append(f"{key}={value}")
        return " ".join(parts)

    def _substitute_workflow_value(self, value: Any, variables: Dict[str, Any]) -> Any:
        if isinstance(value, str):
            result = value
            for key, raw in variables.items():
                result = result.replace(f"${{{key}}}", "" if raw is None else str(raw))
            return result
        if isinstance(value, list):
            return [self._substitute_workflow_value(item, variables) for item in value]
        if isinstance(value, dict):
            return {
                key: self._substitute_workflow_value(item, variables)
                for key, item in value.items()
            }
        return value

    async def _step_configure_collection_events(
        self,
        idx: int,
        step: Dict[str, Any],
        eap_api: Any,
        context: Dict[str, Any],
        state: Dict[str, Any],
    ) -> bool:
        raw_config = step.get("config") or context.get("collection_event_config") or {}
        builder = EventReportSetupBuilder(raw_config)
        enable_mode = step.get("enable_mode")
        commands = builder.build_commands(enable_mode=enable_mode)
        timeout = step.get("timeout")

        if not builder.schema.reports:
            logger.warning(
                "Workflow step %d skipped: no collection event reports configured for configure_collection_events",
                idx,
            )
            return True

        logger.info(
            "Workflow step %d: configure collection events reports=%d events=%d enable=%s",
            idx,
            len(builder.schema.reports),
            len(builder.schema.events),
            enable_mode or builder.options.enable_mode,
        )

        for command in commands:
            logger.info(
                "Workflow step %d: send S%dF%d and wait %s (%s)",
                idx,
                command.stream,
                command.function,
                command.expected_reply_sf,
                command.name,
            )
            reply = await eap_api.send_message(
                stream=command.stream,
                function=command.function,
                items=command.items,
                wait_reply=True,
                timeout=timeout,
            )
            state["last_reply"] = reply
            ack = self._extract_ack_code(reply)
            ack_text = format_reply_ack(reply.sf if reply else command.expected_reply_sf, ack)
            if not reply or reply.sf != command.expected_reply_sf:
                state["last_error"] = RuntimeError(
                    f"{command.name} expected {command.expected_reply_sf}, got {reply.sf if reply else 'no reply'}"
                )
                logger.warning("Workflow step %d %s failed: %s", idx, command.name, state["last_error"])
                return False
            if ack != 0:
                state["last_error"] = RuntimeError(
                    f"{command.name} {ack_text} from {command.expected_reply_sf}"
                )
                logger.warning(
                    "Workflow step %d %s failed: %s",
                    idx,
                    command.name,
                    ack_text,
                )
                return False
            logger.info(
                "Workflow step %d: %s acknowledged by %s %s",
                idx,
                command.name,
                reply.sf,
                ack_text,
            )

        state["last_error"] = None
        return True

    async def _step_send_message(
        self,
        idx: int,
        step: Dict[str, Any],
        eap_api: Any,
        variables: Dict[str, Any],
        state: Dict[str, Any],
    ) -> bool:
        stream = int(step.get("stream"))
        function = int(step.get("function"))
        wait_reply = bool(step.get("wait_reply", True))
        timeout = step.get("timeout")
        items = self._build_items(step.get("items", []), variables)
        retries = int(step.get("retries", 0))
        retry_interval = float(step.get("retry_interval", 0.5))

        logger.info(
            "Workflow step %d: send S%dF%d wait_reply=%s retries=%d",
            idx,
            stream,
            function,
            wait_reply,
            retries,
        )

        attempts = retries + 1
        for attempt in range(1, attempts + 1):
            try:
                reply = await eap_api.send_message(
                    stream=stream,
                    function=function,
                    items=items,
                    wait_reply=wait_reply,
                    timeout=timeout,
                )
                state["last_reply"] = reply
                state["last_error"] = None

                if wait_reply and reply is None:
                    raise TimeoutError(f"No reply for S{stream}F{function}")
                return True
            except Exception as exc:
                state["last_error"] = exc
                logger.warning(
                    "Workflow send failed attempt %d/%d for S%dF%d: %s",
                    attempt,
                    attempts,
                    stream,
                    function,
                    exc,
                )
                if attempt < attempts:
                    await asyncio.sleep(retry_interval)
                else:
                    logger.error("Workflow step %d failed after retries", idx)
                    return False
        return False

    async def _step_call_method(
        self,
        idx: int,
        step: Dict[str, Any],
        eap_api: Any,
        variables: Dict[str, Any],
        state: Dict[str, Any],
    ) -> bool:
        method_name = str(step.get("method", "") or "").strip()
        if not method_name:
            state["last_error"] = RuntimeError(
                f"Workflow step {idx} call_method failed: missing method"
            )
            logger.error("%s", state["last_error"])
            return False
        if method_name.startswith("_"):
            state["last_error"] = RuntimeError(
                f"Workflow step {idx} call_method failed: private method is not allowed ({method_name})"
            )
            logger.error("%s", state["last_error"])
            return False

        method_owner = None
        method = None
        method_candidates: List[str] = []
        for candidate_name in (
            method_name,
            str(method_name or "").strip().lower(),
        ):
            normalized_name = str(candidate_name or "").strip()
            if normalized_name and normalized_name not in method_candidates:
                method_candidates.append(normalized_name)

        for candidate in (
            getattr(eap_api, "call_method_service", None),
            eap_api,
        ):
            if candidate is None:
                continue
            for candidate_name in method_candidates:
                current = getattr(candidate, candidate_name, None)
                if callable(current):
                    method_owner = candidate
                    method = current
                    break
            if callable(method):
                break
        if not callable(method):
            state["last_error"] = RuntimeError(
                f"Workflow step {idx} call_method failed: unknown method={method_name}"
            )
            logger.error("%s", state["last_error"])
            return False

        raw_args = step.get("args", []) or []
        if not isinstance(raw_args, (list, tuple)):
            state["last_error"] = RuntimeError(
                f"Workflow step {idx} call_method failed: args must be a list"
            )
            logger.error("%s", state["last_error"])
            return False

        raw_params = step.get("params", step.get("kwargs"))
        if raw_params is None:
            raw_params = {
                key: value
                for key, value in step.items()
                if key not in self._STEP_CONTROL_KEYS
            }
        if not isinstance(raw_params, dict):
            state["last_error"] = RuntimeError(
                f"Workflow step {idx} call_method failed: params must be a mapping"
            )
            logger.error("%s", state["last_error"])
            return False

        args = self._substitute_workflow_value(list(raw_args), variables)
        params = self._substitute_workflow_value(dict(raw_params), variables)

        logger.info(
            "Workflow step %d: call method %s via %s args=%s kwargs=%s",
            idx,
            method_name,
            type(method_owner).__name__ if method_owner is not None else "unknown",
            args,
            params,
        )

        try:
            result = method(*args, **params)
            if asyncio.iscoroutine(result):
                result = await result

            state["last_method_result"] = result
            if isinstance(result, SECSMessage):
                state["last_reply"] = result
            state["last_error"] = None

            save_as = str(step.get("save_as", "") or "").strip()
            if save_as:
                state[save_as] = result
                variables[save_as] = result
            return True
        except Exception as exc:
            state["last_error"] = exc
            if isinstance(exc, (MesReplyError, SecsMessageError)):
                logger.error(
                    "Workflow step %d call_method %s failed: %s",
                    idx,
                    method_name,
                    exc,
                )
            else:
                logger.error(
                    "Workflow step %d call_method %s failed: %s",
                    idx,
                    method_name,
                    exc,
                    exc_info=True,
                )
            return False

    async def _step_send_secs_msg(
        self,
        idx: int,
        step: Dict[str, Any],
        eap_api: Any,
        variables: Dict[str, Any],
        state: Dict[str, Any],
    ) -> bool:
        secs_msg_service = getattr(eap_api, "secs_msg_service", None)
        if secs_msg_service is None:
            state["last_error"] = RuntimeError(
                f"Workflow step {idx} send_secs_msg failed: secs_msg_service not available"
            )
            logger.error("%s", state["last_error"])
            return False

        method_name = str(step.get("method", "") or "").strip()
        if method_name.startswith("_"):
            state["last_error"] = RuntimeError(
                f"Workflow step {idx} send_secs_msg failed: private method is not allowed ({method_name})"
            )
            logger.error("%s", state["last_error"])
            return False

        raw_args = step.get("args", []) or []
        if not isinstance(raw_args, (list, tuple)):
            state["last_error"] = RuntimeError(
                f"Workflow step {idx} send_secs_msg failed: args must be a list"
            )
            logger.error("%s", state["last_error"])
            return False

        raw_params = step.get("params", step.get("kwargs"))
        if raw_params is None:
            raw_params = {
                key: value
                for key, value in step.items()
                if key not in self._STEP_CONTROL_KEYS
            }
        if not isinstance(raw_params, dict):
            state["last_error"] = RuntimeError(
                f"Workflow step {idx} send_secs_msg failed: params must be a mapping"
            )
            logger.error("%s", state["last_error"])
            return False

        args = self._substitute_workflow_value(list(raw_args), variables)
        params = self._substitute_workflow_value(dict(raw_params), variables)

        method = None
        if method_name:
            method = getattr(secs_msg_service, method_name, None)
            if not callable(method):
                state["last_error"] = RuntimeError(
                    f"Workflow step {idx} send_secs_msg failed: unknown method={method_name}"
                )
                logger.error("%s", state["last_error"])
                return False
        elif "template_name" in params:
            method_name = "send_secs_template"
            method = getattr(secs_msg_service, method_name)
        elif "script" in params:
            method_name = "send_secs_script"
            method = getattr(secs_msg_service, method_name)
        else:
            state["last_error"] = RuntimeError(
                f"Workflow step {idx} send_secs_msg failed: missing method/template_name/script"
            )
            logger.error("%s", state["last_error"])
            return False

        logger.info(
            "Workflow step %d: send secs msg %s via %s args=%s kwargs=%s",
            idx,
            method_name,
            type(secs_msg_service).__name__,
            args,
            params,
        )

        try:
            result = method(*args, **params)
            if asyncio.iscoroutine(result):
                result = await result

            state["last_method_result"] = result
            if isinstance(result, SECSMessage):
                state["last_reply"] = result
            elif isinstance(result, dict):
                reply = result.get("reply")
                if isinstance(reply, SECSMessage):
                    state["last_reply"] = reply
            state["last_error"] = None

            save_as = str(step.get("save_as", "") or "").strip()
            if save_as:
                state[save_as] = result
                variables[save_as] = result
            return True
        except Exception as exc:
            state["last_error"] = exc
            if isinstance(exc, SecsMessageError):
                logger.error(
                    "Workflow step %d send_secs_msg %s failed: %s",
                    idx,
                    method_name,
                    exc,
                )
            else:
                logger.error(
                    "Workflow step %d send_secs_msg %s failed: %s",
                    idx,
                    method_name,
                    exc,
                    exc_info=True,
                )
            return False

    async def _step_if_hcack(
        self,
        step: Dict[str, Any],
        message: SECSMessage,
        context: Dict[str, Any],
        variables: Dict[str, Any],
        state: Dict[str, Any],
    ) -> None:
        reply = state.get("last_reply")
        expected = int(step.get("equals", 0))
        then_steps = step.get("then", []) or []
        else_steps = step.get("else", []) or []

        actual = self._extract_hcack(reply)
        matched = (actual == expected)
        logger.info("Workflow if_hcack: actual=%s expected=%s matched=%s", actual, expected, matched)

        if matched:
            await self._run_steps(then_steps, message, context, variables=variables, state=state)
        else:
            await self._run_steps(else_steps, message, context, variables=variables, state=state)

    def _step_wait_reply(self, idx: int, step: Dict[str, Any], state: Dict[str, Any]) -> None:
        expected_sf = step.get("expect_sf")
        reply = state.get("last_reply")
        if not reply:
            logger.warning("Workflow step %d wait_reply has no last_reply", idx)
            return
        if expected_sf and reply.sf != expected_sf:
            logger.warning(
                "Workflow step %d wait_reply mismatch: expected=%s actual=%s",
                idx,
                expected_sf,
                reply.sf,
            )

    def _extract_hcack(self, reply: Optional[SECSMessage]) -> Optional[int]:
        if not reply or not reply.items:
            return None
        first = reply.items[0]
        try:
            if first.value is not None:
                return int(first.value)
        except Exception:
            return None
        return None

    def _extract_ack_code(self, reply: Optional[SECSMessage]) -> Optional[int]:
        return SecsMessageCommonMixin._extract_ack_code(reply)

    def _extract_variables(
        self,
        message: SECSMessage,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        vars_: Dict[str, Any] = {"sf": message.sf}
        context = context or {}
        for key in ("equipment_id", "mes_equipment_id", "equipment_user_id"):
            value = context.get(key)
            if value not in (None, ""):
                vars_[key] = value
        collection_event = context.get("collection_event")
        if isinstance(collection_event, dict):
            vars_["data_id"] = collection_event.get("data_id")
            vars_["ceid"] = collection_event.get("ceid", "")
            vars_["event_name"] = collection_event.get("name", "")
            reports = collection_event.get("reports", []) or []
            rptids = [report.get("rptid") for report in reports if report.get("rptid") not in (None, "")]
            if rptids:
                vars_["rptids"] = rptids
                vars_["rptid"] = rptids[0] if len(rptids) == 1 else rptids
            vars_.update(collection_event.get("fields", {}))
        return vars_

    def _trigger_matches(self, trigger: Dict[str, Any], variables: Dict[str, Any]) -> bool:
        """Check optional workflow trigger filters beyond S/F."""
        for key, expected in (trigger or {}).items():
            if key == "sf":
                continue
            actual = variables.get(key)
            if not self._trigger_value_matches(actual, expected):
                return False
        return True

    def _trigger_value_matches(self, actual: Any, expected: Any) -> bool:
        if expected is None:
            return True
        if actual is None:
            return False

        if isinstance(actual, (list, tuple, set)):
            actual_values = {str(value) for value in actual}
            if isinstance(expected, (list, tuple, set)):
                return all(str(value) in actual_values for value in expected)
            return str(expected) in actual_values

        if isinstance(expected, (list, tuple, set)):
            return str(actual) in {str(value) for value in expected}

        return str(actual) == str(expected)

    def _build_items(self, item_defs: List[Dict[str, Any]], vars_: Dict[str, Any]) -> List[SECSItem]:
        return [self._build_item(item_def, vars_) for item_def in item_defs]

    def _build_item(self, item_def: Dict[str, Any], vars_: Dict[str, Any]) -> SECSItem:
        item_type = str(item_def.get("type", "A")).upper()

        if item_type == "L":
            children = [self._build_item(child, vars_) for child in item_def.get("items", [])]
            return SECSItem.list_(children)

        value = item_def.get("value")
        if isinstance(value, str):
            for key, raw in vars_.items():
                value = value.replace(f"${{{key}}}", "" if raw is None else str(raw))

        if item_type == "A":
            return SECSItem.ascii("" if value is None else str(value))
        if item_type in ("BOOLEAN", "BOOL", "BL"):
            if isinstance(value, str):
                return SECSItem.boolean(value.strip().upper() in ("1", "T", "TRUE", "Y", "YES", "ON"))
            return SECSItem.boolean(bool(value))
        if item_type == "U1":
            return SECSItem.uint1(int(value or 0))
        if item_type == "U2":
            return SECSItem.uint2(int(value or 0))
        if item_type == "U4":
            return SECSItem.uint4(int(value or 0))
        if item_type == "I1":
            return SECSItem.int1(int(value or 0))
        if item_type == "I2":
            return SECSItem.int2(int(value or 0))
        if item_type == "I4":
            return SECSItem.int4(int(value or 0))
        if item_type == "B":
            if isinstance(value, str):
                return SECSItem.binary(value.encode("ascii"))
            if isinstance(value, bytes):
                return SECSItem.binary(value)
            return SECSItem.binary(b"")

        logger.warning("Unknown item type in workflow: %s, fallback to ASCII", item_type)
        return SECSItem.ascii("" if value is None else str(value))
