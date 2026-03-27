"""
RPLRPTCS transaction codec (JSON payload).

Generated from:
- secs_eap/tx/CRPLRPTCS.h
- secs_eap/tx/CRPLRPTCS.cpp
"""

from dataclasses import dataclass, field
from typing import List

from .base import TxRequestMixin, TxResponseMixin

TX_NAME = "RPLRPTCS"
REQUEST_QUEUE = "F01.TCS.SHARE"
REPLY_QUEUE = "SHARE.REPLY"

@dataclass
class RPLRPTCSOA1:
    rcp_id: str = ""
    rcp_cat: str = ""

@dataclass
class RPLRPTCSRequest(TxRequestMixin):
    trx_id: str = "RPLRPTCS"
    type_id: str = "I"
    eqp_id: str = ""

@dataclass
class RPLRPTCSResponse(TxResponseMixin):
    trx_id: str = "RPLRPTCS"
    type_id: str = "O"
    retcode1: str = ""
    sqlcode: str = ""
    eqp_id: str = ""
    arycnt1: str = ""
    a1: List[RPLRPTCSOA1] = field(default_factory=list)
    raw_payload: str = ""

REQUEST_TYPE = RPLRPTCSRequest
RESPONSE_TYPE = RPLRPTCSResponse

__all__ = [
    "TX_NAME",
    "REQUEST_QUEUE",
    "REPLY_QUEUE",
    "REQUEST_TYPE",
    "RESPONSE_TYPE",
    "RPLRPTCSOA1",
    "RPLRPTCSRequest",
    "RPLRPTCSResponse",
]
