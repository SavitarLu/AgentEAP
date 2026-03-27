"""
APCEQPAL transaction codec (JSON payload).

Generated from:
- secs_eap/tx/CAPCEQPAL.h
- secs_eap/tx/CAPCEQPAL.cpp
"""

from dataclasses import dataclass, field
from typing import List

from .base import TxRequestMixin, TxResponseMixin

TX_NAME = "APCEQPAL"
REQUEST_QUEUE = "F01.APCEQPALI"
REPLY_QUEUE = "SHARE.REPLY"

@dataclass
class APCEQPALRequest(TxRequestMixin):
    trx_id: str = "APCEQPAL"
    type_id: str = "I"
    user_info: str = ""
    eqpt_id: str = ""
    rpt_date: str = ""
    rpt_time: str = ""
    alt_evt_typ: str = ""
    rpt_source: str = ""
    alrt_id: str = ""
    alrt_code: str = ""
    alrt_lvl: str = ""
    alert_on_off_flg: str = ""
    alrt_comment: str = ""
    cfm_user_id: str = ""
    cfm_comment: str = ""

@dataclass
class APCEQPALResponse(TxResponseMixin):
    trx_id: str = "APCEQPAL"
    type_id: str = "O"
    rtn_code: str = ""
    rtn_mesg: str = ""
    raw_payload: str = ""

REQUEST_TYPE = APCEQPALRequest
RESPONSE_TYPE = APCEQPALResponse

__all__ = [
    "TX_NAME",
    "REQUEST_QUEUE",
    "REPLY_QUEUE",
    "REQUEST_TYPE",
    "RESPONSE_TYPE",
    "APCEQPALRequest",
    "APCEQPALResponse",
]
