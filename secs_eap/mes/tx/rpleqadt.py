"""
RPLEQADT transaction codec (JSON payload).

Generated from:
- secs_eap/tx/CRPLEQADT.h
- secs_eap/tx/CRPLEQADT.cpp
"""

from dataclasses import dataclass, field
from typing import List

from .base import TxRequestMixin, TxResponseMixin

TX_NAME = "RPLEQADT"
REQUEST_QUEUE = "F01.RPLEQADTI"
REPLY_QUEUE = "SHARE.REPLY"

@dataclass
class RpleqadtoA1:
    eqpt_id: str = ""
    recipe_id: str = ""
    eqpt_dsc: str = ""
    root_eqpt_id: str = ""
    audit_flag: str = ""

@dataclass
class RPLEQADTRequest(TxRequestMixin):
    trx_id: str = "RPLEQADT"
    type_id: str = "I"
    user_info: str = ""
    eqpt_id: str = ""
    audit_flag: str = ""

@dataclass
class RPLEQADTResponse(TxResponseMixin):
    trx_id: str = "RPLEQADT"
    type_id: str = "O"
    rtn_code: str = ""
    rtn_mesg: str = ""
    eqpt_cnt: str = ""
    oary1: List[RpleqadtoA1] = field(default_factory=list)
    raw_payload: str = ""

REQUEST_TYPE = RPLEQADTRequest
RESPONSE_TYPE = RPLEQADTResponse

__all__ = [
    "TX_NAME",
    "REQUEST_QUEUE",
    "REPLY_QUEUE",
    "REQUEST_TYPE",
    "RESPONSE_TYPE",
    "RpleqadtoA1",
    "RPLEQADTRequest",
    "RPLEQADTResponse",
]
