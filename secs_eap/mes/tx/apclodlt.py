"""
APCLODLT transaction codec (JSON payload).

Generated from:
- secs_eap/tx/CAPCLODLT.h
- secs_eap/tx/CAPCLODLT.cpp
"""

from dataclasses import dataclass, field
from typing import List

from .base import TxRequestMixin, TxResponseMixin

TX_NAME = "APCLODLT"
REQUEST_QUEUE = "F01.APCLODLTI"
REPLY_QUEUE = "SHARE.REPLY"

@dataclass
class APCLODLTRequest(TxRequestMixin):
    trx_id: str = "APCLODLT"
    type_id: str = "I"
    orig_opi_flg: str = ""
    user_info: str = ""
    eqpt_id: str = ""
    port_id: str = ""
    crr_id: str = ""
    container_id: str = ""
    clm_user: str = ""
    layer_code: str = ""
    act_typ: str = ""

@dataclass
class APCLODLTResponse(TxResponseMixin):
    trx_id: str = "APCLODLT"
    type_id: str = "O"
    rtn_code: str = ""
    rtn_mesg: str = ""
    raw_payload: str = ""

REQUEST_TYPE = APCLODLTRequest
RESPONSE_TYPE = APCLODLTResponse

__all__ = [
    "TX_NAME",
    "REQUEST_QUEUE",
    "REPLY_QUEUE",
    "REQUEST_TYPE",
    "RESPONSE_TYPE",
    "APCLODLTRequest",
    "APCLODLTResponse",
]
