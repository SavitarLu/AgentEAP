"""
RPIRBTCS transaction codec (JSON payload).

Generated from:
- secs_eap/tx/CRPIRBTCS.h
- secs_eap/tx/CRPIRBTCS.cpp
"""

from dataclasses import dataclass, field
from typing import List

from .base import TxRequestMixin, TxResponseMixin

TX_NAME = "RPIRBTCS"
REQUEST_QUEUE = "F01.RPIRBTCSI"
REPLY_QUEUE = "SHARE.REPLY"

@dataclass
class RPIRBTCSRequest(TxRequestMixin):
    trx_id: str = "RPIRBTCS"
    type_id: str = "I"
    eqp_id: str = ""
    rcp_id: str = ""
    rcp_body: str = ""
    opi_flg: str = ""
    car_id: str = ""
    sublot_id: str = ""

@dataclass
class RPIRBTCSResponse(TxResponseMixin):
    trx_id: str = "RPIRBTCS"
    type_id: str = "O"
    retcode1: str = ""
    sqlcode: str = ""
    audit_ret: str = ""
    raw_payload: str = ""

REQUEST_TYPE = RPIRBTCSRequest
RESPONSE_TYPE = RPIRBTCSResponse

__all__ = [
    "TX_NAME",
    "REQUEST_QUEUE",
    "REPLY_QUEUE",
    "REQUEST_TYPE",
    "RESPONSE_TYPE",
    "RPIRBTCSRequest",
    "RPIRBTCSResponse",
]
