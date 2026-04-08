"""
APPRDATA transaction codec (JSON payload).

Generated from:
- CAPPRDATA.h
- xlglen.h
- ecslen.h
"""

from dataclasses import dataclass, field
from typing import List

from .base import TxRequestMixin, TxResponseMixin

TX_NAME = "APPRDATA"
REQUEST_QUEUE = "F01.APPRDATAI"
REPLY_QUEUE = "SHARE.REPLY"


@dataclass
class APPRDATAIA:
    svid_value: str = ""
    code: str = ""
    data_type: str = ""
    svid_name: str = ""


@dataclass
class APPRDATARequest(TxRequestMixin):
    trx_id: str = "APPRDATA"
    type_id: str = "I"
    tool_id: str = ""
    chamber_id: str = ""
    start_run_time: str = ""
    batch_id: str = ""
    lot_id: str = ""
    wafer_id: str = ""
    recipe_id: str = ""
    step_no: str = ""
    ceid: str = ""
    cename: str = ""
    sublot_id: str = ""
    slot_no: str = ""
    ope_id: str = ""
    route_id: str = ""
    route_ver: str = ""
    ope_no: str = ""
    prod_id: str = ""
    user_lot_id: str = ""
    trace_id: str = ""
    report_cnt: str = ""
    svid_cnt: str = ""
    ary1: List[APPRDATAIA] = field(default_factory=list)


@dataclass
class APPRDATAResponse(TxResponseMixin):
    trx_id: str = "APPRDATA"
    type_id: str = "O"
    rtn_code: str = ""
    rtn_msg: str = ""
    raw_payload: str = ""


REQUEST_TYPE = APPRDATARequest
RESPONSE_TYPE = APPRDATAResponse

__all__ = [
    "TX_NAME",
    "REQUEST_QUEUE",
    "REPLY_QUEUE",
    "REQUEST_TYPE",
    "RESPONSE_TYPE",
    "APPRDATAIA",
    "APPRDATARequest",
    "APPRDATAResponse",
]
