"""
APCMSRDT transaction codec (JSON payload).

Generated from:
- secs_eap/tx/CAPCMSRDT.h
- secs_eap/tx/CAPCMSRDT.cpp
"""

from dataclasses import dataclass, field
from typing import List

from .base import TxRequestMixin, TxResponseMixin

TX_NAME = "APCMSRDT"
REQUEST_QUEUE = "F01.APCMSRDTI"
REPLY_QUEUE = "SHARE.REPLY"

@dataclass
class ApcmsrdtiA:
    data_id: str = ""
    tcs_label: str = ""
    data_group: str = ""
    data_type: str = ""
    data_value: str = ""

@dataclass
class APCMSRDTRequest(TxRequestMixin):
    trx_id: str = "APCMSRDT"
    type_id: str = "I"
    orig_opi_flg: str = ""
    eqpt_id: str = ""
    eqpt_unit_id: str = ""
    rep_unit: str = ""
    data_pat: str = ""
    mes_id: str = ""
    sht_id: str = ""
    slot_no: str = ""
    lot_id: str = ""
    splt_id: str = ""
    crr_id: str = ""
    product_id: str = ""
    ec_code: str = ""
    route_id: str = ""
    route_ver: str = ""
    ope_id: str = ""
    ope_ver: str = ""
    ope_no: str = ""
    rpt_user: str = ""
    ds_recipe_id: str = ""
    ac_recipe_id: str = ""
    ce_id: str = ""
    dcop_online: str = ""
    data_cnt: str = ""
    iary: List[ApcmsrdtiA] = field(default_factory=list)

@dataclass
class APCMSRDTResponse(TxResponseMixin):
    trx_id: str = "APCMSRDT"
    type_id: str = "O"
    rtn_code: str = ""
    rtn_mesg: str = ""
    spec_result: str = ""
    hold_flg: str = ""
    alrm_flg: str = ""
    raw_payload: str = ""

REQUEST_TYPE = APCMSRDTRequest
RESPONSE_TYPE = APCMSRDTResponse

__all__ = [
    "TX_NAME",
    "REQUEST_QUEUE",
    "REPLY_QUEUE",
    "REQUEST_TYPE",
    "RESPONSE_TYPE",
    "ApcmsrdtiA",
    "APCMSRDTRequest",
    "APCMSRDTResponse",
]
