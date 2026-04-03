# MES APVRYOPE 接入说明

`mes/` 模块提供 IBM MQ 方式的 MES 事务调用，目前内置了 `mes/tx/apvryope.py` 作为 lot 信息查询示例。

当前也支持共享队列上的入站 TX 处理，`RPLRPTCS` 已接入为默认流程。

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

equipment:
  name: "E_CLN_01"
  user_id: "AGT"
```

## Python 调用示例

```python
from secs_eap.mes.tx.apvryope import APVRYOPERequest

request = APVRYOPERequest(
    eqpt_id="ETCH01",
    port_id="01",
    crr_id="CRR123",
    user_id="OP001",
)
resp = await eap.execute_mes_tx("APVRYOPE", request)
print(resp.rtn_code, resp.lot_id, resp.product_id)
```

## 工作流中调用

可以在 `business_logic.workflows` 中直接配置：

```yaml
- action: "call_method"
  method: "inquiry_proc_start"
  port_type: "loader"
  port_id: "01"
  carrier_id: "CRR009"
  user_id: "${equipment_user_id}"
```

如果想按老 TAPAPI 的 `inquiry_proc_start` 风格串起 `APVRYOPE -> APIITEML -> APCLOGON`，直接从 workflow 调用 `services/call_method.py` 中的方法即可：

```yaml
- action: "call_method"
  method: "inquiry_proc_start"
  port_type: "loader"
  port_id: "${lp_id}"
  carrier_id: "${carrier_id}"
  user_id: "${equipment_user_id}"
```

当前 `inquiry_proc_start()` 的行为：

1. 发送 `APVRYOPE`
2. 把返回内容写入 `port_context_store`
3. 在日志里打印当前 `port_context_store` 快照
4. 如果 `mes_id` 不为空，再发送 `APIITEML`
5. 最后发送 `APCLOGON`

如果设备上报的 `lp_id` 是数字，例如 `1`，当前 workflow 和 `call_method` 会在与 MES 交互前自动补成两位，例如 `01`。`port_context_store` 查询同时兼容 `1` 和 `01`。

## 入站 TX 流程

当 MQ 共享队列收到 `RPLRPTCS` 请求时，EAP 会自动执行以下流程：

1. 解析入站 `RPLRPTCS` 请求
2. 向设备发送 `S7F19`
3. 解析设备 `S7F20` 返回的 Recipe ID list
4. 回传 `RPLRPTCS` 响应到来包指定的 `ReplyToQ`；若来包未带 `ReplyToQ`，则回到该 TX 模块配置的 `REPLY_QUEUE`

当前响应字段约定：

- 成功时：`retcode1="0"`、`sqlcode="0"`
- 失败时：`retcode1="1"`、`sqlcode="-1"`

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
- `mq_listener` 定义共享回包/入站请求队列
- `mq_sender` 按配置顺序做主备；先走第一个 alias，只有主链路在请求成功放入 MQ 之前失败时才切到后面的备链路
- 各 TX 会从 `secs_eap/mes/tx/*.py` 自动发现并注册到 `mes/tx_registry.py`
- 新增 TX 时，推荐按 `apvryope.py` 的方式提供 `TX_NAME`、`REQUEST_QUEUE`、`REQUEST_TYPE`、`RESPONSE_TYPE`
- 响应解析同时兼容 `snake_case` 和大写字段
- 原始响应文本保存在 `raw_payload`
- 当前实现使用官方 `ibmmq` 包，并保持与旧 `pymqi` 风格接口兼容的调用方式
