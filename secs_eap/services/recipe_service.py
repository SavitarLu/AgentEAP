"""
Recipe storage service for S7 process program handlers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import copy
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import quote

from secs_driver.src.secs_message import SECSItem
from secs_driver.src.secs_types import SECSType, SECSTypeInfo


logger = logging.getLogger(__name__)


def _default_recipe_dir() -> Path:
    cwd = Path.cwd()
    source_dir = cwd / "secs_eap" / "deploy" / "recipes"
    if source_dir.parent.exists():
        return source_dir

    deploy_dir = cwd / "deploy" / "recipes"
    if deploy_dir.parent.exists():
        return deploy_dir

    return cwd / "recipes"


def _recipe_filename(ppid: str) -> str:
    return f"{quote(ppid, safe='')}.json"


def _serialize_item(item: SECSItem) -> Dict:
    payload = {"type": int(item.type)}
    if item.type == SECSType.LIST:
        payload["children"] = [_serialize_item(child) for child in item.children]
        return payload

    if isinstance(item.value, bytes):
        payload["value_hex"] = item.value.hex().upper()
        payload["value_kind"] = "bytes"
        return payload

    payload["value"] = item.value
    return payload


def _deserialize_item(data: Dict) -> SECSItem:
    item_type = SECSType(int(data.get("type", int(SECSType.ASCII))))
    if item_type == SECSType.LIST:
        return SECSItem.list_([_deserialize_item(child) for child in data.get("children", [])])

    if data.get("value_kind") == "bytes":
        value = bytes.fromhex(str(data.get("value_hex", "")))
    else:
        value = data.get("value")
    return SECSItem(type=item_type, value=value)


@dataclass
class RecipeRecord:
    ppid: str
    body: SECSItem
    updated_at: str
    source: str = ""

    @property
    def body_type(self) -> str:
        return SECSTypeInfo.get_name(self.body.type)

    def to_storage(self) -> Dict:
        return {
            "ppid": self.ppid,
            "updated_at": self.updated_at,
            "source": self.source,
            "body": _serialize_item(self.body),
        }

    @classmethod
    def from_storage(cls, payload: Dict) -> "RecipeRecord":
        return cls(
            ppid=str(payload.get("ppid", "")).strip(),
            updated_at=str(payload.get("updated_at", "")),
            source=str(payload.get("source", "")),
            body=_deserialize_item(payload.get("body", {})),
        )


class RecipeService:
    """Local recipe repository used by S7 process program handlers."""

    def __init__(
        self,
        storage_dir: Optional[str] = None,
        allow_overwrite: bool = True,
    ):
        self._storage_dir = Path(storage_dir).expanduser() if storage_dir else _default_recipe_dir()
        self._allow_overwrite = allow_overwrite
        self._recipes: Dict[str, RecipeRecord] = {}
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self.scan()

    @property
    def storage_dir(self) -> Path:
        return self._storage_dir

    @property
    def allow_overwrite(self) -> bool:
        return self._allow_overwrite

    def scan(self) -> int:
        self._recipes.clear()
        for path in sorted(self._storage_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                record = RecipeRecord.from_storage(payload)
                if not record.ppid:
                    logger.warning("Skip recipe file without PPID: %s", path)
                    continue
                self._recipes[record.ppid] = record
            except Exception as exc:
                logger.warning("Skip invalid recipe file %s: %s", path, exc)
        logger.info("Scanned %d recipes", len(self._recipes))
        return len(self._recipes)

    def list_recipe_ids(self) -> List[str]:
        return sorted(self._recipes)

    def has_recipe(self, ppid: str) -> bool:
        return self._normalize_ppid(ppid) in self._recipes

    def get_recipe(self, ppid: str) -> Optional[RecipeRecord]:
        key = self._normalize_ppid(ppid)
        record = self._recipes.get(key)
        if not record:
            return None
        return RecipeRecord(
            ppid=record.ppid,
            body=copy.deepcopy(record.body),
            updated_at=record.updated_at,
            source=record.source,
        )

    def can_accept_upload(self, ppid: str) -> tuple[bool, int, str]:
        key = self._normalize_ppid(ppid)
        if not key:
            return False, 1, "PPID is empty"
        if self.has_recipe(key) and not self._allow_overwrite:
            return False, 1, f"Recipe already exists and overwrite is disabled: {key}"
        return True, 0, "accepted"

    def save_recipe(self, ppid: str, body: SECSItem, source: str = "S7F3") -> RecipeRecord:
        key = self._normalize_ppid(ppid)
        if not key:
            raise ValueError("PPID is empty")
        if self.has_recipe(key) and not self._allow_overwrite:
            raise FileExistsError(f"Recipe already exists: {key}")

        record = RecipeRecord(
            ppid=key,
            body=copy.deepcopy(body),
            updated_at=datetime.now().isoformat(timespec="seconds"),
            source=source,
        )
        file_path = self._storage_dir / _recipe_filename(key)
        file_path.write_text(
            json.dumps(record.to_storage(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._recipes[key] = record
        logger.info(
            "Saved recipe: ppid=%s body_type=%s dir=%s",
            key,
            record.body_type,
            self._storage_dir,
        )
        return self.get_recipe(key) or record

    def delete_recipes(self, ppids: List[str]) -> tuple[int, List[str]]:
        deleted = 0
        missing: List[str] = []
        for ppid in ppids:
            key = self._normalize_ppid(ppid)
            if not key:
                continue
            record = self._recipes.pop(key, None)
            if record is None:
                missing.append(key)
                continue
            file_path = self._storage_dir / _recipe_filename(key)
            if file_path.exists():
                file_path.unlink()
            deleted += 1

        if deleted:
            logger.info("Deleted %d recipe(s)", deleted)
        if missing:
            logger.warning("Recipe delete missed %d PPID(s): %s", len(missing), missing)
        return deleted, missing

    @staticmethod
    def _normalize_ppid(ppid: str) -> str:
        return str(ppid or "").strip()

