"""
APIROUTE transaction codec (JSON payload).

Generated from:
- secs_eap/tx/CAPIROUTE.h
- secs_eap/tx/CAPIROUTE.cpp
"""

from dataclasses import dataclass, field
from typing import List

from .base import TxRequestMixin, TxResponseMixin

TX_NAME = "APIROUTE"
REQUEST_QUEUE = "F01.APIROUTEI"
REPLY_QUEUE = "SHARE.REPLY"

@dataclass
class ApirouteoA2:
    rwk_id: str = ""
    rwk_dsc: str = ""
    rwk_route_id: str = ""
    rwk_route_ver: str = ""
    rwk_out_ope_no: str = ""
    ctn_rwk_flg: str = ""
    ctn_rwk_route_id: str = ""
    ctn_rwk_route_ver: str = ""

@dataclass
class ApirouteoA4:
    brn_id: str = ""
    brn_dsc: str = ""
    brn_route_id: str = ""
    brn_route_ver: str = ""
    brn_out_ope_no: str = ""
    param_name: str = ""
    param_val: str = ""

@dataclass
class ApirouteoA5:
    pins_cate: str = ""
    pins_id: str = ""
    data_level: str = ""
    set_type: str = ""
    xfer_type: str = ""
    pins_expr: str = ""

@dataclass
class ApirouteoA6:
    test_seq: str = ""
    test_cate: str = ""
    test_expr: str = ""
    act_func: str = ""
    act_parm: str = ""

@dataclass
class ApirouteoA1:
    cr_ope_no: str = ""
    nx_ope_no: str = ""
    rwk_rst_flg: str = ""
    rwk_avl_flg: str = ""
    cr_ope_id: str = ""
    cr_ope_ver: str = ""
    addt_info_1: str = ""
    ope_dsc: str = ""
    proc_id: str = ""
    eqptg_id: str = ""
    pep_lvl: str = ""
    dept_code: str = ""
    std_ld_time: str = ""
    man_ope_time: str = ""
    up_load_id: str = ""
    down_load_id: str = ""
    crr_cln_flg: str = ""
    mproc_flg: str = ""
    mproc_id: str = ""
    stage_id: str = ""
    wip_bank_flg: str = ""
    def_wip_bank_id: str = ""
    shp_bank_flg: str = ""
    pfc_bank_id: str = ""
    rwk_cnt: str = ""
    oary2: List[ApirouteoA2] = field(default_factory=list)
    brn_cnt: str = ""
    oary4: List[ApirouteoA4] = field(default_factory=list)
    pins_cnt: str = ""
    oary5: List[ApirouteoA5] = field(default_factory=list)
    ifth_cnt: str = ""
    oary6: List[ApirouteoA6] = field(default_factory=list)

@dataclass
class APIROUTERequest(TxRequestMixin):
    trx_id: str = "APIROUTE"
    type_id: str = "I"
    user_info: str = ""
    route_id: str = ""
    route_ver: str = ""
    cr_ope_no: str = ""
    cr_ope_id: str = ""
    worder_id: str = ""

@dataclass
class APIROUTEResponse(TxResponseMixin):
    trx_id: str = "APIROUTE"
    type_id: str = "O"
    rtn_code: str = ""
    rtn_mesg: str = ""
    route_id: str = ""
    route_ver: str = ""
    route_dsc: str = ""
    route_cate: str = ""
    str_bank_id: str = ""
    end_bank_id: str = ""
    max_rwk_cnt: str = ""
    ope_cnt: str = ""
    addt_info_1: str = ""
    addt_info_2: str = ""
    addt_info_3: str = ""
    oary1: List[ApirouteoA1] = field(default_factory=list)
    raw_payload: str = ""

REQUEST_TYPE = APIROUTERequest
RESPONSE_TYPE = APIROUTEResponse

__all__ = [
    "TX_NAME",
    "REQUEST_QUEUE",
    "REPLY_QUEUE",
    "REQUEST_TYPE",
    "RESPONSE_TYPE",
    "ApirouteoA2",
    "ApirouteoA4",
    "ApirouteoA5",
    "ApirouteoA6",
    "ApirouteoA1",
    "APIROUTERequest",
    "APIROUTEResponse",
]
