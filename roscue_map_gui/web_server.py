#!/usr/bin/env python3
"""Standalone ROScue map GUI Flask server."""

from __future__ import annotations

import json
import queue
import time
from typing import Any, Dict, Generator

from flask import Flask, Response, jsonify, render_template, request, stream_with_context

import web_gateway

app = Flask(__name__)
ros_node = web_gateway.start_ros_thread()


def ok(message: str, extra: Dict[str, Any] | None = None):
    payload = {"result": "success", "message": message}
    if extra:
        payload.update(extra)
    return jsonify(payload), 200


def fail(message: str, code: int = 400):
    return jsonify({"result": "fail", "message": message}), code


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/api/snapshot", methods=["GET"])
def snapshot():
    return jsonify(web_gateway.STATE.snapshot())


@app.route("/api/clicked_point", methods=["POST"])
def clicked_point():
    data = request.get_json(force=True) or {}
    try:
        x = float(data.get("x"))
        y = float(data.get("y"))
        z = float(data.get("z", 0.0))
    except Exception:
        return fail("x, y는 숫자로 보내야 합니다.", 400)

    try:
        accepted, message = ros_node.publish_clicked_point(x, y, z)
        return ok(message, {"x": x, "y": y, "z": z}) if accepted else fail(message, 500)
    except Exception as e:
        return fail(f"clicked_point publish error: {e}", 500)


@app.route("/api/config", methods=["GET"])
def config():
    s = web_gateway.STATE.snapshot()["status"]
    return jsonify(s)


def sse_format(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.route("/events", methods=["GET"])
def events():
    q = web_gateway.STATE.subscribe()

    def generate() -> Generator[str, None, None]:
        try:
            # 접속 직후 현재 상태 한 번 전송
            yield sse_format("snapshot", web_gateway.STATE.snapshot())
            last_ping = time.time()
            while True:
                try:
                    item = q.get(timeout=1.0)
                    yield sse_format(item["event"], item["data"])
                except queue.Empty:
                    # 프록시/브라우저 연결 유지를 위한 ping
                    now = time.time()
                    if now - last_ping > 10.0:
                        last_ping = now
                        yield ": ping\n\n"
        finally:
            web_gateway.STATE.unsubscribe(q)

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False, threaded=True)
