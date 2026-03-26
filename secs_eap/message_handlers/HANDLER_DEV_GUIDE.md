# Message Handler Dev Guide

This guide helps beginners customize equipment-specific logic.

## Recommended pattern

For each `SxFy`, split code into:

1. `parse(message) -> RequestDTO`
2. `execute(dto, context) -> ResultDTO`
3. `build_reply(result) -> List[SECSItem]`

This keeps protocol details separate from business logic.

## Example in this project

- Use case template: `usecases/s2f41_remote_command.py`
- Handler integration: `message_handlers/s2_handler.py` (`S2F41Handler`)

## How to add a new message quickly

1. Copy `usecases/s2f41_remote_command.py` as a new file.
2. Rename DTO and use case class to your `SxFy`.
3. Update `parse/execute/build_reply`.
4. Add a new handler class in the target stream handler file.
5. Register it in `SxHandlerManager._handler_map` and `register_handlers()`.

## Debug checklist

- Verify log chain: `RX -> handler -> TX-REPLY`.
- If no reply, check:
  - `message.w_bit` is true
  - handler is mapped in `_handler_map`
  - handler is registered in `register_handlers()`

## Workflow orchestration prototype

For cross-message flows (for example `S6F11 -> S6F12 -> send S2F41`),
use YAML workflow config directly in each equipment file:

- `deploy/config/EQP001.yaml`
- field: `business_logic.workflows`

Optional:
- You can still load extra workflows from a separate file with
  `business_logic.workflow_file`

Current engine supports:
- Trigger by incoming `sf` (e.g. `S6F11`)
- Step action `send_message` with optional `wait_reply` and `timeout`
- Basic item templates with `${job_id}` variable

## Visual drag-drop prototype

- File: `deploy/bin/workflow_designer.html`
- Open with browser and drag nodes:
  - Trigger
  - Send Message
  - Wait Reply (placeholder node for UI)
- Click **Export YAML Snippet** and paste output into:
  - `business_logic.workflows` in `EQPxxx.yaml`
