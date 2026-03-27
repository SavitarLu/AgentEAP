# S6F11 Collection Event 配置

为了让 `S6F11` 的处理尽量不依赖硬编码，当前项目支持把 `CEID / RPTID / VID` 直接写进设备配置。

## 推荐写法

```yaml
business_logic:
  collection_events:
    variables:
      303:
        name: lp_id
      310:
        name: carrier_id
    reports:
      8702:
        name: carrier_waiting_host
        vids: [310, 303]
    events:
      214:
        name: carrier_waiting_for_host
        reports: [8702]
```

## 字段说明

- `variables`
  - key 是 `VID`
  - `name` 是开发者看到的变量名，也会自动成为 workflow 变量名
- `reports`
  - key 是 `RPTID`
  - `vids` 定义该 report 中各数据项按顺序对应的 `VID`
- `events`
  - key 是 `CEID`
  - `reports` 定义该事件理论上关联的报表列表

## 兼容思路

为了方便从旧方案迁移，解析器同时兼容下面这些命名风格：

- `variables` 或 `vid_tab`
- `reports` 或 `rptid_tab`
- `events` 或 `ceid_tab`
- 事件名可写 `name` 或 `ename`

## 从旧 Lua 配置迁移

你原来的方案里通常是下面这种结构：

```lua
VID_TAB = {
  [303] = 'LpID',
  [310] = 'CarrierID',
}

RPTID_TAB = {
  [8702] = { 310, 303 },
}

CEID_TAB = {
  [214] = { ename = 'EQP_CarrierSM_03_WaitingForHost', 8702 },
}
```

迁到现在的 EAP，推荐直接写成 YAML：

```yaml
business_logic:
  collection_events:
    variables:
      303:
        name: lp_id
      310:
        name: carrier_id
    reports:
      8702:
        name: carrier_waiting_host
        vids: [310, 303]
    events:
      214:
        name: carrier_waiting_for_host
        reports: [8702]
```

这样做有两个好处：

- 配置结构更直白，开发者不用再记 Lua table 的位置语义
- `name` 会直接成为 workflow 变量名，例如 `carrier_id`、`lp_id`

## 运行效果

收到 `S6F11` 后，EAP 会把事件解析成结构化数据，并写入上下文：

- `ceid`
- `event_name`
- 各个 `VID` 对应的友好字段，例如 `carrier_id`

所以在 workflow 里可以直接用：

```yaml
trigger:
  sf: "S6F11"
  ceid: 214

steps:
  - action: "mes_apvryope"
    transaction:
      port_id: "${lp_id}"
      crr_id: "${carrier_id}"
```

## Online Remote 自动下发 S2Fx

如果设备在 `Online Remote` 事件后，需要像旧 TAP 里的 `BEGIN_ONLINE_REMOTE` 一样自动执行：

- `S2F37` 禁用事件
- `S2F35` 清空事件和报表关联
- `S2F33` 清空报表
- `S2F33` 重新定义报表
- `S2F35` 重新关联事件和报表
- `S2F37` 重新启用事件

现在可以直接用一个 workflow action：

```yaml
business_logic:
  collection_events:
    id_types:
      data_id: U4
      ceid: U4
      rptid: U4
      vid: U4
    report_setup:
      clear_data_id: 0
      define_data_id: 1
      link_data_id: 1
      enable_mode: all

  workflows:
    - name: s6f11_online_remote_setup_reports
      trigger:
        sf: "S6F11"
        event_name: "online_remote"
      steps:
        - action: "configure_collection_events"
```

这里的 `id_types` 就是给 `DATAID / CEID / RPTID / VID` 选 SECS item 类型，常见是 `U1`、`U2`、`U4`。如果某台设备要求 `DATAID=U2`、其余是 `U4`，直接改配置就行，不需要改代码。

另外，普通 `send_message` workflow 现在也支持 `BOOLEAN/BL`，所以像 `S2F37` 里的 `<BL T>`、`<BL F>` 也能手写。

## 注意

- 如果设备实际上没有按标准把 `CEID / RPTID` 带出来，解析器仍会保留原始层级，但无法自动命中定义。
- 如果一个 report 的实际字段数量和 `vids` 不一致，未命中的字段会自动命名为 `value_1`、`value_2`。
