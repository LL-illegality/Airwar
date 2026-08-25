"""Web 客户端静态服务器（Flask，plan P1-3）

- 静态托管：/（index.html）、/js/*、/css/*、/images/*、/sounds/*、/music/*
- API：/api/health（存活探针）、/api/config（基于请求 Host 推断默认 WebSocket 地址）、
  /api/servers（预留：未来可列出可用游戏服务器）
- 仅服务项目根目录内文件（send_from_directory + __file__ 定位），不与游戏数据交互
- 与游戏 WebSocket 服务器（server.py，默认 8000 端口）完全独立；
  浏览器通过 /api/config 拿到的 ws://host:8000 直连游戏服务器
- 桌面端客户端不受影响；本服务器只服务 Web 客户端
"""

import os
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request, send_from_directory

PROJECT_ROOT = Path(__file__).resolve().parent

app = Flask(__name__, static_folder=None)

# 开发期禁止浏览器缓存，便于迭代
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0


@app.route("/")
def index() -> Any:
    """Web 客户端入口页"""
    return send_from_directory(PROJECT_ROOT / "web", "index.html")


@app.route("/js/<path:name>")
def js(name: str) -> Any:
    """JS 资源"""
    return send_from_directory(PROJECT_ROOT / "web" / "js", name)


@app.route("/css/<path:name>")
def css(name: str) -> Any:
    """CSS 资源"""
    return send_from_directory(PROJECT_ROOT / "web" / "css", name)


@app.route("/images/<path:name>")
def images(name: str) -> Any:
    """游戏贴图"""
    return send_from_directory(PROJECT_ROOT / "images", name)


@app.route("/sounds/<path:name>")
def sounds(name: str) -> Any:
    """游戏音效"""
    resp = send_from_directory(PROJECT_ROOT / "sounds", name)
    if name.lower().endswith(".wav"):
        resp.mimetype = "audio/wav"
    return resp


@app.route("/music/<path:name>")
def music(name: str) -> Any:
    """背景音乐"""
    resp = send_from_directory(PROJECT_ROOT / "music", name)
    if name.lower().endswith(".wav"):
        resp.mimetype = "audio/wav"
    return resp


@app.route("/api/health")
def health() -> Any:
    """存活探针"""
    return jsonify({"status": "ok"})


@app.route("/api/config")
def config() -> Any:
    """客户端配置：基于请求 Host 推断默认游戏服务器地址（WebSocket）"""
    host = request.host.split(":")[0]
    return jsonify({"defaultServer": f"ws://{host}:8000"})


@app.route("/api/servers")
def servers() -> Any:
    """预留接口：未来可列出可用游戏服务器"""
    return jsonify([])


def main() -> None:
    port = int(os.environ.get("WEB_PORT", "8080"))
    print(f"Web 客户端已启动: http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()