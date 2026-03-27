"""
APCETLON transaction codec (JSON payload).

Generated from:
- secs_eap/tx/CAPCETLON.h
- secs_eap/tx/CAPCETLON.cpp
"""

from dataclasses import dataclass, field
from typing import List

from .base import TxRequestMixin, TxResponseMixin

TX_NAME = "APCETLON"
REQUEST_QUEUE = "F01.APCETLONI"
REPLY_QUEUE = "SHARE.REPLY"

@dataclass
class ApcetloniA:
    seq_no: str = ""
    instruct: str = ""
    cfm_user: str = ""
    cfm_flag: str = ""
    cfm_comment: str = ""

@dataclass
class APCETLONRequest(TxRequestMixin):
    trx_id: str = "APCETLON"
    type_id: str = "I"
    user_info: str = ""
    layer_code: str = ""
    orig_opi_flg: str = ""
    crr_id: str = ""
    eqpt_id: str = ""
    port_id: str = ""
    user_id: str = ""
    clm_date: str = ""
    clm_time: str = ""
    ds_recipe_id: str = ""
    ac_recipe_id: str = ""
    force_lgn_flg: str = ""
    plant: str = ""
    dept_code: str = ""
    sht_ope_msg: str = ""
    rsp_worder_id: str = ""
    logon_sht_cnt: str = ""
    inst_cnt: str = ""
    batch_flg: str = ""
    batch_sub_worder_id: str = ""
    lot_id: str = ""
    iary: List[ApcetloniA] = field(default_factory=list)

@dataclass
class APCETLONResponse(TxResponseMixin):
    trx_id: str = "APCETLON"
    type_id: str = "O"
    rtn_code: str = ""
    rtn_mesg: str = ""
    crr_id: str = ""
    eqpt_id: str = ""
    port_id: str = ""
    raw_payload: str = ""

REQUEST_TYPE = APCETLONRequest
RESPONSE_TYPE = APCETLONResponse

__all__ = [
    "TX_NAME",
    "REQUEST_QUEUE",
    "REPLY_QUEUE",
    "REQUEST_TYPE",
    "RESPONSE_TYPE",
    "ApcetloniA",
    "APCETLONRequest",
    "APCETLONResponse",
]
