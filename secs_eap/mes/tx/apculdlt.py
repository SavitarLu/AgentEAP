"""
APCULDLT transaction codec (JSON payload).

Generated from:
- secs_eap/tx/CAPCULDLT.h
- secs_eap/tx/CAPCULDLT.cpp
"""

from dataclasses import dataclass, field
from typing import List

from .base import TxRequestMixin, TxResponseMixin

TX_NAME = "APCULDLT"
REQUEST_QUEUE = "F01.APCULDLTI"
REPLY_QUEUE = "SHARE.REPLY"

@dataclass
class APCULDLTRequest(TxRequestMixin):
    trx_id: str = "APCULDLT"
    type_id: str = "I"
    orig_opi_flg: str = ""
    eqpt_id: str = ""
    port_id: str = ""
    crr_id: str = ""
    container_id: str = ""
    xfr_container_id: str = ""
    clm_user: str = ""
    layer_code: str = ""
    act_typ: str = ""

@dataclass
class APCULDLTResponse(TxResponseMixin):
    trx_id: str = "APCULDLT"
    type_id: str = "O"
    rtn_code: str = ""
    rtn_mesg: str = ""
    raw_payload: str = ""

REQUEST_TYPE = APCULDLTRequest
RESPONSE_TYPE = APCULDLTResponse

__all__ = [
    "TX_NAME",
    "REQUEST_QUEUE",
    "REPLY_QUEUE",
    "REQUEST_TYPE",
    "RESPONSE_TYPE",
    "APCULDLTRequest",
    "APCULDLTResponse",
]
