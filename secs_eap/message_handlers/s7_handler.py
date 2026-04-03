"""
S7 process program / recipe message handlers.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from secs_driver.src.secs_message import SECSItem, SECSMessage
from secs_driver.src.secs_types import SECSType

from .base_handler import BaseMessageHandler, HandlerResult, StreamHandlerManager


logger = logging.getLogger(__name__)


ACKC7_ACCEPTED = 0
ACKC7_DENIED = 1
ACKC7_LENGTH_ERROR = 2
ACKC7_FORMAT_ERROR = 3
ACKC7_PPID_NOT_FOUND = 4

PPGNT_GRANTED = 0
PPGNT_DENIED = 1


def _strip_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.hex().upper()
    return str(value).strip()


def _first_item(message: SECSMessage) -> Optional[SECSItem]:
    return message.items[0] if message.items else None


def _parse_ppid(item: Optional[SECSItem]) -> str:
    if item is None:
        return ""
    if item.type == SECSType.LIST:
        for child in item.children:
            ppid = _parse_ppid(child)
            if ppid:
                return ppid
        return ""
    return _strip_text(item.value)


def _collect_ppids(item: Optional[SECSItem]) -> List[str]:
    if item is None:
        return []
    if item.type == SECSType.LIST:
        result: List[str] = []
        for child in item.children:
            result.extend(_collect_ppids(child))
        return [value for value in result if value]
    value = _strip_text(item.value)
    return [value] if value else []


def _empty_recipe_body(reply_sf: str) -> SECSItem:
    if reply_sf == "S7F26":
        return SECSItem.list_([])
    return SECSItem.ascii("")


class S7F1Handler(BaseMessageHandler):
    """S7F1 - Process Program Load Inquire."""

    def __init__(self):
        super().__init__("S7F1Handler")

    def can_handle(self, message: SECSMessage) -> bool:
        return message.stream == 7 and message.function == 1

    async def handle(self, message: SECSMessage, context: Dict[str, Any]) -> HandlerResult:
        logger.info("Received S7F1: Process Program Load Inquire")
        recipe_service = context.get("recipe_service")
        ppid = _parse_ppid(_first_item(message))
        if not recipe_service:
            logger.warning("S7F1 denied: recipe_service not available")
            return HandlerResult(
                success=True,
                message="S7F1 denied: recipe_service not available",
                reply_items=[SECSItem.uint1(PPGNT_DENIED)],
            )

        allowed, ppgnt, reason = recipe_service.can_accept_upload(ppid)
        logger.info("S7F1 load inquire: ppid=%s allowed=%s reason=%s", ppid, allowed, reason)
        return HandlerResult(
            success=True,
            message=f"S7F1 handled, PPGNT={ppgnt}, reason={reason}",
            reply_items=[SECSItem.uint1(ppgnt)],
            data={"ppid": ppid, "allowed": allowed, "reason": reason},
        )


class S7F3Handler(BaseMessageHandler):
    """S7F3 - Process Program Send (host uploads recipe body)."""

    def __init__(self):
        super().__init__("S7F3Handler")

    def can_handle(self, message: SECSMessage) -> bool:
        return message.stream == 7 and message.function == 3

    async def handle(self, message: SECSMessage, context: Dict[str, Any]) -> HandlerResult:
        logger.info("Received S7F3: Process Program Send")
        recipe_service = context.get("recipe_service")
        if not recipe_service:
            logger.warning("S7F3 denied: recipe_service not available")
            return HandlerResult(
                success=True,
                message="S7F3 denied: recipe_service not available",
                reply_items=[SECSItem.uint1(ACKC7_DENIED)],
            )

        if len(message.items) < 2:
            logger.warning("S7F3 rejected: expected PPID and PPBODY, got %d item(s)", len(message.items))
            return HandlerResult(
                success=True,
                message="S7F3 rejected: expected PPID and PPBODY",
                reply_items=[SECSItem.uint1(ACKC7_LENGTH_ERROR)],
            )

        ppid = _parse_ppid(message.items[0])
        body_item = message.items[1]
        if not ppid:
            return HandlerResult(
                success=True,
                message="S7F3 rejected: PPID is empty",
                reply_items=[SECSItem.uint1(ACKC7_FORMAT_ERROR)],
            )

        try:
            recipe_service.save_recipe(ppid, body_item, source="S7F3")
            return HandlerResult(
                success=True,
                message=f"S7F3 handled, recipe saved: {ppid}",
                reply_items=[SECSItem.uint1(ACKC7_ACCEPTED)],
                data={"ppid": ppid, "body_type": body_item.type.name},
            )
        except FileExistsError as exc:
            logger.warning("S7F3 denied for %s: %s", ppid, exc)
            return HandlerResult(
                success=True,
                message=str(exc),
                reply_items=[SECSItem.uint1(ACKC7_DENIED)],
            )
        except Exception as exc:
            logger.exception("S7F3 failed for %s: %s", ppid, exc)
            return HandlerResult(
                success=True,
                message=str(exc),
                reply_items=[SECSItem.uint1(ACKC7_FORMAT_ERROR)],
            )


class _BaseRecipeQueryHandler(BaseMessageHandler):
    """Shared logic for S7F5/S7F25 recipe body queries."""

    request_name = ""
    reply_sf = ""

    async def _handle_query(self, message: SECSMessage, context: Dict[str, Any]) -> HandlerResult:
        recipe_service = context.get("recipe_service")
        ppid = _parse_ppid(_first_item(message))
        logger.info("Received %s: recipe body query for ppid=%s", message.sf, ppid)

        if not recipe_service:
            logger.warning("%s fallback: recipe_service not available", message.sf)
            return HandlerResult(
                success=True,
                message=f"{message.sf} fallback: recipe_service not available",
                reply_items=[SECSItem.ascii(ppid), _empty_recipe_body(self.reply_sf)],
            )

        recipe = recipe_service.get_recipe(ppid)
        if not recipe:
            logger.warning("%s recipe not found: %s", message.sf, ppid)
            return HandlerResult(
                success=True,
                message=f"{message.sf} recipe not found: {ppid}",
                reply_items=[SECSItem.ascii(ppid), _empty_recipe_body(self.reply_sf)],
                data={"ppid": ppid, "found": False},
            )

        return HandlerResult(
            success=True,
            message=f"{message.sf} handled, returned recipe: {ppid}",
            reply_items=[SECSItem.ascii(recipe.ppid), recipe.body],
            data={"ppid": recipe.ppid, "found": True, "body_type": recipe.body_type},
        )


class S7F5Handler(_BaseRecipeQueryHandler):
    """S7F5 - Process Program Request (unformatted body)."""

    reply_sf = "S7F6"

    def __init__(self):
        super().__init__("S7F5Handler")

    def can_handle(self, message: SECSMessage) -> bool:
        return message.stream == 7 and message.function == 5

    async def handle(self, message: SECSMessage, context: Dict[str, Any]) -> HandlerResult:
        return await self._handle_query(message, context)


class S7F17Handler(BaseMessageHandler):
    """S7F17 - Process Program Delete."""

    def __init__(self):
        super().__init__("S7F17Handler")

    def can_handle(self, message: SECSMessage) -> bool:
        return message.stream == 7 and message.function == 17

    async def handle(self, message: SECSMessage, context: Dict[str, Any]) -> HandlerResult:
        logger.info("Received S7F17: Process Program Delete")
        recipe_service = context.get("recipe_service")
        ppids = _collect_ppids(_first_item(message))
        if not recipe_service:
            logger.warning("S7F17 denied: recipe_service not available")
            return HandlerResult(
                success=True,
                message="S7F17 denied: recipe_service not available",
                reply_items=[SECSItem.uint1(ACKC7_DENIED)],
            )

        deleted, missing = recipe_service.delete_recipes(ppids)
        ack = ACKC7_ACCEPTED if not missing else ACKC7_PPID_NOT_FOUND
        return HandlerResult(
            success=True,
            message=f"S7F17 handled, deleted={deleted}, missing={missing}",
            reply_items=[SECSItem.uint1(ack)],
            data={"deleted": deleted, "missing": missing, "ppids": ppids},
        )


class S7F19Handler(BaseMessageHandler):
    """S7F19 - Process Program List Request."""

    def __init__(self):
        super().__init__("S7F19Handler")

    def can_handle(self, message: SECSMessage) -> bool:
        return message.stream == 7 and message.function == 19

    async def handle(self, message: SECSMessage, context: Dict[str, Any]) -> HandlerResult:
        logger.info("Received S7F19: Process Program List Request")
        recipe_service = context.get("recipe_service")
        recipe_ids = recipe_service.list_recipe_ids() if recipe_service else []
        reply_list = SECSItem.list_([SECSItem.ascii(ppid) for ppid in recipe_ids])
        return HandlerResult(
            success=True,
            message=f"S7F19 handled, recipes={len(recipe_ids)}",
            reply_items=[reply_list],
            data={"recipe_ids": recipe_ids},
        )


class S7F25Handler(_BaseRecipeQueryHandler):
    """S7F25 - Formatted Process Program Request."""

    reply_sf = "S7F26"

    def __init__(self):
        super().__init__("S7F25Handler")

    def can_handle(self, message: SECSMessage) -> bool:
        return message.stream == 7 and message.function == 25

    async def handle(self, message: SECSMessage, context: Dict[str, Any]) -> HandlerResult:
        return await self._handle_query(message, context)


class S7HandlerManager(StreamHandlerManager):
    """S7 series handler manager."""

    def __init__(self):
        self._s7f1 = S7F1Handler()
        self._s7f3 = S7F3Handler()
        self._s7f5 = S7F5Handler()
        self._s7f17 = S7F17Handler()
        self._s7f19 = S7F19Handler()
        self._s7f25 = S7F25Handler()
        super().__init__(
            "S7HandlerManager",
            stream=7,
            handler_map={
                (7, 1): self._s7f1,
                (7, 3): self._s7f3,
                (7, 5): self._s7f5,
                (7, 17): self._s7f17,
                (7, 19): self._s7f19,
                (7, 25): self._s7f25,
            },
        )

