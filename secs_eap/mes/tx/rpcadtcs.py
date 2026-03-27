"""
RPCADTCS transaction codec (JSON payload).

Generated from:
- secs_eap/tx/CRPCADTCS.h
- secs_eap/tx/CRPCADTCS.cpp
"""

from dataclasses import dataclass, field
from typing import List

from .base import TxRequestMixin, TxResponseMixin

TX_NAME = "RPCADTCS"
REQUEST_QUEUE = "F01.RPCADTCSI"
REPLY_QUEUE = "SHARE.REPLY"

@dataclass
class RPCADTCSRequest(TxRequestMixin):
    trx_id: str = "RPCADTCS"
    type_id: str = "I"
    user_info: str = ""
    eqpt_id: str = ""
    recipe_id: str = ""
    recipe_level: str = ""
    rcp_file_name: str = ""
    option: str = ""
    user_id: str = ""
    claim_memo: str = ""
    tcs_req: str = ""

@dataclass
class RPCADTCSResponse(TxResponseMixin):
    trx_id: str = "RPCADTCS"
    type_id: str = "O"
    rtn_code: str = ""
    rtn_mesg: str = ""
    raw_payload: str = ""

REQUEST_TYPE = RPCADTCSRequest
RESPONSE_TYPE = RPCADTCSResponse

__all__ = [
    "TX_NAME",
    "REQUEST_QUEUE",
    "REPLY_QUEUE",
    "REQUEST_TYPE",
    "RESPONSE_TYPE",
    "RPCADTCSRequest",
    "RPCADTCSResponse",
]
