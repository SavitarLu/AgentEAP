"""
APMLTTYP transaction codec (JSON payload).

Generated from:
- secs_eap/tx/CAPMLTTYP.h
- secs_eap/tx/CAPMLTTYP.cpp
"""

from dataclasses import dataclass, field
from typing import List

from .base import TxRequestMixin, TxResponseMixin

TX_NAME = "APMLTTYP"
REQUEST_QUEUE = "F01.APMLTTYPI"
REPLY_QUEUE = "SHARE.REPLY"

@dataclass
class ApmlttypiA1:
    lot_id: str = ""
    splt_id: str = ""
    crr_id: str = ""

@dataclass
class APMLTTYPRequest(TxRequestMixin):
    trx_id: str = "APMLTTYP"
    type_id: str = "I"
    user_info: str = ""
    act_type: str = ""
    lot_type: str = ""
    clm_user: str = ""
    comment: str = ""
    lot_cnt: str = ""
    iary1: List[ApmlttypiA1] = field(default_factory=list)

@dataclass
class APMLTTYPResponse(TxResponseMixin):
    trx_id: str = "APMLTTYP"
    type_id: str = "O"
    rtn_code: str = ""
    rtn_mesg: str = ""
    raw_payload: str = ""

REQUEST_TYPE = APMLTTYPRequest
RESPONSE_TYPE = APMLTTYPResponse

__all__ = [
    "TX_NAME",
    "REQUEST_QUEUE",
    "REPLY_QUEUE",
    "REQUEST_TYPE",
    "RESPONSE_TYPE",
    "ApmlttypiA1",
    "APMLTTYPRequest",
    "APMLTTYPResponse",
]
