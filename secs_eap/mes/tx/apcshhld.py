"""
APCSHHLD transaction codec (JSON payload).

Generated from:
- secs_eap/tx/CAPCSHHLD.h
- secs_eap/tx/CAPCSHHLD.cpp
"""

from dataclasses import dataclass, field
from typing import List

from .base import TxRequestMixin, TxResponseMixin

TX_NAME = "APCSHHLD"
REQUEST_QUEUE = "F01.APCSHHLDI"
REPLY_QUEUE = "SHARE.REPLY"

@dataclass
class ApcshhldiA:
    hld_rsn_cate: str = ""
    hld_rsn_code: str = ""
    dept_code: str = ""

@dataclass
class APCSHHLDRequest(TxRequestMixin):
    trx_id: str = "APCSHHLD"
    type_id: str = "I"
    act_typ: str = ""
    sht_id: str = ""
    crr_id: str = ""
    eqpt_id: str = ""
    user_id: str = ""
    dept_code: str = ""
    pln_rel_date: str = ""
    sht_ope_msg: str = ""
    hld_rsn_cnt: str = ""
    iary: List[ApcshhldiA] = field(default_factory=list)

@dataclass
class APCSHHLDResponse(TxResponseMixin):
    trx_id: str = "APCSHHLD"
    type_id: str = "O"
    rtn_code: str = ""
    rtn_mesg: str = ""
    raw_payload: str = ""

REQUEST_TYPE = APCSHHLDRequest
RESPONSE_TYPE = APCSHHLDResponse

__all__ = [
    "TX_NAME",
    "REQUEST_QUEUE",
    "REPLY_QUEUE",
    "REQUEST_TYPE",
    "RESPONSE_TYPE",
    "ApcshhldiA",
    "APCSHHLDRequest",
    "APCSHHLDResponse",
]
