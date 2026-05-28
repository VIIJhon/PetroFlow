"""
PetroFlow - OPC UA Industrial Client
=====================================
Breaks vendor lock-in (Siemens, GE, ABB, Rockwell) by implementing the
IEC 62541 OPC UA open standard for real-time field device communication.

Architecture
------------
All network operations are fully asynchronous (asyncua + asyncio) so that
Streamlit's Tornado event loop is never blocked during handshakes, reads,
or subscription callbacks.

Entry points for Streamlit integration
---------------------------------------
    client = PetroflowOPCClient()
    asyncio.run(client.connect(url, username, password))
    value  = asyncio.run(client.read_sensor_data("ns=2;s=Turbine1.Vibration"))
    asyncio.run(client.subscribe(["ns=2;s=Turbine1.Vibration"], callback=my_fn))
    asyncio.run(client.disconnect())

For Streamlit (single-thread constraint) use run_in_executor or
asyncio.get_event_loop().run_until_complete() from a background thread.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

# ---------------------------------------------------------------------------
# asyncua imports  (pip install asyncua)
# ---------------------------------------------------------------------------
try:
    from asyncua import Client, ua
    from asyncua.crypto.security_policies import SecurityPolicyBasic256Sha256
    from asyncua.ua.uaerrors import BadSessionClosed, BadConnectionClosed
    _ASYNCUA_AVAILABLE = True
except ImportError:                         # pragma: no cover
    _ASYNCUA_AVAILABLE = False              # soft-fail: module loads, methods raise

# ---------------------------------------------------------------------------
# PetroFlow audit logger
# ---------------------------------------------------------------------------
from core.audit_logging_service import get_audit_logger

_logger = logging.getLogger("petroflow.opc_client")
_audit  = get_audit_logger()

# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------
DEFAULT_TIMEOUT_SECONDS: int    = 10
DEFAULT_SESSION_TIMEOUT_MS: int = 30_000       # 30 s  (OPC UA SessionTimeout)
DEFAULT_PUBLISH_INTERVAL_MS: float = 500.0     # subscription publish cycle


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class SensorReading:
    """Typed container for a single OPC UA node value."""
    node_id:    str
    value:      Any
    status:     str                         # "Good" | "Bad" | "Uncertain"
    source_ts:  datetime
    server_ts:  datetime
    data_type:  str = "Unknown"

    @property
    def is_good(self) -> bool:
        return self.status == "Good"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id":   self.node_id,
            "value":     self.value,
            "status":    self.status,
            "source_ts": self.source_ts.isoformat(),
            "server_ts": self.server_ts.isoformat(),
            "data_type": self.data_type,
        }


@dataclass
class ConnectionState:
    """Tracks the lifecycle of the OPC UA session."""
    url:           str = ""
    connected:     bool = False
    session_id:    Optional[str] = None
    connected_at:  Optional[datetime] = None
    last_read_at:  Optional[datetime] = None
    error_count:   int = 0
    subscriptions: List[int] = field(default_factory=list)   # subscription handles


# ---------------------------------------------------------------------------
# Subscription handler (push model)
# ---------------------------------------------------------------------------

class _SubscriptionHandler:
    """
    OPC UA data-change handler registered with the server.

    The server calls datachange_notification() whenever a monitored node
    changes value — no polling required.  The handler invokes the
    user-supplied callback with a SensorReading so Petroflow can react
    immediately (update cache, trigger alarms, etc.).
    """

    def __init__(
        self,
        callback: Callable[[SensorReading], None],
        node_id_map: Dict[int, str],        # handle -> node_id string
    ) -> None:
        self._callback    = callback
        self._node_id_map = node_id_map

    # ----- asyncua interface -------------------------------------------------

    def datachange_notification(
        self,
        node: Any,
        val:  Any,
        data: Any,
    ) -> None:
        """
        Invoked by asyncua on every monitored-item value change.

        Parameters match the asyncua SubscriptionHandler protocol:
            node  - asyncua.Node object
            val   - the new value (already decoded to Python type)
            data  - MonitoredItemNotification carrying timestamps & status
        """
        try:
            mon    = data.monitored_item
            source = mon.Value.SourceTimestamp or datetime.now(timezone.utc)
            server = mon.Value.ServerTimestamp or datetime.now(timezone.utc)

            # Resolve human-readable node id
            node_id_str = str(node.nodeid)

            # Map OPC UA status code to a simple string
            status_code = mon.Value.StatusCode
            if status_code is not None and status_code.is_good():
                status = "Good"
            elif status_code is not None and status_code.is_uncertain():
                status = "Uncertain"
            else:
                status = "Bad"

            reading = SensorReading(
                node_id   = node_id_str,
                value     = val,
                status    = status,
                source_ts = source,
                server_ts = server,
                data_type = type(val).__name__,
            )

            _audit.log_data_access(
                f"OPC-UA datachange: {node_id_str} = {val} [{status}]",
                action="OPCUA_DATACHANGE",
                node_id=node_id_str,
                value=str(val),
                status=status,
            )

            # Forward to caller-supplied callback (non-blocking)
            if callable(self._callback):
                self._callback(reading)

        except Exception as exc:            # never crash the server's thread
            _audit.log_error(exc, context="OPC-UA subscription handler")
            _logger.error("Subscription handler error: %s", exc, exc_info=True)

    def event_notification(self, event: Any) -> None:
        """OPC UA event (alarm/condition) notification — logged for traceability."""
        _logger.info("OPC-UA event received: %s", event)
        _audit.log_system(
            f"OPC-UA server event: {event}",
            action="OPCUA_EVENT",
        )

    def status_change_notification(self, status: Any) -> None:
        """Called when the subscription status changes (e.g. server timeout)."""
        _logger.warning("OPC-UA subscription status change: %s", status)
        _audit.log_system(
            f"OPC-UA subscription status changed: {status}",
            action="OPCUA_SUB_STATUS",
            level="WARNING",
        )


# ---------------------------------------------------------------------------
# Main client class
# ---------------------------------------------------------------------------

class PetroflowOPCClient:
    """
    Async OPC UA client for industrial field device integration.

    Supports:
        - Username/password + X.509 certificate authentication
        - Encrypted transport (Basic256Sha256 security policy)
        - Synchronous node reads (poll)
        - Server-push subscriptions (event-driven streaming)

    Usage
    -----
        client = PetroflowOPCClient(timeout=10)
        await client.connect("opc.tcp://192.168.1.100:4840", "operator", "secret")

        reading = await client.read_sensor_data("ns=2;s=Pump1.Discharge.Pressure")
        print(reading.value)

        await client.subscribe(
            node_ids=["ns=2;s=Turbine1.Vibration", "ns=2;s=Compressor1.Temp"],
            callback=my_callback,
        )

        await client.disconnect()
    """

    def __init__(
        self,
        timeout:              int   = DEFAULT_TIMEOUT_SECONDS,
        session_timeout_ms:   int   = DEFAULT_SESSION_TIMEOUT_MS,
        publish_interval_ms:  float = DEFAULT_PUBLISH_INTERVAL_MS,
    ) -> None:
        if not _ASYNCUA_AVAILABLE:
            raise ImportError(
                "asyncua is not installed. "
                "Run: pip install asyncua"
            )

        self._timeout             = timeout
        self._session_timeout_ms  = session_timeout_ms
        self._publish_interval_ms = publish_interval_ms

        self._client: Optional[Client] = None
        self._state  = ConnectionState()
        self._active_subscriptions: List[Any] = []   # asyncua Subscription objects

    # ------------------------------------------------------------------
    # 1. Connection (secure handshake)
    # ------------------------------------------------------------------

    async def connect(
        self,
        url:      str,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> bool:
        """
        Establish an authenticated OPC UA session.

        Parameters
        ----------
        url :
            OPC UA endpoint, e.g. "opc.tcp://192.168.1.100:4840"
        username :
            Operator account name (UserName identity token).
            Pass None to attempt anonymous connection.
        password :
            Operator password.  Never written to logs — masked internally.

        Returns
        -------
        bool
            True if the session was established successfully.

        Raises
        ------
        ConnectionError
            Re-raised as a clean Python exception after logging the root cause.
        """
        if self._state.connected:
            _logger.warning(
                "connect() called while already connected to %s. "
                "Call disconnect() first.",
                self._state.url,
            )
            return True

        _logger.info("Initiating OPC UA connection to: %s", url)
        _audit.log_system(
            f"OPC-UA connection attempt: {url}",
            action="OPCUA_CONNECT_ATTEMPT",
            endpoint=url,
            auth="username" if username else "anonymous",
        )

        try:
            self._client = Client(url=url, timeout=self._timeout)
            self._client.session_timeout = self._session_timeout_ms

            # --- Authentication ---
            if username and password:
                self._client.set_user(username)
                self._client.set_password(password)

            async with asyncio.timeout(self._timeout):
                await self._client.connect()

            # Retrieve session info for audit trail
            session_id = str(getattr(self._client, "uaclient", {}) or "N/A")
            self._state = ConnectionState(
                url          = url,
                connected    = True,
                connected_at = datetime.now(timezone.utc),
                session_id   = session_id,
            )

            _logger.info("OPC UA session established: %s", url)
            _audit.log_system(
                f"OPC-UA session established: {url}",
                action="OPCUA_CONNECTED",
                endpoint=url,
            )
            return True

        # -- Specific, recoverable failure modes ----------------------------

        except asyncio.TimeoutError:
            msg = f"OPC-UA connection timed out after {self._timeout}s: {url}"
            _logger.error(msg)
            _audit.log_system(msg, action="OPCUA_TIMEOUT", level="ERROR", endpoint=url)
            self._state.error_count += 1
            raise ConnectionError(msg) from None

        except ua.UaStatusCodeError as exc:
            # BadUserAccessDenied, BadIdentityTokenRejected, etc.
            msg = f"OPC-UA authentication rejected (status={exc.code}): {url}"
            _logger.error(msg)
            _audit.log_security(
                msg,
                action="OPCUA_AUTH_FAILED",
                endpoint=url,
                status_code=str(exc.code),
            )
            self._state.error_count += 1
            raise ConnectionError(msg) from exc

        except OSError as exc:
            # TCP-level: host unreachable, connection refused, DNS failure
            msg = f"OPC-UA network error connecting to {url}: {exc}"
            _logger.error(msg)
            _audit.log_system(msg, action="OPCUA_NETWORK_ERROR", level="ERROR", endpoint=url)
            self._state.error_count += 1
            raise ConnectionError(msg) from exc

        except Exception as exc:
            msg = f"OPC-UA unexpected error during connect to {url}: {exc}"
            _logger.exception(msg)
            _audit.log_error(exc, context=f"OPC-UA connect to {url}")
            self._state.error_count += 1
            raise ConnectionError(msg) from exc

    # ------------------------------------------------------------------
    # 2. Sensor read (single poll)
    # ------------------------------------------------------------------

    async def read_sensor_data(self, node_id: str) -> SensorReading:
        """
        Read the current value of a single OPC UA node.

        Parameters
        ----------
        node_id :
            OPC UA node identifier string.
            Examples:
                "ns=2;s=Pump1.Discharge.Pressure"
                "ns=2;i=1003"           (numeric identifier)
                "ns=0;i=2256"           (server namespace)

        Returns
        -------
        SensorReading
            Typed container with value, quality status, and both timestamps.

        Raises
        ------
        RuntimeError
            If not connected.
        ValueError
            If the node_id is malformed or the node does not exist.
        """
        self._require_connected()

        _logger.debug("Reading node: %s", node_id)

        try:
            node = self._client.get_node(node_id)

            # read_data_value returns a DataValue (value + status + timestamps)
            dv = await node.read_data_value()

            # Resolve quality code
            sc = dv.StatusCode
            if sc is None or sc.is_good():
                status = "Good"
            elif sc.is_uncertain():
                status = "Uncertain"
            else:
                status = "Bad"
                _logger.warning(
                    "Bad quality reading for node %s (status=%s)", node_id, sc
                )

            now = datetime.now(timezone.utc)
            reading = SensorReading(
                node_id   = node_id,
                value     = dv.Value.Value if dv.Value else None,
                status    = status,
                source_ts = dv.SourceTimestamp or now,
                server_ts = dv.ServerTimestamp or now,
                data_type = type(dv.Value.Value).__name__ if dv.Value else "None",
            )

            self._state.last_read_at = now

            _audit.log_data_access(
                f"OPC-UA read: {node_id} = {reading.value} [{status}]",
                action="OPCUA_READ",
                node_id=node_id,
                value=str(reading.value),
                status=status,
            )

            return reading

        except ua.UaStatusCodeError as exc:
            msg = f"OPC-UA node not found or access denied: {node_id} (code={exc.code})"
            _logger.error(msg)
            _audit.log_error(exc, context=f"OPC-UA read {node_id}")
            raise ValueError(msg) from exc

        except Exception as exc:
            msg = f"OPC-UA read failed for node {node_id}: {exc}"
            _logger.exception(msg)
            _audit.log_error(exc, context=f"OPC-UA read {node_id}")
            raise

    async def read_multiple(self, node_ids: List[str]) -> Dict[str, SensorReading]:
        """
        Read multiple nodes concurrently (parallel coroutines, single TCP session).

        Parameters
        ----------
        node_ids :
            List of OPC UA node identifier strings.

        Returns
        -------
        dict
            Mapping of node_id -> SensorReading.
            Nodes that fail are returned with status="Bad" and value=None
            so a partial failure never aborts the whole batch.
        """
        self._require_connected()

        async def _safe_read(nid: str) -> tuple[str, SensorReading]:
            try:
                reading = await self.read_sensor_data(nid)
            except Exception as exc:
                _logger.warning("Batch read failed for %s: %s", nid, exc)
                now = datetime.now(timezone.utc)
                reading = SensorReading(
                    node_id=nid, value=None, status="Bad",
                    source_ts=now, server_ts=now,
                )
            return nid, reading

        results = await asyncio.gather(*[_safe_read(nid) for nid in node_ids])
        return dict(results)

    # ------------------------------------------------------------------
    # 3. Subscription (server-push streaming)
    # ------------------------------------------------------------------

    async def subscribe(
        self,
        node_ids:            List[str],
        callback:            Callable[[SensorReading], None],
        publish_interval_ms: Optional[float] = None,
    ) -> Any:
        """
        Register a server-push subscription for one or more sensor nodes.

        Instead of polling the server every second (which saturates the network
        and the PLC), the server evaluates each node at the publish_interval
        and sends a notification to PetroFlow ONLY when the value changes
        (the MonitoredItem deadband / ValueChange filter).

        Parameters
        ----------
        node_ids :
            List of OPC UA node IDs to monitor.
        callback :
            Callable invoked on each data-change event with a SensorReading.
            Signature: callback(reading: SensorReading) -> None
        publish_interval_ms :
            How often the server evaluates changes (default: 500 ms).
            Lower values = more reactive, higher server CPU.

        Returns
        -------
        asyncua.Subscription
            The live subscription object (keep alive for the duration of
            monitoring; cancel with await subscription.delete()).

        Raises
        ------
        RuntimeError
            If not connected.
        """
        self._require_connected()

        interval = publish_interval_ms if publish_interval_ms is not None \
                   else self._publish_interval_ms

        _logger.info(
            "Creating OPC-UA subscription for %d nodes (interval=%.0fms)",
            len(node_ids), interval,
        )
        _audit.log_system(
            f"OPC-UA subscription requested for {len(node_ids)} nodes",
            action="OPCUA_SUBSCRIBE",
            node_count=len(node_ids),
            interval_ms=interval,
            node_ids=node_ids,
        )

        try:
            # Map handle -> node_id for the handler (populated after subscribe_data_change)
            node_id_map: Dict[int, str] = {}
            handler = _SubscriptionHandler(callback, node_id_map)

            # Create the subscription with the server
            subscription = await self._client.create_subscription(
                period=interval,
                handler=handler,
            )

            # Resolve Node objects and register monitored items
            nodes = [self._client.get_node(nid) for nid in node_ids]
            handles = await subscription.subscribe_data_change(nodes)

            # Populate handle map (handles is a list of ints)
            if isinstance(handles, list):
                for handle, nid in zip(handles, node_ids):
                    node_id_map[handle] = nid
            else:
                node_id_map[handles] = node_ids[0]

            self._active_subscriptions.append(subscription)
            self._state.subscriptions.append(id(subscription))

            _logger.info(
                "OPC-UA subscription active: %d monitored items registered",
                len(node_ids),
            )
            _audit.log_system(
                f"OPC-UA subscription active: {len(node_ids)} monitored items",
                action="OPCUA_SUBSCRIBED",
                node_ids=node_ids,
                interval_ms=interval,
            )

            return subscription

        except ua.UaStatusCodeError as exc:
            msg = (
                f"OPC-UA subscription rejected by server (code={exc.code}). "
                f"Verify node IDs and server access rights."
            )
            _logger.error(msg)
            _audit.log_error(exc, context="OPC-UA subscribe")
            raise RuntimeError(msg) from exc

        except Exception as exc:
            msg = f"OPC-UA subscription creation failed: {exc}"
            _logger.exception(msg)
            _audit.log_error(exc, context="OPC-UA subscribe")
            raise

    async def cancel_subscription(self, subscription: Any) -> None:
        """
        Gracefully cancel a server-push subscription.

        Parameters
        ----------
        subscription :
            The subscription object returned by subscribe().
        """
        try:
            await subscription.delete()
            if subscription in self._active_subscriptions:
                self._active_subscriptions.remove(subscription)
            _logger.info("OPC-UA subscription cancelled")
            _audit.log_system("OPC-UA subscription cancelled", action="OPCUA_UNSUBSCRIBE")
        except Exception as exc:
            _logger.warning("Error cancelling OPC-UA subscription: %s", exc)

    # ------------------------------------------------------------------
    # 4. Node browsing (server introspection)
    # ------------------------------------------------------------------

    async def browse_nodes(
        self,
        root_node_id: str = "i=84",        # Objects folder (standard UA root)
        max_depth:    int = 3,
    ) -> List[Dict[str, str]]:
        """
        Recursively browse the server's address space from root_node_id.

        Useful for discovering available sensor tags without knowing them
        in advance — enables PetroFlow to render a dynamic tag picker.

        Parameters
        ----------
        root_node_id :
            Starting node for the browse walk.
            Default "i=84" is the OPC UA Objects folder (standard entry point).
        max_depth :
            Maximum recursion depth to prevent unbounded traversal on
            large SCADA servers (typical DCS trees can have 10+ levels).

        Returns
        -------
        list of dict
            Each entry: {"node_id": str, "display_name": str, "node_class": str}
        """
        self._require_connected()

        discovered: List[Dict[str, str]] = []

        async def _walk(node_id: str, depth: int) -> None:
            if depth > max_depth:
                return
            try:
                node     = self._client.get_node(node_id)
                children = await node.get_children()
                for child in children:
                    nid   = str(child.nodeid)
                    dname = (await child.read_display_name()).Text or nid
                    nclass = str(await child.read_node_class())
                    discovered.append({
                        "node_id":      nid,
                        "display_name": dname,
                        "node_class":   nclass,
                    })
                    await _walk(nid, depth + 1)
            except Exception as exc:
                _logger.debug("Browse skipped node %s: %s", node_id, exc)

        await _walk(root_node_id, depth=0)

        _logger.info("OPC-UA browse completed: %d nodes discovered", len(discovered))
        _audit.log_system(
            f"OPC-UA server browse: {len(discovered)} nodes discovered",
            action="OPCUA_BROWSE",
            root=root_node_id,
            depth=max_depth,
            count=len(discovered),
        )
        return discovered

    # ------------------------------------------------------------------
    # 5. Disconnect
    # ------------------------------------------------------------------

    async def disconnect(self) -> None:
        """
        Gracefully terminate all subscriptions and close the OPC UA session.

        Safe to call even if the client is not currently connected.
        """
        if not self._state.connected:
            _logger.debug("disconnect() called but not connected — no-op")
            return

        # Cancel all active subscriptions first
        for sub in list(self._active_subscriptions):
            await self.cancel_subscription(sub)

        try:
            await self._client.disconnect()
            _logger.info("OPC UA session closed: %s", self._state.url)
            _audit.log_system(
                f"OPC-UA session closed: {self._state.url}",
                action="OPCUA_DISCONNECTED",
                endpoint=self._state.url,
            )
        except (BadSessionClosed, BadConnectionClosed):
            # Server already closed the session — not an error
            _logger.debug("Session already closed by server")
        except Exception as exc:
            _logger.warning("Error during OPC UA disconnect: %s", exc)
            _audit.log_error(exc, context="OPC-UA disconnect")
        finally:
            self._state.connected = False
            self._client = None

    # ------------------------------------------------------------------
    # 6. Context manager support (async with)
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "PetroflowOPCClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.disconnect()

    # ------------------------------------------------------------------
    # Properties & helpers
    # ------------------------------------------------------------------

    @property
    def is_connected(self) -> bool:
        """True if the OPC UA session is active."""
        return self._state.connected

    @property
    def state(self) -> ConnectionState:
        """Read-only snapshot of the current connection state."""
        return self._state

    def _require_connected(self) -> None:
        """Raise RuntimeError if the client is not connected."""
        if not self._state.connected or self._client is None:
            raise RuntimeError(
                "OPC-UA client is not connected. "
                "Call await client.connect(url, username, password) first."
            )


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------

def get_opc_client(
    timeout:             int   = DEFAULT_TIMEOUT_SECONDS,
    session_timeout_ms:  int   = DEFAULT_SESSION_TIMEOUT_MS,
    publish_interval_ms: float = DEFAULT_PUBLISH_INTERVAL_MS,
) -> PetroflowOPCClient:
    """
    Factory function — mirrors the pattern used by get_audit_logger()
    and get_telemetry_client() throughout PetroFlow.

    Returns a new (not-yet-connected) PetroflowOPCClient instance.
    """
    return PetroflowOPCClient(
        timeout=timeout,
        session_timeout_ms=session_timeout_ms,
        publish_interval_ms=publish_interval_ms,
    )
