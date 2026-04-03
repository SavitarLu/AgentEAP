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
REPLY_QUEUE = "F01.TCS.SHARE.T"

@dataclass
class RPLRPTCSOA1:
    recipe_id: str = ""
    recipe_cat: str = ""

@dataclass
class RPLRPTCSRequest(TxRequestMixin):
    trx_id: str = "RPLRPTCS"
    type_id: str = "I"
    eqpt_id: str = ""

@dataclass
class RPLRPTCSResponse(TxResponseMixin):
    trx_id: str = "RPLRPTCS"
    type_id: str = "O"
    rtn_code: str = ""
    rtn_mesg: str = ""
    eqpt_id: str = ""
    arycnt1: str = ""
    oary1: List[RPLRPTCSOA1] = field(default_factory=list)
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
