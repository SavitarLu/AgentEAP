"""
S2F41 remote command use case template.

This file is intentionally simple for EAP beginners:
1) Parse SECS message -> DTO
2) Execute business logic -> DTO
3) Build reply items from DTO
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from secs_driver.src.secs_message import SECSItem, SECSMessage
from secs_driver.src.secs_types import SECSType


@dataclass
class S2F41Request:
    rcmd: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    raw_items: List[SECSItem] = field(default_factory=list)


@dataclass
class S2F42Result:
    # HCACK (host command acknowledge), 0 means accepted.
    hcack: int = 0
    # Optional human-readable reason for logs.
    reason: str = ""


class S2F41RemoteCommandUseCase:
    """
    Beginner-friendly S2F41 implementation template.
    """

    def parse(self, message: SECSMessage) -> S2F41Request:
        request = S2F41Request(raw_items=list(message.items or []))
        if not message.items:
            return request

        root = message.items[0]
        if root.type != SECSType.LIST or not root.children:
            return request

        # Common S2F41 structure:
        # L[2]
        #   <A RCMD>
        #   <L[n] CPNAME/CPVAL ...>
        rcmd_item = root.children[0]
        if rcmd_item.type == SECSType.ASCII and rcmd_item.value:
            request.rcmd = str(rcmd_item.value).strip()

        if len(root.children) > 1:
            param_list = root.children[1]
            if param_list.type == SECSType.LIST:
                for cp in param_list.children:
                    if cp.type != SECSType.LIST or len(cp.children) < 2:
                        continue
                    name_item, value_item = cp.children[0], cp.children[1]
                    if name_item.type == SECSType.ASCII and name_item.value:
                        request.params[str(name_item.value).strip()] = value_item.value

        return request

    async def execute(self, request: S2F41Request, context: Dict[str, Any]) -> S2F42Result:
        equipment_service = context.get("equipment_service")
        if not equipment_service:
            return S2F42Result(hcack=2, reason="equipment_service not available")

        if not request.rcmd:
            return S2F42Result(hcack=3, reason="empty RCMD")

        # Reuse existing business interface to reduce learning cost.
        cmd = {"type": request.rcmd, "params": request.params}
        result = await equipment_service.execute_command(cmd)
        if result.get("success"):
            return S2F42Result(hcack=0, reason=result.get("message", "OK"))
        return S2F42Result(hcack=2, reason=result.get("message", "Command rejected"))

    def build_reply(self, result: S2F42Result) -> List[SECSItem]:
        # Minimal S2F42 reply: only HCACK.
        return [SECSItem.uint1(result.hcack)]

