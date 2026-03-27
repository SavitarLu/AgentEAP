"""
S6F11 collection event schema and parser.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from secs_driver.src.secs_message import SECSItem, SECSMessage
from secs_driver.src.secs_types import SECSTypeInfo


def _normalize_id(value: Any) -> str:
    """Normalize CEID/RPTID/VID keys for schema lookup."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.hex().upper()
    return str(value).strip()


def _item_to_python(item: Optional[SECSItem]) -> Any:
    """Convert one SECS item into plain Python data."""
    if item is None:
        return None
    if item.type == item.type.LIST:
        return [_item_to_python(child) for child in item.children]
    if isinstance(item.value, bytes):
        return item.value.hex().upper()
    if isinstance(item.value, str):
        return item.value.strip()
    return item.value


@dataclass
class EventVariableDefinition:
    vid: str
    name: str
    description: str = ""


@dataclass
class EventReportDefinition:
    rptid: str
    name: str = ""
    vids: List[str] = field(default_factory=list)


@dataclass
class CollectionEventDefinition:
    ceid: str
    name: str = ""
    rptids: List[str] = field(default_factory=list)


@dataclass
class CollectionEventValue:
    vid: str
    name: str
    value: Any
    item_type: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vid": self.vid,
            "name": self.name,
            "value": self.value,
            "item_type": self.item_type,
        }


@dataclass
class CollectionEventReport:
    rptid: str
    name: str
    values: List[CollectionEventValue] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rptid": self.rptid,
            "name": self.name,
            "values": [value.to_dict() for value in self.values],
        }


@dataclass
class CollectionEventPayload:
    data_id: Any
    ceid: str
    name: str
    reports: List[CollectionEventReport] = field(default_factory=list)
    fields: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "data_id": self.data_id,
            "ceid": self.ceid,
            "name": self.name,
            "reports": [report.to_dict() for report in self.reports],
            "fields": dict(self.fields),
        }

    def to_workflow_vars(self) -> Dict[str, Any]:
        vars_ = {
            "data_id": self.data_id,
            "ceid": self.ceid,
            "event_name": self.name,
        }
        vars_.update(self.fields)
        return vars_


@dataclass
class CollectionEventSchema:
    variables: Dict[str, EventVariableDefinition] = field(default_factory=dict)
    reports: Dict[str, EventReportDefinition] = field(default_factory=dict)
    events: Dict[str, CollectionEventDefinition] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: Optional[Dict[str, Any]]) -> "CollectionEventSchema":
        raw = raw or {}
        variables = cls._build_variables(raw.get("variables", raw.get("vid_tab", {})))
        reports = cls._build_reports(raw.get("reports", raw.get("rptid_tab", {})))
        events = cls._build_events(raw.get("events", raw.get("ceid_tab", {})))
        return cls(variables=variables, reports=reports, events=events)

    @staticmethod
    def _build_variables(raw: Dict[str, Any]) -> Dict[str, EventVariableDefinition]:
        result: Dict[str, EventVariableDefinition] = {}
        for vid, definition in (raw or {}).items():
            key = _normalize_id(vid)
            if isinstance(definition, dict):
                name = str(definition.get("name") or definition.get("vname") or key)
                description = str(definition.get("description", ""))
            else:
                name = str(definition)
                description = ""
            result[key] = EventVariableDefinition(vid=key, name=name, description=description)
        return result

    @staticmethod
    def _build_reports(raw: Dict[str, Any]) -> Dict[str, EventReportDefinition]:
        result: Dict[str, EventReportDefinition] = {}
        for rptid, definition in (raw or {}).items():
            key = _normalize_id(rptid)
            if isinstance(definition, dict):
                name = str(definition.get("name") or definition.get("rname") or key)
                vids = [_normalize_id(vid) for vid in definition.get("vids", definition.get("variables", []))]
            else:
                name = key
                vids = [_normalize_id(vid) for vid in (definition or [])]
            result[key] = EventReportDefinition(rptid=key, name=name, vids=vids)
        return result

    @staticmethod
    def _build_events(raw: Dict[str, Any]) -> Dict[str, CollectionEventDefinition]:
        result: Dict[str, CollectionEventDefinition] = {}
        for ceid, definition in (raw or {}).items():
            key = _normalize_id(ceid)
            if isinstance(definition, dict):
                name = str(definition.get("name") or definition.get("ename") or key)
                rptids = [
                    _normalize_id(rptid)
                    for rptid in definition.get("reports", definition.get("rptids", []))
                ]
            else:
                name = key
                rptids = [_normalize_id(rptid) for rptid in (definition or [])]
            result[key] = CollectionEventDefinition(ceid=key, name=name, rptids=rptids)
        return result


class CollectionEventParser:
    """Parse S6F11 messages into configured collection events."""

    def __init__(self, schema: Optional[CollectionEventSchema] = None):
        self._schema = schema or CollectionEventSchema()

    @property
    def schema(self) -> CollectionEventSchema:
        return self._schema

    def set_schema(self, schema: CollectionEventSchema) -> None:
        self._schema = schema

    def parse_s6f11(self, message: SECSMessage) -> Optional[CollectionEventPayload]:
        if message.sf != "S6F11" or not message.items:
            return None

        root = message.items[0]
        if root.type != root.type.LIST or len(root.children) < 3:
            return None

        data_id = _item_to_python(root.children[0])
        ceid = _normalize_id(_item_to_python(root.children[1]))
        event_def = self._schema.events.get(ceid)
        payload = CollectionEventPayload(
            data_id=data_id,
            ceid=ceid,
            name=event_def.name if event_def else ceid or "unknown_event",
        )

        reports_item = root.children[2]
        if reports_item.type != reports_item.type.LIST:
            return payload

        for report_index, report_item in enumerate(reports_item.children, start=1):
            if report_item.type != report_item.type.LIST or len(report_item.children) < 2:
                continue

            rptid = _normalize_id(_item_to_python(report_item.children[0]))
            report_def = self._schema.reports.get(rptid)
            report_name = report_def.name if report_def else rptid or f"report_{report_index}"
            values_parent = report_item.children[1]
            value_items = values_parent.children if values_parent.type == values_parent.type.LIST else [values_parent]
            vid_sequence = report_def.vids if report_def else []

            report = CollectionEventReport(rptid=rptid, name=report_name)
            for value_index, value_item in enumerate(value_items, start=1):
                vid = vid_sequence[value_index - 1] if value_index - 1 < len(vid_sequence) else ""
                var_def = self._schema.variables.get(vid)
                value_name = var_def.name if var_def else (f"vid_{vid}" if vid else f"value_{value_index}")
                value = CollectionEventValue(
                    vid=vid,
                    name=value_name,
                    value=_item_to_python(value_item),
                    item_type=SECSTypeInfo.get_name(value_item.type),
                )
                report.values.append(value)
                payload.fields[value_name] = value.value

            payload.reports.append(report)

        return payload
