"""
APIITEML transaction codec (JSON payload).

Generated from:
- secs_eap/tx/CAPIITEML.h
- secs_eap/tx/CAPIITEML.cpp
"""

from dataclasses import dataclass, field
from typing import List

from .base import TxRequestMixin, TxResponseMixin

TX_NAME = "APIITEML"
REQUEST_QUEUE = "F01.APIITEMLI"
REPLY_QUEUE = "SHARE.REPLY"

@dataclass
class ApiitemloA1:
    data_id: str = ""
    use_tcs_label_flg: str = ""
    prt_label: str = ""
    chd_label: str = ""
    data_group: str = ""
    data_attr: str = ""
    data_cate: str = ""
    opi_data_flg: str = ""
    spec_check_flg: str = ""
    online_spc_flg: str = ""
    act_ope_id: str = ""
    data_type: str = ""
    do_l_spec_flg: str = ""
    do_u_spec_flg: str = ""
    l_spec: str = ""
    u_spec: str = ""
    data_value: str = ""
    mes_id: str = ""

@dataclass
class APIITEMLRequest(TxRequestMixin):
    trx_id: str = "APIITEML"
    type_id: str = "I"
    eqpt_id: str = ""
    rep_unit: str = ""
    data_pat: str = ""
    mes_id: str = ""
    dcop_online: str = ""
    orig_opi_flg: str = ""
    data_cate: str = ""

@dataclass
class APIITEMLResponse(TxResponseMixin):
    trx_id: str = "APIITEML"
    type_id: str = "O"
    rtn_code: str = ""
    rtn_mesg: str = ""
    mes_id: str = ""
    rep_unit: str = ""
    msr_glass_cnt: str = ""
    ary_cnt: str = ""
    oary: List[ApiitemloA1] = field(default_factory=list)
    raw_payload: str = ""

REQUEST_TYPE = APIITEMLRequest
RESPONSE_TYPE = APIITEMLResponse

__all__ = [
    "TX_NAME",
    "REQUEST_QUEUE",
    "REPLY_QUEUE",
    "REQUEST_TYPE",
    "RESPONSE_TYPE",
    "ApiitemloA1",
    "APIITEMLRequest",
    "APIITEMLResponse",
]
