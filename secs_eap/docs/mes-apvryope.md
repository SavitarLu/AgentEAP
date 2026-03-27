# MES APVRYOPE 接入说明

`mes/` 模块提供 IBM MQ 方式的 MES 事务调用，目前内置了 `mes/tx/apvryope.py` 作为 lot 信息查询示例。

## 配置方式

在设备配置文件中补充 `mes_mq`：

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

## Python 调用示例

```python
resp = await eap.query_lot_by_apvryope(
    eqpt_id="ETCH01",
    port_id="P1",
    crr_id="CRR123",
    user_id="OP001",
)
print(resp.rtn_code, resp.lot_id, resp.product_id)
```

## 工作流中调用

可以在 `business_logic.workflows` 中直接配置：

```yaml
- action: "mes_apvryope"
  transaction:
    trx_id: "APVRYOPE"
    eqpt_id: "E_CLN_01"
    port_id: "01"
    crr_id: "CRR009"
    user_id: "IBM"
```

## 报文格式

请求示例：

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

响应示例：

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

## 注意事项

- 运行时依赖：`ibmmq`
- 报文载荷格式：JSON
- `mq_conn_list` 定义 MQ 网关
- `mq_listener` 定义共享回包队列
- `mq_sender` 选择默认发送别名
- 各 TX 会从 `secs_eap/mes/tx/*.py` 自动发现并注册到 `mes/tx_registry.py`
- 新增 TX 时，推荐按 `apvryope.py` 的方式提供 `TX_NAME`、`REQUEST_QUEUE`、`REQUEST_TYPE`、`RESPONSE_TYPE`
- 响应解析同时兼容 `snake_case` 和大写字段
- 原始响应文本保存在 `raw_payload`
- 当前实现使用官方 `ibmmq` 包，并保持与旧 `pymqi` 风格接口兼容的调用方式
