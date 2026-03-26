"""
IBM MQ service wrapper for MES transactions.
"""

from dataclasses import dataclass, field
import json
import logging
import re
from typing import Dict, Optional, Tuple

from .apvryope import APVRYOPERequest, APVRYOPEResponse
from .tx_registry import get_tx_route


logger = logging.getLogger(__name__)


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
    Minimal synchronous MQ client for APVRYOPE.
    """

    def __init__(self, config: MesMqConfig):
        self._config = config
        self._qmgr_by_alias: Dict[str, object] = {}

    @property
    def is_connected(self) -> bool:
        return bool(self._qmgr_by_alias)

    def connect(self) -> None:
        try:
            import pymqi  # type: ignore
        except Exception as exc:
            raise RuntimeError("pymqi is required for IBM MQ integration") from exc

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

    def query_lot_apvryope(self, request: APVRYOPERequest) -> APVRYOPEResponse:
        # Avoid using cached qmgr across threads; create a fresh connection per call.
        if not self._config.mq_conn_list:
            raise RuntimeError("MES MQ not connected/configured (mq_conn_list empty)")

        import pymqi  # type: ignore

        tx_name = "APVRYOPE"
        tx_route = get_tx_route(tx_name)
        conn_alias = self._resolve_sender_alias()
        request_queue = tx_route.request_queue
        listener_endpoint = self._resolve_listener(conn_alias)
        _, reply_queue, _ = self._parse_endpoint(listener_endpoint)
        qmgr = None
        req_q = None
        rep_q = None
        try:
            qmgr = self._connect_qmgr_fresh(conn_alias)
            req_q = pymqi.Queue(qmgr, request_queue)
            rep_q = pymqi.Queue(qmgr, reply_queue)

            payload = request.to_payload()
            msg = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            md = pymqi.MD()
            pmo = pymqi.PMO()
            gmo = pymqi.GMO()
            gmo.Options = pymqi.CMQC.MQGMO_WAIT | pymqi.CMQC.MQGMO_FAIL_IF_QUIESCING
            gmo.WaitInterval = self._config.timeout_ms

            req_q.put(msg, md, pmo)
            logger.info(
                "MQ TX sent(JSON): %s qm_alias=%s req_queue=%s reply_queue=%s eqpt_id=%s crr_id=%s",
                tx_name,
                conn_alias,
                request_queue,
                reply_queue,
                request.eqpt_id,
                request.crr_id,
            )

            reply_bytes = rep_q.get(None, md, gmo)
            raw_payload = reply_bytes.decode("utf-8", errors="ignore")
            try:
                reply_obj = json.loads(raw_payload)
            except Exception as exc:
                raise RuntimeError(f"APVRYOPE reply is not valid JSON: {exc}") from exc

            if not isinstance(reply_obj, dict):
                raise RuntimeError("APVRYOPE reply JSON root must be object")

            response = APVRYOPEResponse.from_payload(reply_obj, raw_payload=raw_payload)
            logger.info(
                "MQ TX reply: APVRYOPE rtn_code=%s lot_id=%s",
                response.rtn_code,
                response.lot_id,
            )
            return response
        except Exception as exc:
            logger.error(
                "MQ TX failed: %s conn_alias=%s req_queue=%s reply_queue=%s eqpt_id=%s crr_id=%s error=%s",
                tx_name,
                conn_alias,
                request_queue,
                reply_queue,
                request.eqpt_id,
                request.crr_id,
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
                if rep_q:
                    rep_q.close()
            except Exception:
                pass
            try:
                if qmgr:
                    qmgr.disconnect()
            except Exception:
                pass

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

    def _get_or_connect_qmgr(self, alias: str):
        if alias in self._qmgr_by_alias:
            return self._qmgr_by_alias[alias]

        spec = self._config.mq_conn_list.get(alias, "")
        if not spec:
            raise RuntimeError(f"MQ connection alias not found: {alias}")

        qmgr_name, channel, conn_name = self._parse_conn_spec(spec)
        import pymqi  # type: ignore

        cd = pymqi.CD()
        cd.ChannelName = channel
        cd.ConnectionName = conn_name
        cd.ChannelType = pymqi.CMQC.MQCHT_CLNTCONN
        sco = pymqi.SCO()

        if self._config.user:
            qmgr = pymqi.QueueManager(None)
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
                qmgr = pymqi.connect(qmgr_name, channel, conn_name)
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

        self._qmgr_by_alias[alias] = qmgr
        logger.info("MES MQ connected alias=%s qmgr=%s", alias, qmgr_name)
        return qmgr

    def _connect_qmgr_fresh(self, alias: str):
        """
        Create a new QueueManager instance for a single operation.
        This avoids reusing cached qmgr objects across asyncio worker threads.
        """
        spec = self._config.mq_conn_list.get(alias, "")
        if not spec:
            raise RuntimeError(f"MQ connection alias not found: {alias}")

        qmgr_name, channel, conn_name = self._parse_conn_spec(spec)
        import pymqi  # type: ignore

        cd = pymqi.CD()
        cd.ChannelName = channel
        cd.ConnectionName = conn_name
        cd.ChannelType = pymqi.CMQC.MQCHT_CLNTCONN
        sco = pymqi.SCO()

        if self._config.user:
            qmgr = pymqi.QueueManager(None)
            qmgr.connect_with_options(
                qmgr_name,
                user=self._config.user,
                password=self._config.password,
                cd=cd,
                sco=sco,
            )
        else:
            qmgr = pymqi.connect(qmgr_name, channel, conn_name)

        return qmgr

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

