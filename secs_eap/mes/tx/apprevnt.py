"""
APPREVNT transaction codec (JSON payload).

Generated from:
- CAPPREVNT.h
- xlglen.h
- ecslen.h
"""

from dataclasses import dataclass, field
from typing import List

from .base import TxRequestMixin, TxResponseMixin

TX_NAME = "APPREVNT"
REQUEST_QUEUE = "F01.APPREVNTI"
REPLY_QUEUE = "SHARE.REPLY"


@dataclass
class APPREVNTIA:
    waf_id: str = ""
    slot_no: str = ""
    pj_id: str = ""
    vid: str = ""
    vid_name: str = ""
    value: str = ""
    original_value: str = ""
    data_type: str = ""


@dataclass
class APPREVNTRequest(TxRequestMixin):
    trx_id: str = "APPREVNT"
    type_id: str = "I"
    tool_id: str = ""
    chamber_id: str = ""
    step_change_flg: str = ""
    ceid: str = ""
    cename: str = ""
    ctrljob_id: str = ""
    lot_id: str = ""
    lot_type: str = ""
    sublot_id: str = ""
    ope_id: str = ""
    route_id: str = ""
    ope_no: str = ""
    recipe_id: str = ""
    step_no: str = ""
    report_timestamp: str = ""
    arycnt1: str = ""
    ary1: List[APPREVNTIA] = field(default_factory=list)


@dataclass
class APPREVNTResponse(TxResponseMixin):
    trx_id: str = "APPREVNT"
    type_id: str = "O"
    rtn_code: str = ""
    rtn_msg: str = ""
    raw_payload: str = ""


REQUEST_TYPE = APPREVNTRequest
RESPONSE_TYPE = APPREVNTResponse

__all__ = [
    "TX_NAME",
    "REQUEST_QUEUE",
    "REPLY_QUEUE",
    "REQUEST_TYPE",
    "RESPONSE_TYPE",
    "APPREVNTIA",
    "APPREVNTRequest",
    "APPREVNTResponse",
]
