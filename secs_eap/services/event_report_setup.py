"""
Build S2F33/S2F35/S2F37 payloads from collection event config.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from secs_driver.src.secs_message import SECSItem

from .collection_events import CollectionEventSchema


@dataclass
class EventReportSetupOptions:
    data_id_type: str = "U4"
    ceid_type: str = "U4"
    rptid_type: str = "U4"
    vid_type: str = "U4"
    clear_data_id: int = 0
    define_data_id: int = 1
    link_data_id: int = 1
    enable_mode: str = "all"


@dataclass
class EventReportCommand:
    stream: int
    function: int
    name: str
    items: List[SECSItem]
    expected_reply_sf: str


class EventReportSetupBuilder:
    """Translate CEID/RPTID/VID config into SECS setup messages."""

    def __init__(self, raw_config: Optional[Dict[str, Any]] = None):
        self._raw_config = raw_config or {}
        self._schema = CollectionEventSchema.from_dict(self._raw_config)
        self._options = self._build_options(self._raw_config)

    @property
    def schema(self) -> CollectionEventSchema:
        return self._schema

    @property
    def options(self) -> EventReportSetupOptions:
        return self._options

    @classmethod
    def _build_options(cls, raw_config: Dict[str, Any]) -> EventReportSetupOptions:
        id_types = raw_config.get("id_types", {}) or {}
        report_setup = raw_config.get("report_setup", raw_config.get("setup", {})) or {}
        return EventReportSetupOptions(
            data_id_type=str(id_types.get("data_id", "U4")).upper(),
            ceid_type=str(id_types.get("ceid", "U4")).upper(),
            rptid_type=str(id_types.get("rptid", "U4")).upper(),
            vid_type=str(id_types.get("vid", "U4")).upper(),
            clear_data_id=cls._to_int(report_setup.get("clear_data_id", 0)),
            define_data_id=cls._to_int(report_setup.get("define_data_id", 1)),
            link_data_id=cls._to_int(report_setup.get("link_data_id", 1)),
            enable_mode=str(report_setup.get("enable_mode", "all")).lower(),
        )

    @staticmethod
    def _to_int(value: Any) -> int:
        if value is None or value == "":
            return 0
        if isinstance(value, int):
            return value
        return int(str(value), 0)

    @classmethod
    def _build_typed_id(cls, type_name: str, value: Any) -> SECSItem:
        numeric_value = cls._to_int(value)
        if type_name == "U1":
            return SECSItem.uint1(numeric_value)
        if type_name == "U2":
            return SECSItem.uint2(numeric_value)
        if type_name == "U4":
            return SECSItem.uint4(numeric_value)
        if type_name == "I1":
            return SECSItem.int1(numeric_value)
        if type_name == "I2":
            return SECSItem.int2(numeric_value)
        if type_name == "I4":
            return SECSItem.int4(numeric_value)
        raise ValueError(f"Unsupported SECS integer type: {type_name}")

    def build_commands(self, enable_mode: Optional[str] = None) -> List[EventReportCommand]:
        mode = (enable_mode or self._options.enable_mode or "all").lower()
        commands = [
            self._build_disable_all_events(),
            self._build_clear_links(),
            self._build_clear_reports(),
        ]

        if self._schema.reports:
            commands.append(self._build_define_reports())

        if self._linked_event_ids():
            commands.append(self._build_link_reports())

        if mode != "none":
            commands.append(self._build_enable_events(mode))

        return commands

    def _build_disable_all_events(self) -> EventReportCommand:
        return EventReportCommand(
            stream=2,
            function=37,
            name="disable_all_events",
            items=[
                SECSItem.list_([
                    SECSItem.boolean(False),
                    SECSItem.list_([]),
                ])
            ],
            expected_reply_sf="S2F38",
        )

    def _build_clear_links(self) -> EventReportCommand:
        return EventReportCommand(
            stream=2,
            function=35,
            name="clear_event_report_links",
            items=[
                SECSItem.list_([
                    self._build_typed_id(self._options.data_id_type, self._options.clear_data_id),
                    SECSItem.list_([]),
                ])
            ],
            expected_reply_sf="S2F36",
        )

    def _build_clear_reports(self) -> EventReportCommand:
        return EventReportCommand(
            stream=2,
            function=33,
            name="clear_reports",
            items=[
                SECSItem.list_([
                    self._build_typed_id(self._options.data_id_type, self._options.clear_data_id),
                    SECSItem.list_([]),
                ])
            ],
            expected_reply_sf="S2F34",
        )

    def _build_define_reports(self) -> EventReportCommand:
        report_items: List[SECSItem] = []
        for report in self._schema.reports.values():
            vid_items = [
                self._build_typed_id(self._options.vid_type, vid)
                for vid in report.vids
            ]
            report_items.append(
                SECSItem.list_([
                    self._build_typed_id(self._options.rptid_type, report.rptid),
                    SECSItem.list_(vid_items),
                ])
            )

        return EventReportCommand(
            stream=2,
            function=33,
            name="define_reports",
            items=[
                SECSItem.list_([
                    self._build_typed_id(self._options.data_id_type, self._options.define_data_id),
                    SECSItem.list_(report_items),
                ])
            ],
            expected_reply_sf="S2F34",
        )

    def _build_link_reports(self) -> EventReportCommand:
        event_items: List[SECSItem] = []
        for event in self._schema.events.values():
            if not event.rptids:
                continue
            report_items = [
                self._build_typed_id(self._options.rptid_type, rptid)
                for rptid in event.rptids
            ]
            event_items.append(
                SECSItem.list_([
                    self._build_typed_id(self._options.ceid_type, event.ceid),
                    SECSItem.list_(report_items),
                ])
            )

        return EventReportCommand(
            stream=2,
            function=35,
            name="link_event_reports",
            items=[
                SECSItem.list_([
                    self._build_typed_id(self._options.data_id_type, self._options.link_data_id),
                    SECSItem.list_(event_items),
                ])
            ],
            expected_reply_sf="S2F36",
        )

    def _build_enable_events(self, mode: str) -> EventReportCommand:
        ceid_items: List[SECSItem] = []
        if mode == "selected":
            ceid_items = [
                self._build_typed_id(self._options.ceid_type, event.ceid)
                for event in self._schema.events.values()
            ]
        elif mode != "all":
            raise ValueError(f"Unsupported enable_mode: {mode}")

        return EventReportCommand(
            stream=2,
            function=37,
            name=f"enable_{mode}_events",
            items=[
                SECSItem.list_([
                    SECSItem.boolean(True),
                    SECSItem.list_(ceid_items),
                ])
            ],
            expected_reply_sf="S2F38",
        )

    def _linked_event_ids(self) -> List[Tuple[str, List[str]]]:
        linked: List[Tuple[str, List[str]]] = []
        for event in self._schema.events.values():
            if event.rptids:
                linked.append((event.ceid, list(event.rptids)))
        return linked
