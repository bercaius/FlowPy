"""Application backbone — services, WebSocket bridge, plugin manager integration.

Services singleton wires together:
- Plugin manager lifecycle
- WebSocket bridge (JSON-RPC 2.0)
- Graph notification system
- Run request handling
"""

from __future__ import annotations

import json
import logging
import os
import socket
import struct
import threading
from typing import Callable

from PySide6.QtCore import QObject, QTimer, Qt, Signal

from flowpy.core.pytoflow import FlowBuilder, layout_graph
from flowpy.core.runner import Runner
from flowpy.plugins.manager import PluginManager

logger = logging.getLogger(__name__)


def _server_frame(payload: bytes) -> bytes:
    """WebSocket sunucu çerçevesi (maskesiz, uzunluk kodlamalı)."""
    n = len(payload)
    if n <= 125:
        return bytes([0x81, n]) + payload
    if n <= 65535:
        return bytes([0x81, 126]) + struct.pack(">H", n) + payload
    return bytes([0x81, 127]) + struct.pack(">Q", n) + payload


class Bridge(QObject):
    """WebSocket bridge for external tools (VS Code, etc.).

    stdlib-only socket — PyInstaller uyumlu.
    JSON-RPC 2.0 protocol.
    """

    message_received = Signal(str)

    def __init__(self, host: str = "127.0.0.1", port: int = 18809) -> None:
        super().__init__()
        self.host = host
        self.port = port
        self._running = False
        self._thread: threading.Thread | None = None
        self._sock: socket.socket | None = None
        self._clients: set[socket.socket] = set()

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def url(self) -> str:
        return f"ws://{self.host}:{self.port}"

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        logger.info("Bridge started on %s", self.url)

    def stop(self) -> None:
        self._running = False
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=2.0)
        logger.info("Bridge stopped")

    def _serve(self) -> None:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            srv.bind((self.host, self.port))
            srv.listen(5)
            srv.settimeout(1.0)
            while self._running:
                try:
                    client, addr = srv.accept()
                    threading.Thread(
                        target=self._handle_client,
                        args=(client, addr),
                        daemon=True,
                    ).start()
                except socket.timeout:
                    continue
                except OSError:
                    break
        except Exception as exc:
            logger.error("Bridge error: %s", exc)
        finally:
            srv.close()

    def _handle_client(self, client: socket.socket, addr) -> None:
        logger.debug("Client connected: %s", addr)
        try:
            key = self._handshake(client)
            if not key:
                return
            self._clients.add(client)
            logger.info("Bridge client registered (%d aktif)", len(self._clients))
            self._read_frames(client)
        except Exception as exc:
            logger.debug("Client error: %s", exc)
        finally:
            self._clients.discard(client)
            try:
                client.close()
            except Exception:
                pass

    def _handshake(self, client: socket.socket) -> str | None:
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = client.recv(1024)
            if not chunk:
                return None
            buf += chunk

        headers = {}
        for line in buf.split(b"\r\n"):
            if b":" in line:
                k, v = line.split(b":", 1)
                headers[k.strip().decode().lower()] = v.strip().decode()

        key = headers.get("sec-websocket-key", "")
        if not key:
            return None

        import hashlib
        import base64
        accept = base64.b64encode(
            hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()
        ).decode()

        client.sendall(
            b"HTTP/1.1 101 Switching Protocols\r\n"
            b"Upgrade: websocket\r\n"
            b"Connection: Upgrade\r\n"
            b"Sec-WebSocket-Accept: " + accept.encode() + b"\r\n\r\n"
        )
        return key

    def _read_frames(self, client: socket.socket) -> None:
        while self._running:
            try:
                frame = self._read_frame(client)
                if frame is None:
                    break
                self.message_received.emit(frame)
            except Exception:
                break

    def _read_frame(self, client: socket.socket) -> str | None:
        head = b""
        while len(head) < 2:
            chunk = client.recv(2 - len(head))
            if not chunk:
                return None
            head += chunk

        masked = bool(head[1] & 0x80)
        length = head[1] & 0x7F
        if length == 126:
            ext = b""
            while len(ext) < 2:
                ext += client.recv(2 - len(ext))
            length = struct.unpack(">H", ext)[0]
        elif length == 127:
            ext = b""
            while len(ext) < 8:
                ext += client.recv(8 - len(ext))
            length = struct.unpack(">Q", ext)[0]

        mask_key = b""
        if masked:
            mask_key = b""
            while len(mask_key) < 4:
                mask_key += client.recv(4 - len(mask_key))

        data = b""
        while len(data) < length:
            chunk = client.recv(length - len(data))
            if not chunk:
                return None
            data += chunk

        if masked:
            data = bytes(b ^ mask_key[i % 4] for i, b in enumerate(data))

        return data.decode("utf-8", "replace")

    def send(self, text: str) -> None:
        """Broadcast a text message to all connected clients."""
        if not self._clients:
            return
        try:
            payload = text.encode("utf-8")
            frame = _server_frame(payload)
            dead = set()
            for client in list(self._clients):
                try:
                    client.sendall(frame)
                except Exception:
                    dead.add(client)
            for client in dead:
                self._clients.discard(client)
        except Exception:
            pass


class Services(QObject):
    """Central application services backbone."""

    runRequested = Signal(str)
    logMessage = Signal(str)

    def __init__(
        self,
        parent: QObject | None = None,
        host: str = "127.0.0.1",
        port: int = 18809,
    ) -> None:
        super().__init__(parent)
        self.manager = PluginManager()
        self.bridge = Bridge(host, port)
        self.bridge.message_received.connect(
            self._on_bridge_message, Qt.ConnectionType.DirectConnection
        )

        self._runner = Runner()
        self._runner.line.connect(self._on_run_line)
        self._runner.finished.connect(lambda c: self._notify({"method": "run_finished", "params": {"exit": c}}))

        self._get_code: Callable[[], str] = lambda: ""
        self._get_graph: Callable[[], object | None] = lambda: None
        self._set_code: Callable[[str], None] | None = None
        self._log: Callable[[str], None] | None = None

    def attach(
        self,
        *,
        get_code: Callable[[], str],
        get_graph: Callable[[], object | None],
        log: Callable[[str], None],
        set_code: Callable[[str], None] | None = None,
    ) -> None:
        """Attach UI callbacks."""
        self._get_code = get_code
        self._get_graph = get_graph
        self._log = log
        self._set_code = set_code

    def start(self) -> None:
        """Start all services."""
        self.manager.discover()
        self.bridge.start()
        logger.info("Services started")

    def stop(self) -> None:
        """Stop all services."""
        self.bridge.stop()
        for name in list(self.manager.active_plugins):
            self.manager.deactivate_plugin(name)
        logger.info("Services stopped")

    def notify_graph(self, graph: object) -> None:
        """Notify external tools about graph changes."""
        payload = json.dumps({
            "jsonrpc": "2.0",
            "method": "graph_updated",
            "params": {"nodes": len(getattr(graph, "nodes", []))},
        })
        self.bridge.send(payload)

    # ------------------------------------------------------------------
    # Gerçek dönüştürücü & çalıştırıcı (JSON-RPC ile dış araçlara açılır)
    # ------------------------------------------------------------------
    def generate_graph(self, field: str = "") -> dict:
        """Aktif kodu gerçek dönüştürücüden geçirip grafı JSON olarak döndürür."""
        code = self._get_code()
        if not code.strip():
            return {"nodes": [], "edges": [], "error": "kod boş"}
        graph, err = FlowBuilder().build(code, field)
        if err is not None:
            return {"nodes": [], "edges": [], "error": str(err)}
        graph = layout_graph(graph)
        return {
            "nodes": [
                {
                    "id": n.id,
                    "kind": n.kind,
                    "label": n.label,
                    "code": getattr(n, "code", ""),
                    "x": round(n.x, 1),
                    "y": round(n.y, 1),
                    "line": n.line,
                }
                for n in graph.nodes
            ],
            "edges": [
                {"src": e.src, "dst": e.dst, "label": e.label, "back": e.back}
                for e in graph.edges
            ],
        }

    def run_code(self, code: str, cwd: str | None = None) -> None:
        """Kodu gerçek Python yorumlayıcısı ile çalıştırır (köprü üzerinden)."""
        import os
        from pathlib import Path

        workdir = Path(cwd) if cwd else Path(os.getcwd())
        self._notify({"method": "run_started", "params": {}})
        self._runner.run_code(code, workdir)

    def _on_run_line(self, text: str) -> None:
        self._notify({"method": "run_output", "params": {"line": text}})
        if self._log is not None:
            self._log(text)

    def _notify(self, message: dict) -> None:
        message.setdefault("jsonrpc", "2.0")
        self.bridge.send(json.dumps(message))

    def _on_bridge_message(self, message: str) -> None:
        """Handle incoming WebSocket messages (JSON-RPC 2.0)."""
        try:
            req = json.loads(message)
            method = req.get("method")
            req_id = req.get("id")
            params = req.get("params")

            result = None
            error = None

            if method == "ping":
                result = "pong"
            elif method == "get_code":
                result = self._get_code()
            elif method == "get_graph":
                g = self._get_graph()
                result = {
                    "nodes": len(getattr(g, "nodes", [])),
                    "edges": len(getattr(g, "edges", [])),
                }
            elif method == "list_plugins":
                result = list(self.manager.loaded_plugins.keys())
            elif method == "activate_plugin":
                name = params if isinstance(params, str) else params.get("name")
                ok = self.manager.activate_plugin(name) if name else False
                result = {"success": ok}
            elif method == "deactivate_plugin":
                name = params if isinstance(params, str) else params.get("name")
                self.manager.deactivate_plugin(name)
                result = {"success": True}
            elif method == "generate_graph":
                field = params.get("field", "") if isinstance(params, dict) else ""
                result = self.generate_graph(field)
            elif method == "set_code":
                code = params if isinstance(params, str) else (params.get("code", "") if isinstance(params, dict) else "")
                if self._set_code is not None:
                    self._set_code(code)
                result = {"success": True}
            elif method == "run":
                code = params if isinstance(params, str) else (params.get("code", "") if isinstance(params, dict) else "")
                if not code:
                    code = self._get_code()
                cwd = params.get("cwd") if isinstance(params, dict) else None
                if code:
                    QTimer.singleShot(0, lambda: self.run_code(code, cwd))
                    result = {"started": True}
                else:
                    error = {"code": -32000, "message": "Çalıştırılacak kod yok"}
            elif method == "run_file":
                path = params.get("path") if isinstance(params, dict) else (params if isinstance(params, str) else "")
                if path:
                    self.runRequested.emit(path)
                    result = {"started": True}
                else:
                    error = {"code": -32000, "message": "Dosya yolu yok"}
            else:
                error = {"code": -32601, "message": f"Method not found: {method}"}

            if req_id is not None:
                response = {"jsonrpc": "2.0", "id": req_id}
                if error:
                    response["error"] = error
                else:
                    response["result"] = result
                self.bridge.send(json.dumps(response))
        except Exception as exc:
            logger.error("Bridge message error: %s", exc)
