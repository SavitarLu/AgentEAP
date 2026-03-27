# secs_eap

`secs_eap` 是基于 `secs_driver` 的 EAP 示例工程，按“驱动适配 -> 消息处理 -> 业务服务 -> 部署运行”分层组织，方便继续做设备定制。

## 目录说明

```text
secs_eap/
├── config/              # 配置模型
├── deploy/              # 启动脚本、部署配置、打包脚本
├── docs/                # 开发与集成文档
├── mes/                 # MES / MQ 集成
├── message_handlers/    # SECS 消息处理
├── services/            # 业务服务
├── usecases/            # 具体消息用例模板
├── driver_adapter.py    # 对 secs_driver 的适配层
└── eap.py               # EAP 主入口
```

## 快速开始

建议在仓库根目录执行：

```bash
cd /path/to/AgentEAP
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install pyyaml
export PYTHONPATH="$(pwd):$PYTHONPATH"
```

验证驱动导入：

```bash
python3 -c "from secs_driver.src.secs_driver import SECSDriver; print('secs_driver import ok')"
```

命令行启动 EAP：

```bash
python3 -m secs_eap.eap --host 127.0.0.1 --port 5000 --mode active --device-id 0 --log-level INFO
```

按设备配置启动：

```bash
python3 secs_eap/deploy/bin/run_eap.py EQP001
```

常用参数：

- `--mode active|passive`
- `--host` / `--port`
- `--device-id`
- `--log-file`
- `--config`，支持 JSON / YAML

## 文档入口

- [文档总览](docs/README.md)
- [消息处理开发指南](docs/handler-development.md)
- [S6F11 Collection Event 配置](docs/collection-events.md)
- [MES APVRYOPE 接入说明](docs/mes-apvryope.md)

## 常见问题

- `ModuleNotFoundError: secs_driver`
  - 在仓库根目录执行 `export PYTHONPATH="$(pwd):$PYTHONPATH"`。
- `No module named yaml`
  - 执行 `python3 -m pip install pyyaml`。
- 已连接但长期未 `selected`
  - 检查双方 `mode` 是否匹配，并确认对端实现了 Select 握手。
