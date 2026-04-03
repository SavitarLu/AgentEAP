"""
APCEQPST transaction codec (JSON payload).

Generated from:
- secs_eap/tx/CAPCEQPST.h
- secs_eap/tx/CAPCEQPST.cpp
"""

from dataclasses import dataclass, field
from typing import List

from .base import TxRequestMixin, TxResponseMixin

TX_NAME = "APCEQPST"
REQUEST_QUEUE = "F01.APCEQPSTI"
REPLY_QUEUE = "SHARE.REPLY"

@dataclass
class CpceqpstoA:
    port_id: str = ""
    port_typ: str = ""

@dataclass
class APCEQPSTRequest(TxRequestMixin):
    trx_id: str = "APCEQPST"
    type_id: str = "I"
    user_info: str = ""
    clm_eqst_typ: str = "A"
    orig_opi_flg: str = "N"
    clm_date: str = ""
    clm_time: str = ""
    clm_time_ms6f: str = ""
    user_id: str = "AGT"
    eqpt_id: str = ""
    eqpt_mode: str = ""
    eqpt_stat: str = ""
    eqpt_sub_stat: str = ""
    port_id: str = ""
    port_stat: str = ""
    reason_code: str = ""
    recipe_id: str = ""
    crr_accept_flg: str = ""
    comment: str = ""
    vcr_stat: str = ""
    eqpt_run_mode: str = ""
    eng_sht_id: str = ""

@dataclass
class APCEQPSTResponse(TxResponseMixin):
    trx_id: str = "APCEQPST"
    type_id: str = "O"
    rtn_code: str = ""
    rtn_mesg: str = ""
    eqpt_id: str = ""
    eqpt_run_mode: str = ""
    eqpt_cate: str = ""
    port_cnt: str = ""
    oary: List[CpceqpstoA] = field(default_factory=list)
    raw_payload: str = ""

REQUEST_TYPE = APCEQPSTRequest
RESPONSE_TYPE = APCEQPSTResponse

__all__ = [
    "TX_NAME",
    "REQUEST_QUEUE",
    "REPLY_QUEUE",
    "REQUEST_TYPE",
    "RESPONSE_TYPE",
    "CpceqpstoA",
    "APCEQPSTRequest",
    "APCEQPSTResponse",
]
