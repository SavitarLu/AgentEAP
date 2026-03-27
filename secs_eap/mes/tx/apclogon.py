"""
APCLOGON transaction codec (JSON payload).

Generated from:
- secs_eap/tx/CAPCLOGON.h
- secs_eap/tx/CAPCLOGON.cpp
"""

from dataclasses import dataclass, field
from typing import List

from .base import TxRequestMixin, TxResponseMixin

TX_NAME = "APCLOGON"
REQUEST_QUEUE = "F01.APCLOGONI"
REPLY_QUEUE = "SHARE.REPLY"

@dataclass
class APCLOGONRequest(TxRequestMixin):
    trx_id: str = "APCLOGON"
    type_id: str = "I"
    user_info: str = ""
    orig_opi_flg: str = ""
    crr_id: str = ""
    eqpt_id: str = ""
    port_id: str = ""
    user_id: str = ""
    ds_recipe_id: str = ""
    ac_recipe_id: str = ""
    force_lgn_flg: str = ""
    dept_code: str = ""
    sht_ope_msg: str = ""

@dataclass
class APCLOGONResponse(TxResponseMixin):
    trx_id: str = "APCLOGON"
    type_id: str = "O"
    rtn_code: str = ""
    rtn_mesg: str = ""
    crr_id: str = ""
    eqpt_id: str = ""
    port_id: str = ""
    raw_payload: str = ""

REQUEST_TYPE = APCLOGONRequest
RESPONSE_TYPE = APCLOGONResponse

__all__ = [
    "TX_NAME",
    "REQUEST_QUEUE",
    "REPLY_QUEUE",
    "REQUEST_TYPE",
    "RESPONSE_TYPE",
    "APCLOGONRequest",
    "APCLOGONResponse",
]
