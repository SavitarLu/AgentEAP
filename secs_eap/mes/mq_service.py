"""
IBM MQ service wrapper for MES transactions.
"""

from dataclasses import dataclass, field
import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from secs_driver.src.logging_utils import format_tagged_block

from .tx.apvryope import APVRYOPERequest, APVRYOPEResponse
from .tx_registry import get_tx_response_type, get_tx_route


logger = logging.getLogger(__name__)


def _load_mq_client():
    """Lazy-load the official IBM MQ Python client."""
    try:
        import ibmmq as mq  # type: ignore
    except Exception as exc:
        raise RuntimeError("ibmmq is required for IBM MQ integration") from exc
    return mq


def _apply_client_channel_type(mq, cd) -> None:
    """
    Set client channel type if the installed MQ binding exposes the constant.

    In some ibmmq builds, `MQCHT_CLNTCONN` is not exported from `CMQC`
    even though the rest of the client API is available.
    """
    constant = None
    for module_name in ("CMQC", "CMQXC", "CMQCFC"):
        module = getattr(mq, module_name, None)
        if module is not None:
            constant = getattr(module, "MQCHT_CLNTCONN", None)
            if constant is not None:
                break

    if constant is None:
        logger.debug(
            "MQCHT_CLNTCONN not exported by ibmmq; skip explicit ChannelType assignment"
        )
        return

    try:
        cd.ChannelType = constant
    except Exception as exc:
        logger.debug("Failed to assign MQ client ChannelType: %s", exc)


def _get_mq_constant(mq, name: str):
    """Lookup an MQ constant across common constant modules."""
    for module_name in ("CMQC", "CMQXC", "CMQCFC"):
        module = getattr(mq, module_name, None)
        if module is not None and hasattr(module, name):
            return getattr(module, name)
    return None


def _set_if_present(obj, attr: str, value) -> None:
    """Assign an MQ structure field only when the binding exposes it."""
    if value is None or not hasattr(obj, attr):
        return
    try:
        setattr(obj, attr, value)
    except Exception as exc:
        logger.debug("Failed to set MQ field %s: %s", attr, exc)


def _format_mq_id(value) -> str:
    """Render MQ binary identifiers as uppercase hex for logs."""
    if value is None:
        return ""
    try:
        raw = bytes(value)
    except Exception:
        return str(value)
    return raw.hex().upper()


def _format_json_for_log(payload) -> str:
    """Pretty-print JSON payloads for readable logs."""
    try:
        return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False)
    except Exception:
        return str(payload)


def _log_json_block(title: str, payload) -> None:
    logger.info(
        "%s",
        format_tagged_block(f"{title}\n{_format_json_for_log(payload)}", "H"),
        extra={"raw_log": True},
    )


def _is_no_msg_available(exc: Exception) -> bool:
    """Best-effort detection of MQRC_NO_MSG_AVAILABLE across bindings."""
    reason = getattr(exc, "reason", None)
    if reason == 2033:
        return True
    return "2033" in str(exc) or "MQRC_NO_MSG_AVAILABLE" in str(exc)


@dataclass
class MesMqConfig:
    # Legacy single-endpoint mode
    host: str = ""
    port: int = 0
    channel: str = ""
    queue_manager: str = ""
    request_queue: str = ""
    reply_queue: str = ""

    # Cluster mode
    mq_conn_list: Dict[str, str] = field(default_factory=dict)
    mq_listener: Dict[str, str] = field(default_factory=dict)
    mq_sender: Dict[str, str] = field(default_factory=dict)  # name -> QM alias (e.g. MQ1 -> QM1)

    user: str = ""
    password: str = ""
    timeout_ms: int = 5000
    ccsid: int = 1208

    @classmethod
    def from_dict(cls, cfg: Dict) -> "MesMqConfig":
        return cls(
            host=str(cfg.get("host", "")),
            port=int(cfg.get("port", 0) or 0),
            channel=str(cfg.get("channel", "")),
            queue_manager=str(cfg.get("queue_manager", "")),
            request_queue=str(cfg.get("request_queue", "")),
            reply_queue=str(cfg.get("reply_queue", "")),
            mq_conn_list=dict(cfg.get("mq_conn_list", {}) or {}),
            mq_listener=dict(cfg.get("mq_listener", {}) or {}),
            mq_sender=dict(cfg.get("mq_sender", {}) or {}),
            user=str(cfg.get("user", "")),
            password=str(cfg.get("password", "")),
            timeout_ms=int(cfg.get("timeout_ms", 5000)),
            ccsid=int(cfg.get("ccsid", 1208)),
        )


class MesMqService:
    """
    Minimal synchronous MQ client for Python-based MES TX codecs.
    """

    def __init__(self, config: MesMqConfig):
        self._config = config
        self._qmgr_by_alias: Dict[str, object] = {}

    @property
    def is_connected(self) -> bool:
        return bool(self._qmgr_by_alias)

    def connect(self) -> None:
        _load_mq_client()

        # Pre-connect all cluster aliases if defined, else fallback to legacy single endpoint.
        if self._config.mq_conn_list:
            for alias in self._config.mq_conn_list:
                self._get_or_connect_qmgr(alias)
            logger.info("MES MQ cluster connected aliases=%s", ",".join(self._qmgr_by_alias.keys()))
            return

        if not (self._config.queue_manager and self._config.channel and self._config.host and self._config.port):
            raise RuntimeError("MES MQ config incomplete")

        # Treat legacy as alias 'LEGACY'.
        self._config.mq_conn_list = {
            "LEGACY": f"{self._config.queue_manager}/{self._config.channel}/{self._config.host}({self._config.port})"
        }
        if self._config.request_queue:
            self._config.mq_sender.setdefault("MQ1", "LEGACY")
        if self._config.reply_queue:
            self._config.mq_listener.setdefault("LEGACY", f"LEGACY/{self._config.reply_queue}/")
        self._get_or_connect_qmgr("LEGACY")
        logger.info("MES MQ connected in legacy mode")

    def close(self) -> None:
        for alias, qmgr in list(self._qmgr_by_alias.items()):
            try:
                qmgr.disconnect()
            except Exception:
                pass
            logger.info("MES MQ disconnected alias=%s", alias)
        self._qmgr_by_alias.clear()

    def execute_tx(self, tx_name: str, request: Any) -> Any:
        # Avoid using cached qmgr across threads; create a fresh connection per call.
        if not self._config.mq_conn_list:
            raise RuntimeError("MES MQ not connected/configured (mq_conn_list empty)")

        mq = _load_mq_client()

        tx_name = str(tx_name or getattr(request, "trx_id", "") or "").strip().upper()
        if not tx_name:
            raise RuntimeError("TX name is required")
        if not hasattr(request, "to_payload"):
            raise RuntimeError(f"{tx_name} request object must provide to_payload()")
        tx_route = get_tx_route(tx_name)
        conn_alias = self._resolve_sender_alias()
        request_queue = tx_route.request_queue
        listener_endpoints = self._resolve_listeners(conn_alias)
        primary_listener = listener_endpoints[0]
        _, reply_queue, reply_app_id = self._parse_endpoint(primary_listener)
        qmgr_name, _, _ = self._parse_conn_spec(self._config.mq_conn_list[conn_alias])
        reply_to_qmgr = qmgr_name if len(listener_endpoints) == 1 else None
        qmgr = None
        req_q = None
        reply_handles = []
        request_md = None
        last_reply_md = None
        try:
            qmgr = self._connect_qmgr_fresh(conn_alias)
            req_q = mq.Queue(qmgr, request_queue)

            payload = request.to_payload()
            msg = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            _log_json_block("MQ TX payload(JSON):", payload)
            request_md = mq.MD()
            pmo = mq.PMO()
            _set_if_present(
                pmo,
                "Options",
                (_get_mq_constant(mq, "MQPMO_NEW_MSG_ID") or 0)
                | (_get_mq_constant(mq, "MQPMO_FAIL_IF_QUIESCING") or 0),
            )
            _set_if_present(request_md, "ReplyToQ", reply_queue)
            _set_if_present(request_md, "ReplyToQMgr", reply_to_qmgr)
            _set_if_present(request_md, "ApplIdentityData", reply_app_id[:32] if reply_app_id else None)
            user_id = getattr(request, "user_id", "") or ""
            _set_if_present(request_md, "UserIdentifier", user_id[:12] if user_id else None)
            _set_if_present(request_md, "CodedCharSetId", self._config.ccsid)
            _set_if_present(request_md, "Format", _get_mq_constant(mq, "MQFMT_STRING"))
            _set_if_present(request_md, "MsgType", _get_mq_constant(mq, "MQMT_REQUEST"))

            req_q.put(msg, request_md, pmo)
            request_msg_id = getattr(request_md, "MsgId", None)
            request_correl_id = getattr(request_md, "CorrelId", None)
            logger.info(
                "MQ TX sent(JSON): %s qm_alias=%s req_queue=%s reply_queue=%s reply_qmgr=%s "
                "eqpt_id=%s crr_id=%s msg_id=%s correl_id=%s app_id=%s listeners=%s",
                tx_name,
                conn_alias,
                request_queue,
                reply_queue,
                reply_to_qmgr or "",
                getattr(request, "eqpt_id", ""),
                getattr(request, "crr_id", ""),
                _format_mq_id(request_msg_id),
                _format_mq_id(request_correl_id),
                reply_app_id,
                ",".join(
                    f"{alias}:{queue}"
                    for alias, queue, _app in (self._parse_endpoint(ep) for ep in listener_endpoints)
                ),
            )

            reply_handles = self._open_reply_handles(mq, listener_endpoints)
            deadline = time.monotonic() + (self._config.timeout_ms / 1000.0)
            reply_bytes, last_reply_md, reply_alias, reply_queue = self._wait_for_reply(
                mq=mq,
                tx_name=tx_name,
                reply_handles=reply_handles,
                request_msg_id=request_msg_id,
                deadline=deadline,
            )
            raw_payload = reply_bytes.decode("utf-8", errors="ignore")
            try:
                reply_obj = json.loads(raw_payload)
            except Exception as exc:
                raise RuntimeError(f"{tx_name} reply is not valid JSON: {exc}") from exc

            if not isinstance(reply_obj, dict):
                raise RuntimeError(f"{tx_name} reply JSON root must be object")

            response = self._decode_tx_response(tx_name, reply_obj, raw_payload)
            _log_json_block("MQ TX reply(JSON):", reply_obj)
            logger.info(
                "MQ TX reply: %s qm_alias=%s reply_queue=%s rtn_code=%s lot_id=%s msg_id=%s correl_id=%s",
                tx_name,
                reply_alias,
                reply_queue,
                getattr(response, "rtn_code", ""),
                getattr(response, "lot_id", ""),
                _format_mq_id(getattr(last_reply_md, "MsgId", None)),
                _format_mq_id(getattr(last_reply_md, "CorrelId", None)),
            )
            return response
        except Exception as exc:
            logger.error(
                "MQ TX failed: %s conn_alias=%s req_queue=%s reply_queue=%s reply_qmgr=%s "
                "eqpt_id=%s crr_id=%s request_msg_id=%s wait_msg_id=%s app_id=%s error=%s",
                tx_name,
                conn_alias,
                request_queue,
                reply_queue,
                reply_to_qmgr or "",
                getattr(request, "eqpt_id", ""),
                getattr(request, "crr_id", ""),
                _format_mq_id(getattr(request_md, "MsgId", None) if request_md else None),
                _format_mq_id(request_msg_id if 'request_msg_id' in locals() else None),
                reply_app_id,
                exc,
            )
            raise
        finally:
            try:
                if req_q:
                    req_q.close()
            except Exception:
                pass
            try:
                for reply_qmgr, rep_q, _reply_alias, _reply_queue in reply_handles:
                    try:
                        rep_q.close()
                    except Exception:
                        pass
                    try:
                        reply_qmgr.disconnect()
                    except Exception:
                        pass
            except Exception:
                pass
            try:
                if qmgr:
                    qmgr.disconnect()
            except Exception:
                pass

    def query_lot_apvryope(self, request: APVRYOPERequest) -> APVRYOPEResponse:
        return self.execute_tx("APVRYOPE", request)

    @staticmethod
    def _decode_tx_response(tx_name: str, payload: Dict[str, Any], raw_payload: str) -> Any:
        response_type = get_tx_response_type(tx_name)
        if response_type and hasattr(response_type, "from_payload"):
            return response_type.from_payload(payload, raw_payload=raw_payload)
        return payload

    def _resolve_sender_alias(self) -> str:
        if self._config.mq_sender:
            first = next(iter(self._config.mq_sender.values()))
            if first:
                return first
        # Fallback: use first listener alias.
        if self._config.mq_listener:
            endpoint = next(iter(self._config.mq_listener.values()))
            alias, _queue, _eqpt = self._parse_endpoint(endpoint)
            return alias
        raise RuntimeError("No MQ sender alias configured")

    def _resolve_listener(self, conn_alias: str) -> str:
        for _name, endpoint in self._config.mq_listener.items():
            ep_alias, _queue, _eqpt = self._parse_endpoint(endpoint)
            if ep_alias == conn_alias:
                return endpoint
        if self._config.mq_listener:
            return next(iter(self._config.mq_listener.values()))
        raise RuntimeError(f"No MQ listener configured for alias={conn_alias}")

    def _resolve_listeners(self, conn_alias: str) -> List[str]:
        """Return reply listener endpoints, prioritizing the sender alias."""
        matched = []
        others = []
        for endpoint in self._config.mq_listener.values():
            ep_alias, _queue, _eqpt = self._parse_endpoint(endpoint)
            if ep_alias == conn_alias:
                matched.append(endpoint)
            else:
                others.append(endpoint)

        listeners = matched + others
        if listeners:
            return listeners
        raise RuntimeError(f"No MQ listener configured for alias={conn_alias}")

    def _get_or_connect_qmgr(self, alias: str):
        if alias in self._qmgr_by_alias:
            return self._qmgr_by_alias[alias]
        return self._connect_qmgr(alias, cache_result=True)

    def _connect_qmgr(self, alias: str, cache_result: bool):
        """Connect one queue manager, optionally caching the handle by alias."""
        mq = _load_mq_client()

        spec = self._config.mq_conn_list.get(alias, "")
        if not spec:
            raise RuntimeError(f"MQ connection alias not found: {alias}")

        qmgr_name, channel, conn_name = self._parse_conn_spec(spec)
        cd = mq.CD()
        cd.ChannelName = channel
        cd.ConnectionName = conn_name
        _apply_client_channel_type(mq, cd)
        sco = mq.SCO()

        if self._config.user:
            qmgr = mq.QueueManager(None)
            try:
                qmgr.connect_with_options(
                    qmgr_name,
                    user=self._config.user,
                    password=self._config.password,
                    cd=cd,
                    sco=sco,
                )
            except Exception as exc:
                logger.error(
                    "MES MQ connect failed (alias=%s) qmgr_name=%s channel=%s conn_name=%s user_provided=yes error=%s",
                    alias,
                    qmgr_name,
                    channel,
                    conn_name,
                    exc,
                )
                raise
        else:
            try:
                qmgr = mq.connect(qmgr_name, channel, conn_name)
            except Exception as exc:
                logger.error(
                    "MES MQ connect failed (alias=%s) qmgr_name=%s channel=%s conn_name=%s user_provided=no error=%s",
                    alias,
                    qmgr_name,
                    channel,
                    conn_name,
                    exc,
                )
                raise

        if cache_result:
            self._qmgr_by_alias[alias] = qmgr
        logger.info(
            "MES MQ connected alias=%s qmgr=%s cached=%s",
            alias,
            qmgr_name,
            cache_result,
        )
        return qmgr

    def _connect_qmgr_fresh(self, alias: str):
        """
        Create a new QueueManager instance for a single operation.
        This avoids reusing cached qmgr objects across asyncio worker threads.
        """
        return self._connect_qmgr(alias, cache_result=False)

    def _open_reply_handles(self, mq, listener_endpoints: List[str]):
        """Open reply queues for all configured listeners."""
        handles = []
        for endpoint in listener_endpoints:
            reply_alias, reply_queue, _reply_app_id = self._parse_endpoint(endpoint)
            reply_qmgr = self._connect_qmgr_fresh(reply_alias)
            rep_q = mq.Queue(reply_qmgr, reply_queue)
            handles.append((reply_qmgr, rep_q, reply_alias, reply_queue))
        return handles

    def _wait_for_reply(
        self,
        mq,
        tx_name: str,
        reply_handles,
        request_msg_id,
        deadline: float,
    ):
        """Poll all listener queues until one returns the expected reply."""
        match_msg_id = _format_mq_id(request_msg_id)
        match_correl_opt = _get_mq_constant(mq, "MQMO_MATCH_CORREL_ID")
        match_msg_opt = _get_mq_constant(mq, "MQMO_MATCH_MSG_ID")
        match_specs = []
        if match_msg_opt is not None:
            match_specs.append(("msg_id", "MsgId", match_msg_opt))
        if match_correl_opt is not None:
            match_specs.append(("correl_id", "CorrelId", match_correl_opt))
        if not match_specs:
            raise RuntimeError("IBM MQ binding does not expose reply match options")

        while True:
            remaining_ms = int(max(0.0, deadline - time.monotonic()) * 1000)
            if remaining_ms <= 0:
                raise TimeoutError(
                    f"Timed out waiting MQ reply for msg_id={match_msg_id}"
                )

            wait_slice_ms = min(remaining_ms, 1000)
            last_no_msg_exc = None
            for _reply_qmgr, rep_q, reply_alias, reply_queue in reply_handles:
                for match_name, match_attr, match_option in match_specs:
                    reply_md = mq.MD()
                    if match_attr == "MsgId":
                        _set_if_present(reply_md, "MsgId", request_msg_id)
                    elif match_attr == "CorrelId":
                        _set_if_present(reply_md, "MsgId", _get_mq_constant(mq, "MQMI_NONE"))
                        _set_if_present(reply_md, "CorrelId", request_msg_id)

                    gmo = mq.GMO()
                    gmo.Options = mq.CMQC.MQGMO_WAIT | mq.CMQC.MQGMO_FAIL_IF_QUIESCING
                    gmo.WaitInterval = wait_slice_ms
                    if hasattr(gmo, "MatchOptions"):
                        _set_if_present(gmo, "MatchOptions", match_option)

                    logger.info(
                        "MQ TX waiting reply: %s qm_alias=%s reply_queue=%s wait_ms=%s "
                        "match_type=%s match_value=%s",
                        tx_name,
                        reply_alias,
                        reply_queue,
                        wait_slice_ms,
                        match_name,
                        _format_mq_id(getattr(reply_md, match_attr, None)),
                    )
                    try:
                        reply_bytes = rep_q.get(None, reply_md, gmo)
                        return reply_bytes, reply_md, reply_alias, reply_queue
                    except Exception as exc:
                        if _is_no_msg_available(exc):
                            last_no_msg_exc = exc
                            continue
                        raise

            if last_no_msg_exc is not None and time.monotonic() >= deadline:
                raise last_no_msg_exc

    @staticmethod
    def _parse_conn_spec(spec: str) -> Tuple[str, str, str]:
        # format: "MESDEVGW1/MESDEVGW1.SVRCONN/95.40.166.36(51419)"
        parts = spec.split("/", 2)
        if len(parts) != 3:
            raise RuntimeError(f"Invalid mq_conn_list spec: {spec}")
        qmgr_name, channel, conn_name = parts
        if not re.match(r".+\(\d+\)$", conn_name):
            raise RuntimeError(f"Invalid connection name in spec: {spec}")
        return qmgr_name.strip(), channel.strip(), conn_name.strip()

    @staticmethod
    def _parse_endpoint(endpoint: str) -> Tuple[str, str, str]:
        # format: "QM1/F01.TCS.SHARE/E_CLN_01"
        parts = endpoint.split("/", 2)
        if len(parts) != 3:
            raise RuntimeError(f"Invalid endpoint spec: {endpoint}")
        return parts[0].strip(), parts[1].strip(), parts[2].strip()
