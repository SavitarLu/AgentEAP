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
from .event_report_setup import EventReportSetupBuilder
from .reply_meanings import format_reply_ack


logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Simple YAML-driven workflow runner."""

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
            await self._run_steps(workflow.get("steps", []), message, context)

    async def _run_steps(
        self,
        steps: List[Dict[str, Any]],
        message: SECSMessage,
        context: Dict[str, Any],
    ) -> None:
        eap_api = context.get("eap_api")
        if not eap_api:
            logger.warning("Workflow skipped: eap_api not available in context")
            return

        variables = self._extract_variables(message, context)
        state: Dict[str, Any] = {
            "last_reply": None,
            "last_error": None,
            "last_mq_response": None,
        }

        for idx, step in enumerate(steps, start=1):
            action = step.get("action")
            if action == "send_message":
                ok = await self._step_send_message(idx, step, eap_api, variables, state)
                if not ok:
                    break
                continue

            if isinstance(action, str) and action.startswith("mes_"):
                ok = await self._step_mes_tx(idx, step, eap_api, variables, state)
                if not ok:
                    break
                continue

            if action == "configure_collection_events":
                ok = await self._step_configure_collection_events(idx, step, eap_api, context, state)
                if not ok:
                    break
                continue

            if action == "if_hcack":
                await self._step_if_hcack(step, message, context, variables, state)
                continue

            if action == "wait_reply":
                self._step_wait_reply(idx, step, state)
                continue

            logger.warning("Unsupported workflow action at step %d: %s", idx, action)

    async def _step_mes_tx(
        self,
        idx: int,
        step: Dict[str, Any],
        eap_api: Any,
        variables: Dict[str, Any],
        state: Dict[str, Any],
    ) -> bool:
        action = str(step.get("action") or "")
        tx = self._substitute_workflow_value(step.get("transaction", {}) or {}, variables)
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
            return True
        except Exception as exc:
            state["last_error"] = exc
            logger.warning("Workflow step %d MES MQ failed: %s", idx, exc)
            return False

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
            await self._run_steps(then_steps, message, context)
        else:
            await self._run_steps(else_steps, message, context)

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
        if not reply or not reply.items:
            return None
        first = reply.items[0]
        value = first.value
        try:
            if first.type == SECSType.BOOLEAN:
                return 1 if bool(value) else 0
            if isinstance(value, bytes):
                return value[0] if value else 0
            if isinstance(value, bool):
                return 1 if value else 0
            if value is not None:
                return int(value)
        except Exception:
            return None
        return None

    def _extract_variables(
        self,
        message: SECSMessage,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        vars_: Dict[str, Any] = {"sf": message.sf}
        context = context or {}
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
