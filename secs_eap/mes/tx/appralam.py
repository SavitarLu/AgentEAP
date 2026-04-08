"""
APPRALAM transaction codec (JSON payload).

Generated from:
- CAPPRALAM.h
- xlglen.h
- ecslen.h
"""

from dataclasses import dataclass

from .base import TxRequestMixin, TxResponseMixin

TX_NAME = "APPRALAM"
REQUEST_QUEUE = "F01.APPRALAMI"
REPLY_QUEUE = "SHARE.REPLY"


@dataclass
class APPRALAMRequest(TxRequestMixin):
    trx_id: str = "APPRALAM"
    type_id: str = "I"
    reqmode: str = ""
    message_id: str = ""
    message_key: str = ""
    eqp_id: str = ""
    alarm_id: str = ""
    alarm_code: str = ""
    alarm_type: str = ""
    alarm_text: str = ""
    report_timestamp: str = ""


@dataclass
class APPRALAMResponse(TxResponseMixin):
    trx_id: str = "APPRALAM"
    type_id: str = "O"
    rtn_code: str = ""
    rtn_msg: str = ""
    raw_payload: str = ""


REQUEST_TYPE = APPRALAMRequest
RESPONSE_TYPE = APPRALAMResponse

__all__ = [
    "TX_NAME",
    "REQUEST_QUEUE",
    "REPLY_QUEUE",
    "REQUEST_TYPE",
    "RESPONSE_TYPE",
    "APPRALAMRequest",
    "APPRALAMResponse",
]
