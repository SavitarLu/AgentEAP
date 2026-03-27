"""
RPVUPLOD transaction codec (JSON payload).

Generated from:
- secs_eap/tx/CRPVUPLOD.h
- secs_eap/tx/CRPVUPLOD.cpp
"""

from dataclasses import dataclass, field
from typing import List

from .base import TxRequestMixin, TxResponseMixin

TX_NAME = "RPVUPLOD"
REQUEST_QUEUE = "F01.TCS.SHARE"
REPLY_QUEUE = "SHARE.REPLY"

@dataclass
class RPVUPLODRequest(TxRequestMixin):
    trx_id: str = "RPVUPLOD"
    type_id: str = "I"
    eqp_id: str = ""
    rcp_id: str = ""

@dataclass
class RPVUPLODResponse(TxResponseMixin):
    trx_id: str = "RPVUPLOD"
    type_id: str = "O"
    retcode1: str = ""
    sqlcode: str = ""
    raw_payload: str = ""

REQUEST_TYPE = RPVUPLODRequest
RESPONSE_TYPE = RPVUPLODResponse

__all__ = [
    "TX_NAME",
    "REQUEST_QUEUE",
    "REPLY_QUEUE",
    "REQUEST_TYPE",
    "RESPONSE_TYPE",
    "RPVUPLODRequest",
    "RPVUPLODResponse",
]
