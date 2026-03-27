"""
Shared logging helpers for protocol-style output.
"""

from datetime import datetime
import logging


class RuntimeLogFormatter(logging.Formatter):
    """Keep normal logs verbose while allowing raw protocol blocks."""

    def format(self, record: logging.LogRecord) -> str:
        if getattr(record, "raw_log", False):
            return record.getMessage()
        return super().format(record)


def protocol_timestamp() -> str:
    now = datetime.now()
    return now.strftime("%Y-%m-%d-%H.%M.%S.") + f"{now.microsecond // 1000:03d}"


def format_tagged_block(text: str, tag: str) -> str:
    """Prefix each line with protocol timestamp and one short tag."""
    lines = str(text or "").splitlines() or [""]
    return "\n".join(
        f"{protocol_timestamp()} [{tag}] {line}" if line else f"{protocol_timestamp()} [{tag}]"
        for line in lines
    )
