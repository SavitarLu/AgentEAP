"""
APLSPCPR transaction codec (JSON payload).

Generated from:
- secs_eap/tx/CAPLSPCPR.h
- secs_eap/tx/CAPLSPCPR.cpp
"""

from dataclasses import dataclass, field
from typing import List

from .base import TxRequestMixin, TxResponseMixin

TX_NAME = "APLSPCPR"
REQUEST_QUEUE = "F01.APLSPCPRI"
REPLY_QUEUE = "SHARE.REPLY"

@dataclass
class AplspcproA:
    eqpt_id: str = ""
    product_id: str = ""
    ec_code: str = ""
    route_id: str = ""
    route_ver: str = ""
    ope_id: str = ""
    ope_ver: str = ""
    s_name: str = ""
    s_value: str = ""
    s_desc: str = ""

@dataclass
class APLSPCPRRequest(TxRequestMixin):
    trx_id: str = "APLSPCPR"
    type_id: str = "I"
    user_info: str = ""
    eqpt_id: str = ""
    product_id: str = ""
    ope_id: str = ""
    s_name: str = ""

@dataclass
class APLSPCPRResponse(TxResponseMixin):
    trx_id: str = "APLSPCPR"
    type_id: str = "O"
    rtn_code: str = ""
    rtn_mesg: str = ""
    oary_cnt: str = ""
    oary: List[AplspcproA] = field(default_factory=list)
    raw_payload: str = ""

REQUEST_TYPE = APLSPCPRRequest
RESPONSE_TYPE = APLSPCPRResponse

__all__ = [
    "TX_NAME",
    "REQUEST_QUEUE",
    "REPLY_QUEUE",
    "REQUEST_TYPE",
    "RESPONSE_TYPE",
    "AplspcproA",
    "APLSPCPRRequest",
    "APLSPCPRResponse",
]
