"""
APCETLOF transaction codec (JSON payload).

Generated from:
- secs_eap/tx/CAPCETLOF.h
- secs_eap/tx/CAPCETLOF.cpp
"""

from dataclasses import dataclass, field
from typing import List

from .base import TxRequestMixin, TxResponseMixin

TX_NAME = "APCETLOF"
REQUEST_QUEUE = "F01.APCETLOFI"
REPLY_QUEUE = "SHARE.REPLY"

@dataclass
class ApcetlofiA:
    sht_id: str = ""
    slot_no: str = ""
    logof_sht_cnt: str = ""
    sht_cnt: str = ""
    mtrl_qty: str = ""
    crr_id: str = ""
    port_id: str = ""

@dataclass
class ApcetlofiA2:
    mtrl_product_id: str = ""
    mtrl_lot_id: str = ""
    seq_no: str = ""
    used_mtrl_qty: str = ""
    add_mtrl_qty: str = ""

@dataclass
class ApcetlofiA3:
    sub_bom_id: str = ""
    addt_info_1: str = ""
    sub_eqpt_id: str = ""
    order: str = ""
    desc: str = ""

@dataclass
class ApcetlofiA4:
    mtrl_product_id: str = ""
    mtrl_qty: str = ""

@dataclass
class APCETLOFRequest(TxRequestMixin):
    trx_id: str = "APCETLOF"
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
    ppbox_id: str = ""
    lot_hld_flg: str = ""
    bom_qty_upd_flg: str = ""
    hld_rsn_cate: str = ""
    hld_rsn_code: str = ""
    dept_code: str = ""
    sht_ope_msg: str = ""
    rwk_id: str = ""
    ce_id: str = ""
    pfc_flg: str = ""
    sht_judge: str = ""
    unit: str = ""
    bulk_id: str = ""
    mark_id: str = ""
    sampling_qty: str = ""
    inprocess_qty: str = ""
    lot_qty: str = ""
    evt_pk_qty: str = ""
    sht_ary_cnt: str = ""
    batch_flg: str = ""
    batch_sub_worder_id: str = ""
    batch_last_flg: str = ""
    iary: List[ApcetlofiA] = field(default_factory=list)
    mtrl_lot_cnt: str = ""
    iary2: List[ApcetlofiA2] = field(default_factory=list)
    worder_process_typ: str = ""
    mo_mtrl_lot_seq_no: str = ""
    rsp_worder_id: str = ""
    bank_id: str = ""
    chk_sub_eqp_cnt: str = ""
    iary3: List[ApcetlofiA3] = field(default_factory=list)
    pre_coat_flg: str = ""
    stk_mtrl_cnt: str = ""
    iary4: List[ApcetlofiA4] = field(default_factory=list)

@dataclass
class APCETLOFResponse(TxResponseMixin):
    trx_id: str = "APCETLOF"
    type_id: str = "O"
    rtn_code: str = ""
    rtn_mesg: str = ""
    crr_id: str = ""
    eqpt_id: str = ""
    user_id: str = ""
    prod_cate: str = ""
    raw_payload: str = ""

REQUEST_TYPE = APCETLOFRequest
RESPONSE_TYPE = APCETLOFResponse

__all__ = [
    "TX_NAME",
    "REQUEST_QUEUE",
    "REPLY_QUEUE",
    "REQUEST_TYPE",
    "RESPONSE_TYPE",
    "ApcetlofiA",
    "ApcetlofiA2",
    "ApcetlofiA3",
    "ApcetlofiA4",
    "APCETLOFRequest",
    "APCETLOFResponse",
]
