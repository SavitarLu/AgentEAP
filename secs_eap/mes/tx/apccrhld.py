"""
APCCRHLD transaction codec (JSON payload).

Generated from:
- secs_eap/tx/CAPCCRHLD.h
- secs_eap/tx/CAPCCRHLD.cpp
"""

from dataclasses import dataclass, field
from typing import List

from .base import TxRequestMixin, TxResponseMixin

TX_NAME = "APCCRHLD"
REQUEST_QUEUE = "F01.APCCRHLDI"
REPLY_QUEUE = "SHARE.REPLY"

@dataclass
class ApccrhldiA:
    hld_rsn_cate: str = ""
    hld_rsn_code: str = ""
    dept_code: str = ""

@dataclass
class APCCRHLDRequest(TxRequestMixin):
    trx_id: str = "APCCRHLD"
    type_id: str = "I"
    user_info: str = ""
    inpr_sht_flg: str = ""
    crr_id: str = ""
    lot_id: str = ""
    splt_id: str = ""
    pln_rel_date: str = ""
    user_id: str = ""
    dept_code: str = ""
    sht_ope_msg: str = ""
    hld_note: str = ""
    hld_rsn_cnt: str = ""
    iary: List[ApccrhldiA] = field(default_factory=list)

@dataclass
class APCCRHLDResponse(TxResponseMixin):
    trx_id: str = "APCCRHLD"
    type_id: str = "O"
    rtn_code: str = ""
    rtn_mesg: str = ""
    raw_payload: str = ""

REQUEST_TYPE = APCCRHLDRequest
RESPONSE_TYPE = APCCRHLDResponse

__all__ = [
    "TX_NAME",
    "REQUEST_QUEUE",
    "REPLY_QUEUE",
    "REQUEST_TYPE",
    "RESPONSE_TYPE",
    "ApccrhldiA",
    "APCCRHLDRequest",
    "APCCRHLDResponse",
]
