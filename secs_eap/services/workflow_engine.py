"""
Lightweight workflow engine prototype.

Purpose:
- Trigger follow-up SECS actions after specific incoming messages.
- Keep beginner customization in YAML instead of Python code.
"""

import logging
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

from secs_driver.src.secs_message import SECSItem, SECSMessage


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

        for workflow in self._workflows:
            trigger = workflow.get("trigger", {})
            if trigger.get("sf") != message.sf:
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

        variables = self._extract_variables(message)
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

            if action == "mes_apvryope":
                ok = await self._step_mes_apvryope(idx, step, eap_api, variables, state)
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

    async def _step_mes_apvryope(
        self,
        idx: int,
        step: Dict[str, Any],
        eap_api: Any,
        variables: Dict[str, Any],
        state: Dict[str, Any],
    ) -> bool:
        tx = step.get("transaction", {}) or {}

        def sub(v: Any) -> Any:
            if not isinstance(v, str):
                return v
            out = v
            for key, raw in variables.items():
                out = out.replace(f"${{{key}}}", "" if raw is None else str(raw))
            return out

        trx_id = sub(tx.get("trx_id", "APVRYOPE")) or "APVRYOPE"
        eqpt_id = sub(tx.get("eqpt_id", "")) or ""
        port_id = sub(tx.get("port_id", "")) or ""
        crr_id = sub(tx.get("crr_id", "")) or ""
        user_id = sub(tx.get("user_id", "")) or ""

        logger.info(
            "Workflow step %d: MES MQ TX %s (eqpt_id=%s port_id=%s crr_id=%s user_id=%s)",
            idx,
            trx_id,
            eqpt_id,
            port_id,
            crr_id,
            user_id,
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
                "Reason=%s. Please install pymqi and IBM MQ client, then restart EAP.",
                idx,
                reason,
            )
            return True

        try:
            resp = await eap_api.query_lot_by_apvryope(
                eqpt_id=eqpt_id,
                port_id=port_id,
                crr_id=crr_id,
                user_id=user_id,
                trx_id=trx_id,
            )
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

    def _extract_variables(self, message: SECSMessage) -> Dict[str, Any]:
        vars_: Dict[str, Any] = {"sf": message.sf}
        # Friendly example variable for S6F11-like flow.
        if message.sf == "S6F11" and message.items:
            vars_["job_id"] = message.items[0].value
        return vars_

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

