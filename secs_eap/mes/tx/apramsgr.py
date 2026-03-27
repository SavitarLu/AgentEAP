"""
APRAMSGR transaction codec (JSON payload).

Generated from:
- secs_eap/tx/CAPRAMSGR.h
- secs_eap/tx/CAPRAMSGR.cpp
"""

from dataclasses import dataclass, field
from typing import List

from .base import TxRequestMixin, TxResponseMixin

TX_NAME = "APRAMSGR"
REQUEST_QUEUE = "F01.APRAMSGRI"
REPLY_QUEUE = "SHARE.REPLY"

@dataclass
class ApramsgriSpchld:
    cname: str = ""
    gname: str = ""
    ope_no: str = ""
    eqpt_id: str = ""
    recipe_id: str = ""
    m_eqpt_id: str = ""
    m_recipe_id: str = ""
    sht_id: str = ""
    point_value: str = ""

@dataclass
class ApramsgriSpcalm:
    cname: str = ""
    gname: str = ""
    ope_no: str = ""
    eqpt_id: str = ""
    recipe_id: str = ""
    m_eqpt_id: str = ""
    m_recipe_id: str = ""
    sht_id: str = ""
    point_value: str = ""

@dataclass
class ApramsgriEqpalr:
    eqpt_id: str = ""
    rpt_date: str = ""
    rpt_time: str = ""
    rpt_source: str = ""
    alrt_id: str = ""
    alrt_code: str = ""
    alrt_lvl: str = ""
    alrt_dsc: str = ""
    alrt_comment: str = ""

@dataclass
class ApramsgriEqpalm:
    eqpt_id: str = ""
    eqpt_stat: str = ""
    eqpt_sub_stat: str = ""
    eqpt_mode: str = ""
    port_id: str = ""
    port_stat: str = ""
    clm_user: str = ""
    clm_date: str = ""
    clm_time: str = ""

@dataclass
class ApramsgriEqptcs:
    eqpt_id: str = ""
    sht_id: str = ""
    crr_id: str = ""
    product_id: str = ""
    ec_code: str = ""
    route_id: str = ""
    proc_id: str = ""
    ope_no: str = ""
    ope_id: str = ""

@dataclass
class ApramsgriPmsalm:
    eqpt_id: str = ""
    rpt_date: str = ""
    rpt_time: str = ""
    pm_id: str = ""
    pm_type: str = ""
    event_source: str = ""
    event_type: str = ""
    reasoncode: str = ""
    pm_planner: str = ""
    pm_owner: str = ""

@dataclass
class ApramsgriPmsrca:
    eqpt_id: str = ""
    alm_case: str = ""
    alm_module: str = ""
    alm_type: str = ""
    alm_time: str = ""
    alm_msg: str = ""

@dataclass
class ApramsgriStkalm:
    stocker_id: str = ""
    pati_id: str = ""
    pati_max_cnt: str = ""
    pati_used_cnt: str = ""
    clm_user: str = ""
    clm_date: str = ""
    clm_time: str = ""

@dataclass
class ApramsgriMtralm:
    ope_id: str = ""
    mtrl_product_id: str = ""
    mtrl_sub_type: str = ""
    clm_user: str = ""
    clm_date: str = ""
    clm_time: str = ""

@dataclass
class ApramsgriOthers:
    p_name1: str = ""
    p_value1: str = ""
    p_name2: str = ""
    p_value2: str = ""
    p_name3: str = ""
    p_value3: str = ""
    p_name4: str = ""
    p_value4: str = ""
    p_name5: str = ""
    p_value5: str = ""
    p_name6: str = ""
    p_value6: str = ""
    p_name7: str = ""
    p_value7: str = ""
    p_name8: str = ""
    p_value8: str = ""
    p_name9: str = ""
    p_value9: str = ""
    p_name10: str = ""
    p_value10: str = ""

@dataclass
class APRAMSGRRequest(TxRequestMixin):
    trx_id: str = "APRAMSGR"
    type_id: str = "I"
    user_info: str = ""
    clm_source: str = ""
    clm_cate: str = ""
    message: str = ""
    spchld: ApramsgriSpchld = field(default_factory=ApramsgriSpchld)
    spcalm: ApramsgriSpcalm = field(default_factory=ApramsgriSpcalm)
    eqpalr: ApramsgriEqpalr = field(default_factory=ApramsgriEqpalr)
    eqpalm: ApramsgriEqpalm = field(default_factory=ApramsgriEqpalm)
    eqptcs: ApramsgriEqptcs = field(default_factory=ApramsgriEqptcs)
    pmsalm: ApramsgriPmsalm = field(default_factory=ApramsgriPmsalm)
    pmsrca: ApramsgriPmsrca = field(default_factory=ApramsgriPmsrca)
    stkalm: ApramsgriStkalm = field(default_factory=ApramsgriStkalm)
    mtralm: ApramsgriMtralm = field(default_factory=ApramsgriMtralm)
    others: ApramsgriOthers = field(default_factory=ApramsgriOthers)

@dataclass
class APRAMSGRResponse(TxResponseMixin):
    trx_id: str = "APRAMSGR"
    type_id: str = "O"
    rtn_code: str = ""
    rtn_mesg: str = ""
    raw_payload: str = ""

REQUEST_TYPE = APRAMSGRRequest
RESPONSE_TYPE = APRAMSGRResponse

__all__ = [
    "TX_NAME",
    "REQUEST_QUEUE",
    "REPLY_QUEUE",
    "REQUEST_TYPE",
    "RESPONSE_TYPE",
    "ApramsgriSpchld",
    "ApramsgriSpcalm",
    "ApramsgriEqpalr",
    "ApramsgriEqpalm",
    "ApramsgriEqptcs",
    "ApramsgriPmsalm",
    "ApramsgriPmsrca",
    "ApramsgriStkalm",
    "ApramsgriMtralm",
    "ApramsgriOthers",
    "APRAMSGRRequest",
    "APRAMSGRResponse",
]
