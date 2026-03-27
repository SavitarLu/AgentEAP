"""
APMLTFAC transaction codec (JSON payload).

Generated from:
- secs_eap/tx/CAPMLTFAC.h
- secs_eap/tx/CAPMLTFAC.cpp
"""

from dataclasses import dataclass, field
from typing import List

from .base import TxRequestMixin, TxResponseMixin

TX_NAME = "APMLTFAC"
REQUEST_QUEUE = "F01.APMLTFACI"
REPLY_QUEUE = "SHARE.REPLY"

@dataclass
class ApmltfaciA:
    lot_id: str = ""
    splt_id: str = ""
    product_id: str = ""
    route_id: str = ""
    route_ver: str = ""

@dataclass
class APMLTFACRequest(TxRequestMixin):
    trx_id: str = "APMLTFAC"
    type_id: str = "I"
    user_info: str = ""
    tbl_act_flg: str = ""
    user_id: str = ""
    template_id: str = ""
    lot_id: str = ""
    splt_id: str = ""
    sgr_id: str = ""
    sht_id: str = ""
    sht_judge: str = ""
    product_id: str = ""
    route_id: str = ""
    route_ver: str = ""
    ftact_time: str = ""
    ope_id: str = ""
    ope_no: str = ""
    ope_ver: str = ""
    ftact_act_code: str = ""
    seq_no: str = ""
    rwk_id: str = ""
    rwk_route_id: str = ""
    rwk_route_ver: str = ""
    rwk_out_ope_no: str = ""
    rsn_code: str = ""
    hld_dept_code: str = ""
    pln_rel_date: str = ""
    smp_route_id: str = ""
    smp_route_ver: str = ""
    smp_ope_no: str = ""
    recipe_id: str = ""
    eqptg_id: str = ""
    eqpt_id: str = ""
    dept_code: str = ""
    sht_ope_msg: str = ""
    aff_cnt: str = ""
    een_id: str = ""
    pair_splt_id: str = ""
    dst_sgr_id: str = ""
    dst_product_id: str = ""
    dst_ec_code: str = ""
    dst_route_id: str = ""
    dst_route_ver: str = ""
    dst_ope_no: str = ""
    proc_id: str = ""
    dst_proc_id: str = ""
    dst_bank_id: str = ""
    abnormal_flg: str = ""
    cp_product_id: str = ""
    cp_route_id: str = ""
    cp_route_ver: str = ""
    lot_cnt: str = ""
    iary: List[ApmltfaciA] = field(default_factory=list)

@dataclass
class APMLTFACResponse(TxResponseMixin):
    trx_id: str = "APMLTFAC"
    type_id: str = "O"
    rtn_code: str = ""
    rtn_mesg: str = ""
    raw_payload: str = ""

REQUEST_TYPE = APMLTFACRequest
RESPONSE_TYPE = APMLTFACResponse

__all__ = [
    "TX_NAME",
    "REQUEST_QUEUE",
    "REPLY_QUEUE",
    "REQUEST_TYPE",
    "RESPONSE_TYPE",
    "ApmltfaciA",
    "APMLTFACRequest",
    "APMLTFACResponse",
]
