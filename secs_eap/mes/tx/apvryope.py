"""
APVRYOPE transaction codec (JSON payload).

Generated from:
- apvryope.h
- xlglen.h
"""

from dataclasses import dataclass, field
from typing import List

from .base import TxRequestMixin, TxResponseMixin

TX_NAME = "APVRYOPE"
REQUEST_QUEUE = "F01.APVRYOPEI"
REPLY_QUEUE = "SHARE.REPLY"


@dataclass
class ApvryopeoA2:
    xy_dim: str = ""
    sub_sht_id: str = ""


@dataclass
class ApvryopeoA1:
    slot_no: str = ""
    sht_id: str = ""
    product_id: str = ""
    sgr_id: str = ""
    vry_ope_proc_flg: str = ""
    proc_panel: str = ""
    rwk_cnt: str = ""
    test_rslt: str = ""
    mtrl_grade: str = ""
    stb_shop: str = ""
    pnl_sht_cnt: str = ""
    sub_sht_cnt: str = ""
    oary2: List[ApvryopeoA2] = field(default_factory=list)


@dataclass
class APVRYOPERequest(TxRequestMixin):
    trx_id: str = "APVRYOPE"
    type_id: str = "I"
    user_info: str = ""
    eqpt_id: str = ""
    port_id: str = ""
    crr_id: str = ""
    user_id: str = ""


@dataclass
class APVRYOPEResponse(TxResponseMixin):
    trx_id: str = "APVRYOPE"
    type_id: str = "O"
    rtn_code: str = ""
    rtn_mesg: str = ""
    eqpt_id: str = ""
    port_id: str = ""
    crr_id: str = ""
    user_id: str = ""
    lot_id: str = ""
    splt_id: str = ""
    product_cate: str = ""
    product_id: str = ""
    ec_code: str = ""
    nx_route_id: str = ""
    nx_route_ver: str = ""
    nx_proc_id: str = ""
    nx_ope_no: str = ""
    nx_ope_ver: str = ""
    nx_ope_dsc: str = ""
    nx_ope_id: str = ""
    nx_pep_lvl: str = ""
    prty: str = ""
    sht_cnt: str = ""
    pnl_cnt: str = ""
    recipe_id: str = ""
    recipe_ver: str = ""
    mes_id: str = ""
    up_load_id: str = ""
    down_load_id: str = ""
    up_eqpt_id: str = ""
    up_recipe_id: str = ""
    qrs_route_id: str = ""
    qrs_route_ver: str = ""
    qrs_ope_id: str = ""
    qrs_ope_no: str = ""
    qrs_date: str = ""
    qrs_time: str = ""
    rwk_cnt: str = ""
    max_rwk_cnt: str = ""
    ppbody: str = ""
    spc_check_flg: str = ""
    spec_check_flg: str = ""
    logof_eqpt_id: str = ""
    logof_port_id: str = ""
    logof_recipe_id: str = ""
    pfc_bank_id: str = ""
    sgr_id: str = ""
    owner_id: str = ""
    test_rep_typ: str = ""
    use_pfc_flg: str = ""
    stb_shop: str = ""
    mtrl_product_id: str = ""
    max_sht_cnt: str = ""
    ary_sht_cnt: str = ""
    oary1: List[ApvryopeoA1] = field(default_factory=list)
    raw_payload: str = ""


REQUEST_TYPE = APVRYOPERequest
RESPONSE_TYPE = APVRYOPEResponse

__all__ = [
    "TX_NAME",
    "REQUEST_QUEUE",
    "REPLY_QUEUE",
    "REQUEST_TYPE",
    "RESPONSE_TYPE",
    "ApvryopeoA2",
    "ApvryopeoA1",
    "APVRYOPERequest",
    "APVRYOPEResponse",
]
