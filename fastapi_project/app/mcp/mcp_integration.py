import subprocess
import sys
import os
from typing import Optional, Dict, Any, List
from pathlib import Path
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
import asyncio
import logging
import json

logger = logging.getLogger(__name__)


class MCPServerManager:
    """MCP 서버 프로세스 관리자"""

    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.mcp_server_path = Path(__file__).parent / "mcp_server.py"

    def start(self):
        """MCP 서버 시작"""
        if self.process is None or self.process.poll() is not None:
            try:
                self.process = subprocess.Popen(
                    [sys.executable, str(self.mcp_server_path)],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env={
                        **os.environ,
                        "PYTHONPATH": str(Path(__file__).parent.parent.parent),
                    },
                )
                logger.info(f"MCP Server started with PID: {self.process.pid}")
            except Exception as e:
                logger.error(f"Failed to start MCP server: {e}")
                raise

    def stop(self):
        """MCP 서버 중지"""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            logger.info("MCP Server stopped")

    def restart(self):
        """MCP 서버 재시작"""
        self.stop()
        self.start()

    def is_running(self) -> bool:
        """MCP 서버 실행 상태 확인"""
        return self.process is not None and self.process.poll() is None

    def get_status(self) -> Dict[str, Any]:
        """MCP 서버 상태 정보 반환"""
        if self.is_running():
            return {
                "status": "running",
                "pid": self.process.pid,
                "uptime": "unknown",  # 추후 구현 가능
            }
        else:
            return {"status": "stopped", "pid": None, "uptime": None}

    def get_logs(self, lines: int = 50) -> List[str]:
        """MCP 서버 로그 반환 (추후 구현)"""
        # 현재는 placeholder
        return ["Log collection not implemented yet"]


def integrate_mcp_with_fastapi(app: FastAPI) -> MCPServerManager:
    """FastAPI 앱에 MCP 서버 통합"""

    mcp_manager = MCPServerManager()

    # MCP 관련 라우트 추가
    @app.post("/mcp/restart", tags=["MCP"])
    async def restart_mcp_server(background_tasks: BackgroundTasks):
        """MCP 서버 재시작"""
        background_tasks.add_task(mcp_manager.restart)
        return {"message": "MCP server restart initiated"}

    @app.get("/mcp/status", tags=["MCP"])
    async def get_mcp_status():
        """MCP 서버 상태 확인"""
        if mcp_manager.is_running():
            return {"status": "running", "pid": mcp_manager.process.pid}
        else:
            return {"status": "stopped"}

    @app.get("/mcp/config", tags=["MCP"])
    async def get_mcp_config():
        """Claude Desktop 설정 정보 반환"""
        return {
            "config_location": "~/.claude/claude_desktop_config.json",
            "config_example": {
                "mcpServers": {
                    "careerbee": {
                        "command": "python",
                        "args": [str(mcp_manager.mcp_server_path)],
                        "env": {"PYTHONPATH": str(Path(__file__).parent.parent.parent)},
                    }
                }
            },
        }

    return mcp_manager
