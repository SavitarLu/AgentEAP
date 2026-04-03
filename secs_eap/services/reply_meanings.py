"""
Human-readable meanings for common SECS reply acknowledgment codes.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class ReplyAckSpec:
    field_name: str
    meanings: Dict[int, str] = field(default_factory=dict)
    default_meaning: str = "Unknown Ack Code."
    success_codes: Tuple[int, ...] = (0,)


def _register_reply_specs() -> Dict[str, ReplyAckSpec]:
    specs: Dict[str, ReplyAckSpec] = {}

    def add(
        reply_sfs,
        field_name: str,
        meanings: Dict[int, str],
        default_meaning: str = "Unknown Ack Code.",
        success_codes: Tuple[int, ...] = (0,),
    ) -> None:
        spec = ReplyAckSpec(
            field_name=field_name,
            meanings=dict(meanings),
            default_meaning=default_meaning,
            success_codes=tuple(success_codes or ()),
        )
        for reply_sf in reply_sfs:
            specs[str(reply_sf).upper()] = spec

    add(
        ["S1F14"],
        "COMMACK",
        {
            0: "Accepted.",
            1: "Denied, Try Again.",
        },
    )
    add(
        ["S1F18"],
        "ONLACK",
        {
            0: "ON-LINE Accepted.",
            1: "ON-LINE Not Allowed.",
            2: "Equipment Already ON-LINE.",
        },
        success_codes=(0, 2),
    )
    add(
        ["S2F16"],
        "EAC",
        {
            0: "Acknowledge.",
            1: "Denied. At least one constant does not exist.",
            2: "Denied. Busy.",
            3: "Denied. At least one constant out of range.",
        },
    )
    add(
        ["S2F32"],
        "TIACK",
        {
            0: "OK.",
            1: "Error, not done.",
        },
    )
    add(
        ["S2F34"],
        "DRACK",
        {
            0: "Accepted.",
            1: "Denied. Insufficient space.",
            2: "Denied. Invalid format.",
            3: "Denied. At least one RPTID already defined.",
            4: "Denied. At least one VID does not exist.",
        },
        default_meaning="Other error, not accepted.",
    )
    add(
        ["S2F36"],
        "LRACK",
        {
            0: "Accepted.",
            1: "Denied. Insufficient space.",
            2: "Denied. Invalid format.",
            3: "Denied. At least one CEID link already defined.",
            4: "Denied. At least one CEID does not exist.",
            5: "Denied. At least one RPTID does not exist.",
        },
        default_meaning="Other error, not accepted.",
    )
    add(
        ["S2F38"],
        "ERACK",
        {
            0: "Accepted.",
            1: "Denied. At least one CEID does not exist.",
        },
        default_meaning="Denied or not accepted.",
    )
    add(
        ["S2F42", "S2F50"],
        "HCACK",
        {
            0: "Acknowledge, command has been performed.",
            1: "Command does not exist.",
            2: "Cannot perform now.",
            3: "At least one parameter is invalid.",
            4: "Acknowledge, command will be performed with completion signaled later by an event.",
            5: "Rejected, already in desired condition.",
            6: "No such object exists.",
        },
        success_codes=(0, 4),
    )
    add(
        ["S2F44"],
        "RSPACK",
        {
            0: "Spooling setup accepted.",
            1: "Spooling setup rejected.",
        },
    )
    add(
        ["S2F46"],
        "VLAACK",
        {
            0: "Accepted.",
            1: "Variable does not exist.",
            2: "Variable has no limits capability.",
            3: "Variable repeated in message.",
            4: "Limit value error as described in LIMITACK.",
        },
    )
    add(
        ["S3F18", "S3F20", "S3F22", "S3F24", "S3F26", "S3F28", "S3F30", "S3F32"],
        "CAACK",
        {
            0: "Acknowledge, command has been performed.",
            1: "Invalid command.",
            2: "Can not perform now.",
            3: "Invalid data or argument.",
            4: "Acknowledge, request will be performed with completion signaled later by an event.",
            5: "Rejected. Invalid state.",
            6: "Command performed with errors.",
        },
        success_codes=(0, 4),
    )
    add(
        ["S5F4"],
        "ACKC5",
        {
            0: "Accepted.",
        },
    )
    add(
        ["S6F24"],
        "RSDA",
        {
            0: "Accepted.",
            1: "Denied, busy try again later.",
            2: "Denied, spooled data does not exist.",
        },
    )
    add(
        ["S16F12", "S16F16"],
        "ACKA",
        {
            1: "Accepted.",
            0: "Error.",
        },
        success_codes=(1,),
    )
    add(
        ["S14F2", "S14F4", "S14F6", "S14F8", "S14F10", "S14F12", "S14F14", "S14F16", "S14F18", "S14F26", "S14F28"],
        "OBJACK",
        {
            0: "Successful completion of requested data.",
            1: "Error.",
        },
    )

    return specs


REPLY_ACK_SPECS: Dict[str, ReplyAckSpec] = _register_reply_specs()


def get_reply_ack_spec(reply_sf: str) -> Optional[ReplyAckSpec]:
    """Return reply ack metadata for one SxFy reply."""
    return REPLY_ACK_SPECS.get(str(reply_sf or "").upper())


def get_reply_ack_label(reply_sf: str) -> str:
    """Return the ack field label, for example DRACK/LRACK/HCACK."""
    spec = get_reply_ack_spec(reply_sf)
    return spec.field_name if spec else "ACK"


def get_reply_ack_meaning(reply_sf: str, ack_code: Optional[int]) -> str:
    """Return a human-readable explanation for one reply ack code."""
    if ack_code is None:
        return "No ack code available."

    spec = get_reply_ack_spec(reply_sf)
    if not spec:
        return f"Unknown ack code: {ack_code}"

    return spec.meanings.get(ack_code, spec.default_meaning)


def is_reply_ack_accepted(reply_sf: str, ack_code: Optional[int]) -> bool:
    """Return whether one reply ack code should be treated as success."""
    if ack_code is None:
        return False

    spec = get_reply_ack_spec(reply_sf)
    if not spec:
        return ack_code == 0
    return ack_code in set(spec.success_codes)


def format_reply_ack(reply_sf: str, ack_code: Optional[int]) -> str:
    """Format one ack code as FIELD=value meaning."""
    label = get_reply_ack_label(reply_sf)
    meaning = get_reply_ack_meaning(reply_sf, ack_code)
    if ack_code is None:
        return f"{label}=None {meaning}"
    return f"{label}={ack_code} {meaning}"
