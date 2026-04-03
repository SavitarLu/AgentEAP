"""
Inbound MES TX request handling.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

from secs_driver.src.secs_message import SECSItem, SECSMessage
from secs_driver.src.secs_types import SECSType

from ..mes.mq_service import InboundMesTxMessage
from ..mes.tx.rplrptcs import RPLRPTCSOA1, RPLRPTCSResponse


logger = logging.getLogger(__name__)


def _strip_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.hex().upper()
    return str(value).strip()


def _collect_recipe_ids(item: Optional[SECSItem]) -> List[str]:
    if item is None:
        return []
    if item.type == SECSType.LIST:
        result: List[str] = []
        for child in item.children:
            result.extend(_collect_recipe_ids(child))
        return [recipe_id for recipe_id in result if recipe_id]
    value = _strip_text(item.value)
    return [value] if value else []


class MesTxService:
    """Handle inbound MES TX requests that need device-side SECS actions."""

    def __init__(self, equipment_id: str = "", s7f19_timeout: float = 180.0):
        self._equipment_id = str(equipment_id or "").strip()
        self._s7f19_timeout = float(s7f19_timeout or 180.0)

    async def handle_request(self, inbound: InboundMesTxMessage, eap_api: Any) -> Any:
        tx_name = str(inbound.tx_name or "").strip().upper()
        if tx_name == "RPLRPTCS":
            return await self._handle_rplrptcs(inbound, eap_api)

        logger.info("No inbound MES TX handler registered for %s", tx_name)
        return None

    async def _handle_rplrptcs(self, inbound: InboundMesTxMessage, eap_api: Any) -> RPLRPTCSResponse:
        eqpt_id = self._resolve_equipment_id(inbound)
        logger.info("Handling inbound RPLRPTCS for eqpt_id=%s", eqpt_id)

        reply = await eap_api.send_message(
            stream=7,
            function=19,
            items=[],
            wait_reply=True,
            timeout=self._s7f19_timeout,
        )
        if not reply or reply.sf != "S7F20":
            actual = reply.sf if reply else "no reply"
            logger.warning("RPLRPTCS S7F19 query failed: expected S7F20, got %s", actual)
            return RPLRPTCSResponse(
                rtn_code="1",
                rtn_mesg=f"S7F19 expected S7F20, got {actual}",
                eqpt_id=eqpt_id,
                arycnt1="0",
                oary1=[],
            )

        recipe_ids = self._extract_s7f20_recipe_ids(reply)
        logger.info("RPLRPTCS recipe list collected: count=%d", len(recipe_ids))
        return RPLRPTCSResponse(
            rtn_code="0",
            rtn_mesg="SUCCESS",
            eqpt_id=eqpt_id,
            arycnt1=str(len(recipe_ids)),
            oary1=[RPLRPTCSOA1(recipe_id=recipe_id, recipe_cat="") for recipe_id in recipe_ids],
        )

    def _resolve_equipment_id(self, inbound: InboundMesTxMessage) -> str:
        for key in ("eqp_id", "eqpt_id"):
            value = str(getattr(inbound.request, key, "") or "").strip()
            if value:
                return value

        root = inbound.payload.get("transaction", inbound.payload) if isinstance(inbound.payload, dict) else {}
        if isinstance(root, dict):
            for key in ("eqp_id", "eqpt_id", "EQP_ID", "EQPT_ID"):
                value = str(root.get(key, "") or "").strip()
                if value:
                    return value

        if inbound.appl_identity_data:
            return str(inbound.appl_identity_data).strip()
        return self._equipment_id

    @staticmethod
    def _extract_s7f20_recipe_ids(reply: SECSMessage) -> List[str]:
        recipe_ids: List[str] = []
        for item in reply.items or []:
            recipe_ids.extend(_collect_recipe_ids(item))
        seen = set()
        ordered: List[str] = []
        for recipe_id in recipe_ids:
            if recipe_id in seen:
                continue
            seen.add(recipe_id)
            ordered.append(recipe_id)
        return ordered
