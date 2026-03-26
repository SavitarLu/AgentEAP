# secs_eap

基于 `secs_driver` 的 EAP（Equipment Automation Program）示例工程，包含：

- 驱动适配层：`driver_adapter.py`
- 消息处理层：`message_handlers/`
- 业务服务层：`services/`
- 主入口：`eap.py`

## 1. 运行前准备

本项目依赖你本地的 `secs_driver` 源码目录：

- `secs_eap`: `/Users/luxinyu/work/个人/secs_eap`
- `secs_driver`: `/Users/luxinyu/work/个人/secs_driver`

建议使用 Python 3.10+。

```bash
cd "/Users/luxinyu/work/个人/secs_eap"
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install pyyaml
```

> 说明：`EAPConfig.from_file()` 在读取 YAML 配置时需要 `pyyaml`。

## 2. 配置 Python 路径（让 secs_eap 能导入 secs_driver）

当前工程通过 `from secs_driver.src...` 导入驱动模块，因此需要把 `secs_driver` 的父目录加入 `PYTHONPATH`：

```bash
export PYTHONPATH="/Users/luxinyu/work/个人:$PYTHONPATH"
```

可用下面命令快速验证：

```bash
python3 -c "from secs_driver.src.secs_driver import SECSDriver; print('secs_driver import ok')"
```

## 3. 启动方式

### 方式 A：命令行启动 EAP

```bash
cd "/Users/luxinyu/work/个人/secs_eap"
export PYTHONPATH="/Users/luxinyu/work/个人:$PYTHONPATH"
python3 -m secs_eap.eap --host 127.0.0.1 --port 5000 --mode active --device-id 0 --log-level INFO
```

常用参数：

- `--mode active|passive`
- `--host` / `--port`
- `--device-id`
- `--log-file`
- `--config`（支持 JSON/YAML）

## 4. 常见问题

- `ModuleNotFoundError: secs_driver`
  - 先执行 `export PYTHONPATH="/Users/luxinyu/work/个人:$PYTHONPATH"`。
- `No module named yaml`
  - 执行 `python3 -m pip install pyyaml`。
- 已连接但长期未 `selected`
  - 检查双方 `mode` 是否匹配，确认对端是否实现了 Select 握手。
