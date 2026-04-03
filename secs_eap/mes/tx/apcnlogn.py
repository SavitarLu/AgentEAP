"""
APCNLOGN transaction codec (JSON payload).

Generated from:
- secs_eap/tx/CAPCNLOGN.h
- secs_eap/tx/CAPCNLOGN.cpp
"""

from dataclasses import dataclass, field
from typing import List

from .base import TxRequestMixin, TxResponseMixin

TX_NAME = "APCNLOGN"
REQUEST_QUEUE = "F01.APCNLOGNI"
REPLY_QUEUE = "SHARE.REPLY"

@dataclass
class ApcnlogniA:
    sht_id: str = ""
    slot_no: str = ""

@dataclass
class APCNLOGNRequest(TxRequestMixin):
    trx_id: str = "APCNLOGN"
    type_id: str = "I"
    user_info: str = ""
    crr_id: str = ""
    eqpt_id: str = ""
    dept_code: str = ""
    sht_ope_msg: str = ""
    user_id: str = ""
    sht_cnt: str = ""
    iary: List[ApcnlogniA] = field(default_factory=list)

@dataclass
class APCNLOGNResponse(TxResponseMixin):
    trx_id: str = "APCNLOGN"
    type_id: str = "O"
    rtn_code: str = ""
    rtn_mesg: str = ""
    raw_payload: str = ""

REQUEST_TYPE = APCNLOGNRequest
RESPONSE_TYPE = APCNLOGNResponse

__all__ = [
    "TX_NAME",
    "REQUEST_QUEUE",
    "REPLY_QUEUE",
    "REQUEST_TYPE",
    "RESPONSE_TYPE",
    "ApcnlogniA",
    "APCNLOGNRequest",
    "APCNLOGNResponse",
]
