"""
RPCAEQRP transaction codec (JSON payload).

Generated from:
- secs_eap/tx/CRPCAEQRP.h
- secs_eap/tx/CRPCAEQRP.cpp
"""

from dataclasses import dataclass, field
from typing import List

from .base import TxRequestMixin, TxResponseMixin

TX_NAME = "RPCAEQRP"
REQUEST_QUEUE = "F01.RPCAEQRPI"
REPLY_QUEUE = "SHARE.REPLY"

@dataclass
class RpcaeqrpiA2:
    recipe_para_name: str = ""
    recipe_para_val: str = ""

@dataclass
class RpcaeqrpiA1:
    c_block_name: str = ""
    sub_recipe_para_cnt: str = ""
    iary2: List[RpcaeqrpiA2] = field(default_factory=list)

@dataclass
class RpcaeqrpiA:
    sub_eqpt_id: str = ""
    p_block_name: str = ""
    step_cnt: str = ""
    iary1: List[RpcaeqrpiA1] = field(default_factory=list)

@dataclass
class RPCAEQRPRequest(TxRequestMixin):
    trx_id: str = "RPCAEQRP"
    type_id: str = "I"
    user_info: str = ""
    eqpt_id: str = ""
    recipe_id: str = ""
    recipe_level: str = ""
    request_user_id: str = ""
    confirm_user_id: str = ""
    claim_memo: str = ""
    audit_req: str = ""
    sub_eqpt_cnt: str = ""
    iary: List[RpcaeqrpiA] = field(default_factory=list)

@dataclass
class RPCAEQRPResponse(TxResponseMixin):
    trx_id: str = "RPCAEQRP"
    type_id: str = "O"
    rtn_code: str = ""
    rtn_mesg: str = ""
    raw_payload: str = ""

REQUEST_TYPE = RPCAEQRPRequest
RESPONSE_TYPE = RPCAEQRPResponse

__all__ = [
    "TX_NAME",
    "REQUEST_QUEUE",
    "REPLY_QUEUE",
    "REQUEST_TYPE",
    "RESPONSE_TYPE",
    "RpcaeqrpiA2",
    "RpcaeqrpiA1",
    "RpcaeqrpiA",
    "RPCAEQRPRequest",
    "RPCAEQRPResponse",
]
