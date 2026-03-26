# APVRYOPE MES MQ Usage

This module adds IBM MQ interaction for MES TX `APVRYOPE` (lot info query), using JSON payload format.

## 1) Configure in `EQPxxx.yaml`

```yaml
mes_mq:
  enabled: true
  mq_conn_list:
    QM1: "MESDEVGW1/MESDEVGW1.SVRCONN/95.40.166.36(51419)"
    QM2: "MESDEVGW2/MESDEVGW2.SVRCONN/95.40.166.36(51420)"
  mq_listener:
    MQ1: "QM1/F01.TCS.SHARE/E_CLN_01"
    MQ2: "QM2/F01.TCS.SHARE/E_CLN_01"
  mq_sender:
    MQ1: "QM1"
  user: "appuser"
  password: "secret"
  timeout_ms: 5000
```

## 2) Python call example

```python
resp = await eap.query_lot_by_apvryope(
    eqpt_id="ETCH01",
    port_id="P1",
    crr_id="CRR123",
    user_id="OP001",
)
print(resp.rtn_code, resp.lot_id, resp.product_id)
```

## JSON format example

Request:
```json
{
  "transaction": {
    "trx_id": "APVRYOPE",
    "type_id": "I",
    "eqpt_id": "E_CLN_01",
    "port_id": "01",
    "crr_id": "CRR009",
    "user_id": "IBM"
  }
}
```

Response:
```json
{
  "transaction": {
    "trx_id": "APVRYOPE",
    "type_id": "O",
    "rtn_code": "2401202",
    "rtn_mesg": "Not Found Record [DCARRIST][CRR_ID]=[CRR009                        ]"
  }
}
```

## Notes

- Runtime dependency: `pymqi`.
- MQ payload format: JSON (request/response).
- Cluster mode:
  - `mq_conn_list` defines MQ cluster gateways.
  - `mq_listener` defines shared reply queue (for example `F01.TCS.SHARE`).
  - `mq_sender` selects default sender QM alias.
- TX queue is defined per TX module (not in config):
  - `mes/tx_registry.py`
  - Example: `APVRYOPE -> F01.APVRYOPEI` (from C++ `getquename()` style)
- Response parser accepts both `snake_case` and uppercase field names.
- Full response text is kept in `raw_payload`.
- `user_info` is omitted when empty.
