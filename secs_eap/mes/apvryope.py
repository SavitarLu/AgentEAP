"""
APVRYOPE transaction codec (JSON payload).

Reference:
- apvryope.h
- xlglen.h
"""

from dataclasses import dataclass
from typing import Any, Dict
from collections import OrderedDict


@dataclass
class APVRYOPERequest:
    trx_id: str = "APVRYOPE"
    type_id: str = "I"
    eqpt_id: str = ""
    port_id: str = ""
    crr_id: str = ""
    user_id: str = ""
    user_info: Dict[str, Any] = None

    def to_payload(self) -> Dict[str, Any]:
        # Keep field order stable for MES-side trace comparison.
        tx = OrderedDict()
        tx["trx_id"] = self.trx_id
        tx["type_id"] = self.type_id
        if self.user_info:
            tx["user_info"] = self.user_info
        tx["eqpt_id"] = self.eqpt_id
        tx["port_id"] = self.port_id
        tx["crr_id"] = self.crr_id
        tx["user_id"] = self.user_id
        return {"transaction": tx}


@dataclass
class APVRYOPEResponse:
    trx_id: str
    type_id: str
    rtn_code: str
    rtn_mesg: str
    eqpt_id: str
    port_id: str
    crr_id: str
    user_id: str
    lot_id: str
    splt_id: str
    product_cate: str
    product_id: str
    nx_route_id: str
    nx_proc_id: str
    nx_ope_no: str
    nx_ope_id: str
    recipe_id: str
    raw_payload: str

    @classmethod
    def from_payload(cls, payload: Dict[str, Any], raw_payload: str = "") -> "APVRYOPEResponse":
        root = payload.get("transaction", payload) if isinstance(payload, dict) else {}

        def g(*keys: str) -> str:
            for key in keys:
                if key in root and root[key] is not None:
                    return str(root[key])
            return ""

        return cls(
            trx_id=g("trx_id", "TRX_ID"),
            type_id=g("type_id", "TYPE_ID"),
            rtn_code=g("rtn_code", "RTN_CODE"),
            rtn_mesg=g("rtn_mesg", "RTN_MESG"),
            eqpt_id=g("eqpt_id", "EQPT_ID"),
            port_id=g("port_id", "PORT_ID"),
            crr_id=g("crr_id", "CRR_ID"),
            user_id=g("user_id", "USER_ID"),
            lot_id=g("lot_id", "LOT_ID"),
            splt_id=g("splt_id", "SPLT_ID"),
            product_cate=g("product_cate", "PRODUCT_CATE"),
            product_id=g("product_id", "PRODUCT_ID"),
            nx_route_id=g("nx_route_id", "NX_ROUTE_ID"),
            nx_proc_id=g("nx_proc_id", "NX_PROC_ID"),
            nx_ope_no=g("nx_ope_no", "NX_OPE_NO"),
            nx_ope_id=g("nx_ope_id", "NX_OPE_ID"),
            recipe_id=g("recipe_id", "RECIPE_ID"),
            raw_payload=raw_payload,
        )

