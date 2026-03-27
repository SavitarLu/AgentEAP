"""
RPCDLTCS transaction codec (JSON payload).

Generated from:
- secs_eap/tx/CRPCDLTCS.h
- secs_eap/tx/CRPCDLTCS.cpp
"""

from dataclasses import dataclass, field
from typing import List

from .base import TxRequestMixin, TxResponseMixin

TX_NAME = "RPCDLTCS"
REQUEST_QUEUE = "F01.RPCDLTCSI"
REPLY_QUEUE = "SHARE.REPLY"

@dataclass
class RpcdltcsoA2:
    recipe_para_name: str = ""
    recipe_para_val: str = ""

@dataclass
class RpcdltcsoA1:
    sub_eqpt_id: str = ""
    sub_recipe_id: str = ""
    sub_recipe_para_cnt: str = ""
    oary2: List[RpcdltcsoA2] = field(default_factory=list)

@dataclass
class RPCDLTCSRequest(TxRequestMixin):
    trx_id: str = "RPCDLTCS"
    type_id: str = "I"
    user_info: str = ""
    eqpt_id: str = ""
    recipe_id: str = ""
    recipe_level: str = ""
    option: str = ""
    user_id: str = ""
    claim_memo: str = ""

@dataclass
class RPCDLTCSResponse(TxResponseMixin):
    trx_id: str = "RPCDLTCS"
    type_id: str = "O"
    rtn_code: str = ""
    rtn_mesg: str = ""
    recipe_id: str = ""
    sub_eqpt_cnt: str = ""
    oary1: List[RpcdltcsoA1] = field(default_factory=list)
    raw_payload: str = ""

REQUEST_TYPE = RPCDLTCSRequest
RESPONSE_TYPE = RPCDLTCSResponse

__all__ = [
    "TX_NAME",
    "REQUEST_QUEUE",
    "REPLY_QUEUE",
    "REQUEST_TYPE",
    "RESPONSE_TYPE",
    "RpcdltcsoA2",
    "RpcdltcsoA1",
    "RPCDLTCSRequest",
    "RPCDLTCSResponse",
]
