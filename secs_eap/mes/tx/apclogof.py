"""
APCLOGOF transaction codec (JSON payload).

Generated from:
- secs_eap/tx/CAPCLOGOF.h
- secs_eap/tx/CAPCLOGOF.cpp
"""

from dataclasses import dataclass, field
from typing import List

from .base import TxRequestMixin, TxResponseMixin

TX_NAME = "APCLOGOF"
REQUEST_QUEUE = "F01.APCLOGOFI"
REPLY_QUEUE = "SHARE.REPLY"

@dataclass
class ApclogofiA:
    sht_id: str = ""
    slot_no: str = ""

@dataclass
class APCLOGOFRequest(TxRequestMixin):
    trx_id: str = "APCLOGOF"
    type_id: str = "I"
    user_info: str = ""
    orig_opi_flg: str = ""
    crr_id: str = ""
    eqpt_id: str = ""
    port_id: str = ""
    user_id: str = ""
    lot_hld_flg: str = ""
    hld_rsn_cate: str = ""
    hld_rsn_code: str = ""
    dept_code: str = ""
    sht_ope_msg: str = ""
    rwk_id: str = ""
    ce_id: str = ""
    pfc_flg: str = ""
    sht_judge: str = ""
    unit: str = ""
    hld_rsn_cnt: str = ""
    iary: List[ApclogofiA] = field(default_factory=list)

@dataclass
class APCLOGOFResponse(TxResponseMixin):
    trx_id: str = "APCLOGOF"
    type_id: str = "O"
    rtn_code: str = ""
    rtn_mesg: str = ""
    crr_id: str = ""
    eqpt_id: str = ""
    user_id: str = ""
    raw_payload: str = ""

REQUEST_TYPE = APCLOGOFRequest
RESPONSE_TYPE = APCLOGOFResponse

__all__ = [
    "TX_NAME",
    "REQUEST_QUEUE",
    "REPLY_QUEUE",
    "REQUEST_TYPE",
    "RESPONSE_TYPE",
    "ApclogofiA",
    "APCLOGOFRequest",
    "APCLOGOFResponse",
]
