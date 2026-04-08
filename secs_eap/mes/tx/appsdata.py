"""
APPSDATA transaction codec (JSON payload).

Generated from:
- CAPPSDATA.h
- xlglen.h
- ecslen.h
"""

from dataclasses import dataclass, field
from typing import List

from .base import TxRequestMixin, TxResponseMixin

TX_NAME = "APPSDATA"
REQUEST_QUEUE = "F01.APPSDATAI"
REPLY_QUEUE = "SHARE.REPLY"


@dataclass
class APPSDATAOA2:
    svid_value: str = ""
    code: str = ""
    svid_name: str = ""


@dataclass
class APPSDATAOA1:
    trace_id: str = ""
    chamber_id: str = ""
    start_ceid: str = ""
    end_ceid: str = ""
    repgsz: str = ""
    dsper: str = ""
    max_ds: str = ""
    data_type: str = ""
    arycnt2: str = ""
    ary2: List[APPSDATAOA2] = field(default_factory=list)


@dataclass
class APPSDATARequest(TxRequestMixin):
    trx_id: str = "APPSDATA"
    type_id: str = "I"
    reqmode: str = ""
    message_id: str = ""
    message_key: str = ""
    eqp_id: str = ""
    report_timestamp: str = ""


@dataclass
class APPSDATAResponse(TxResponseMixin):
    trx_id: str = "APPSDATA"
    type_id: str = "O"
    rtn_code: str = ""
    rtn_msg: str = ""
    message_id: str = ""
    message_key: str = ""
    eqp_id: str = ""
    report_timestamp: str = ""
    arycnt1: str = ""
    ary1: List[APPSDATAOA1] = field(default_factory=list)
    raw_payload: str = ""


REQUEST_TYPE = APPSDATARequest
RESPONSE_TYPE = APPSDATAResponse

__all__ = [
    "TX_NAME",
    "REQUEST_QUEUE",
    "REPLY_QUEUE",
    "REQUEST_TYPE",
    "RESPONSE_TYPE",
    "APPSDATAOA2",
    "APPSDATAOA1",
    "APPSDATARequest",
    "APPSDATAResponse",
]
