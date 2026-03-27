# 消息处理开发指南

这份文档用于说明如何在 `secs_eap` 中新增或定制 `SxFy` 消息处理逻辑。

## 推荐模式

建议把每个消息拆成三层：

1. `parse(message) -> RequestDTO`
2. `execute(dto, context) -> ResultDTO`
3. `build_reply(result) -> List[SECSItem]`

这样协议解析、业务执行和回复拼装会更清晰，便于后续维护。

## 当前工程示例

- 用例模板：`usecases/s2f41_remote_command.py`
- 处理器接入：`message_handlers/s2_handler.py` 中的 `S2F41Handler`

## 新增一个消息处理器

1. 复制 `usecases/s2f41_remote_command.py` 作为新用例模板。
2. 按目标消息重命名 DTO 和 UseCase 类。
3. 实现 `parse / execute / build_reply`。
4. 在对应的 `message_handlers/sx_handler.py` 中新增处理器类。
5. 把处理器注册到对应的 `SxHandlerManager`。

## 调试检查项

- 观察日志链路是否完整：`RX -> handler -> TX-REPLY`
- 如果没有自动回复，优先检查：
  - `message.w_bit` 是否为 `True`
  - 处理器是否注册到目标 `SxHandlerManager`
  - 对应 Stream 是否被 `EAP` 注册进 `MessageDispatcher`

## 工作流编排

跨消息联动流程建议优先写在 YAML 里，而不是直接塞进 handler：

- 配置文件：`deploy/config/EQP001.yaml`
- 配置字段：`business_logic.workflows`

也可以通过 `business_logic.workflow_file` 额外加载工作流文件。

当前工作流引擎支持：

- 通过 `sf` 触发，例如 `S6F11`
- `send_message`
- `mes_apvryope`
- `if_hcack`
- `wait_reply`
- `${variable}` 形式的简单变量替换

## 可视化原型

- 文件：`deploy/bin/workflow_designer.html`
- 可拖拽节点：
  - Trigger
  - Send Message
  - Wait Reply

导出的 YAML 片段可以直接粘贴到设备配置中的 `business_logic.workflows`。
