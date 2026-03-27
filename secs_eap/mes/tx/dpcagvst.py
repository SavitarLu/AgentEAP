"""
DPCAGVST transaction codec (JSON payload).

Generated from:
- secs_eap/tx/CDPCAGVST.h
- secs_eap/tx/CDPCAGVST.cpp
"""

from dataclasses import dataclass, field
from typing import List

from .base import TxRequestMixin, TxResponseMixin

TX_NAME = "DPCAGVST"
REQUEST_QUEUE = "F01.DPCAGVSTI"
REPLY_QUEUE = "SHARE.REPLY"

@dataclass
class DPCAGVSTRequest(TxRequestMixin):
    trx_id: str = "DPCAGVST"
    type_id: str = "I"
    clm_date: str = ""
    clm_time: str = ""
    user_id: str = ""
    eqpt_id: str = ""
    port_id: str = ""
    agv_mode: str = ""
    ld_agv_mode: str = ""
    ul_agv_mode: str = ""
    event_shop: str = ""

@dataclass
class DPCAGVSTResponse(TxResponseMixin):
    trx_id: str = "DPCAGVST"
    type_id: str = "O"
    rtn_code: str = ""
    rtn_mesg: str = ""
    raw_payload: str = ""

REQUEST_TYPE = DPCAGVSTRequest
RESPONSE_TYPE = DPCAGVSTResponse

__all__ = [
    "TX_NAME",
    "REQUEST_QUEUE",
    "REPLY_QUEUE",
    "REQUEST_TYPE",
    "RESPONSE_TYPE",
    "DPCAGVSTRequest",
    "DPCAGVSTResponse",
]
