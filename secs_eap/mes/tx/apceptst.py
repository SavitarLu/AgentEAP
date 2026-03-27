"""
APCEPTST transaction codec (JSON payload).

Generated from:
- secs_eap/tx/CAPCEPTST.h
- secs_eap/tx/CAPCEPTST.cpp
"""

from dataclasses import dataclass, field
from typing import List

from .base import TxRequestMixin, TxResponseMixin

TX_NAME = "APCEPTST"
REQUEST_QUEUE = "F01.APCEPTSTI"
REPLY_QUEUE = "SHARE.REPLY"

@dataclass
class APCEPTSTRequest(TxRequestMixin):
    trx_id: str = "APCEPTST"
    type_id: str = "I"
    user_info: str = ""
    clm_date: str = ""
    clm_time: str = ""
    user_id: str = ""
    eqpt_id: str = ""
    port_id: str = ""
    port_stat: str = ""
    crr_id: str = ""
    port_enable_flg: str = ""
    abnormal_flg: str = ""
    pfc_bank_id: str = ""
    rpt_sht_id: str = ""
    sht_judge: str = ""
    pair_flg: str = ""
    pair_port_id: str = ""
    port_typ: str = ""
    rpt_ppbox_id: str = ""
    rpt_mtrl_grade: str = ""
    ng_type: str = ""
    tcs_node: str = ""

@dataclass
class APCEPTSTResponse(TxResponseMixin):
    trx_id: str = "APCEPTST"
    type_id: str = "O"
    rtn_code: str = ""
    rtn_mesg: str = ""
    eqpt_id: str = ""
    port_id: str = ""
    port_stat: str = ""
    crr_id: str = ""
    port_enable_flg: str = ""
    reset_time: str = ""
    to_gateway: str = ""
    raw_payload: str = ""

REQUEST_TYPE = APCEPTSTRequest
RESPONSE_TYPE = APCEPTSTResponse

__all__ = [
    "TX_NAME",
    "REQUEST_QUEUE",
    "REPLY_QUEUE",
    "REQUEST_TYPE",
    "RESPONSE_TYPE",
    "APCEPTSTRequest",
    "APCEPTSTResponse",
]
