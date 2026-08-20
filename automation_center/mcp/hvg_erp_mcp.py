#!/usr/bin/env python3
"""Local MCP server for the HaviGroup ERP GraphQL API.

The server deliberately exposes a small, typed toolset instead of a generic
GraphQL executor.  That keeps every operation inside PROJ-0049 and prevents an
AI client from escaping the business scope by crafting arbitrary queries.
"""

from __future__ import annotations

import json
import subprocess
import time
import urllib.error
import urllib.request
import warnings
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

warnings.filterwarnings(
    "ignore",
    message=r"Field 'lifespan' has an incomplete definition.*",
)

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations


ERP_BASE_URL = "https://erp.havigroup.llc"
ERP_GRAPHQL_PATH = "/api/method/hvg_workspace.graphql.endpoint.graphql"
ALLOWED_PROJECT = "PROJ-0049"
KEYCHAIN_SERVICE = "HaviGroup ERP MCP"
REQUEST_TIMEOUT_SECONDS = 30
MINIMUM_REQUEST_INTERVAL_SECONDS = 1.1  # stays below the 60 requests/minute bot limit


class ERPError(RuntimeError):
    """A safe error that can be returned to an MCP client."""


def _keychain_value(account: str) -> str:
    try:
        completed = subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-a", account, "-w"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise ERPError(
            "ERP credential chưa có trong macOS Keychain. "
            "Cần lưu api-key và api-secret dưới service 'HaviGroup ERP MCP'."
        ) from exc
    value = completed.stdout.strip()
    if not value:
        raise ERPError("ERP credential trong macOS Keychain đang rỗng.")
    return value


def _optional_keychain_value(account: str) -> str | None:
    try:
        return _keychain_value(account)
    except ERPError:
        return None


def _authorization_header() -> str:
    """Use the scoped Bot credential whenever it has been provisioned."""
    bot_token = _optional_keychain_value("bot-token")
    if bot_token:
        return f"HVGToken {bot_token}"
    key = _keychain_value("api-key")
    secret = _keychain_value("api-secret")
    return f"token {key}:{secret}"


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def _clean_text(value: str, *, field: str, maximum: int) -> str:
    text = " ".join(str(value or "").split()).strip()
    if not text:
        raise ERPError(f"{field} là bắt buộc.")
    if len(text) > maximum:
        raise ERPError(f"{field} dài quá {maximum} ký tự.")
    return text


def _task_id(value: str) -> str:
    task = _clean_text(value, field="Task ID", maximum=140)
    if not task.upper().startswith("TASK-"):
        raise ERPError("Task ID phải có dạng TASK-xxxx.")
    return task


def _walk(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _belongs_to_allowed_project(payload: Any) -> bool:
    project_keys = {"project", "project_id", "projectId", "project_name", "projectName"}
    for item in _walk(payload):
        for key in project_keys:
            candidate = item.get(key)
            if isinstance(candidate, str) and candidate.strip().upper() == ALLOWED_PROJECT:
                return True
            if isinstance(candidate, dict):
                for nested_key in ("name", "id", "project"):
                    nested = candidate.get(nested_key)
                    if isinstance(nested, str) and nested.strip().upper() == ALLOWED_PROJECT:
                        return True
    return False


@dataclass
class ERPClient:
    last_request_at: float = 0.0

    def execute(self, operation_name: str, query: str, variables: dict[str, Any]) -> Any:
        remaining = MINIMUM_REQUEST_INTERVAL_SECONDS - (time.monotonic() - self.last_request_at)
        if remaining > 0:
            time.sleep(remaining)
        body = json.dumps(
            {"query": query, "variables": variables, "operationName": operation_name},
            ensure_ascii=False,
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{ERP_BASE_URL}{ERP_GRAPHQL_PATH}",
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "HaviGroup-ERP-MCP/1.0",
                "Authorization": _authorization_header(),
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                raise ERPError("ERP credential không hợp lệ hoặc không còn hiệu lực.") from exc
            if exc.code == 429:
                raise ERPError("ERP đang giới hạn tần suất. Hãy đợi một lúc rồi thử lại.") from exc
            raise ERPError(f"ERP từ chối request (HTTP {exc.code}).") from exc
        except urllib.error.URLError as exc:
            raise ERPError("Không kết nối được ERP qua HTTPS.") from exc
        except (TimeoutError, json.JSONDecodeError) as exc:
            raise ERPError("ERP trả về phản hồi không hợp lệ hoặc quá thời gian.") from exc
        finally:
            self.last_request_at = time.monotonic()

        errors = payload.get("errors") if isinstance(payload, dict) else None
        if errors:
            messages = [str(error.get("message") or "Lỗi GraphQL.") for error in errors if isinstance(error, dict)]
            raise ERPError("; ".join(messages[:3]) or "ERP từ chối thao tác.")
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
            raise ERPError("ERP không trả dữ liệu GraphQL hợp lệ.")
        return payload["data"].get(_field_name(operation_name))


def _field_name(operation_name: str) -> str:
    return {
        "ProjectOverview": "projectOverview",
        "TaskBoard": "taskBoard",
        "TaskDetail": "taskDetail",
        "CreateTask": "createTask",
        "UpdateTaskStatus": "updateTaskStatus",
        "AddTaskComment": "addTaskComment",
    }[operation_name]


client = ERPClient()
READ_ONLY = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=True)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True)
mcp = FastMCP(
    "HaviGroup ERP",
    instructions=(
        "MCP này chỉ thao tác ERP Project PROJ-0049. Dùng tool đọc để kiểm tra trước. "
        "Các tool ghi bắt buộc confirmed=true và chỉ gọi sau khi người dùng xác nhận rõ thay đổi. "
        "Không yêu cầu, hiển thị hoặc ghi ERP credential vào hội thoại."
    ),
)


@mcp.tool(annotations=READ_ONLY)
def erp_project_overview() -> str:
    """Đọc tổng quan Project PROJ-0049; không thay đổi dữ liệu."""
    payload = client.execute(
        "ProjectOverview",
        "query ProjectOverview($project: String!) { projectOverview(project: $project) }",
        {"project": ALLOWED_PROJECT},
    )
    return _compact_json(payload)


@mcp.tool(annotations=READ_ONLY)
def erp_list_project_tasks(include_archived: bool = False) -> str:
    """Liệt kê board Task thuộc riêng Project PROJ-0049; không thay đổi dữ liệu."""
    payload = client.execute(
        "TaskBoard",
        "query TaskBoard($project: String!, $includeArchived: Boolean!) { taskBoard(project: $project, includeArchived: $includeArchived) }",
        {"project": ALLOWED_PROJECT, "includeArchived": bool(include_archived)},
    )
    return _compact_json(payload)


@mcp.tool(annotations=READ_ONLY)
def erp_get_task(task_id: str) -> str:
    """Đọc một Task trong PROJ-0049. Từ chối Task nếu không xác minh được scope."""
    task = _task_id(task_id)
    payload = client.execute(
        "TaskDetail",
        "query TaskDetail($name: String!) { taskDetail(name: $name) }",
        {"name": task},
    )
    if not _belongs_to_allowed_project(payload):
        raise ERPError("Task không thuộc hoặc không xác minh được thuộc PROJ-0049.")
    return _compact_json(payload)


@mcp.tool(annotations=WRITE)
def erp_create_task(subject: str, description: str = "", priority: str = "", exp_end_date: str = "", confirmed: bool = False) -> str:
    """Tạo Task mới trong PROJ-0049. Cần confirmed=true sau xác nhận rõ của người dùng."""
    if not confirmed:
        raise ERPError("Tạo Task là thao tác ghi. Hãy xin xác nhận rồi gọi lại với confirmed=true.")
    variables = {
        "subject": _clean_text(subject, field="Tiêu đề Task", maximum=180),
        "project": ALLOWED_PROJECT,
        "description": _clean_text(description, field="Mô tả", maximum=6000) if description else "",
        "priority": _clean_text(priority, field="Ưu tiên", maximum=80) if priority else "",
        "expEndDate": _clean_text(exp_end_date, field="Hạn hoàn thành", maximum=40) if exp_end_date else "",
    }
    payload = client.execute(
        "CreateTask",
        "mutation CreateTask($subject: String!, $project: String!, $description: String, $priority: String, $expEndDate: String) { createTask(subject: $subject, project: $project, description: $description, priority: $priority, expEndDate: $expEndDate) }",
        variables,
    )
    return _compact_json(payload)


@mcp.tool(annotations=WRITE)
def erp_update_task_status(task_id: str, status: str, confirmed: bool = False) -> str:
    """Đổi trạng thái Task trong PROJ-0049. Cần confirmed=true sau xác nhận rõ của người dùng."""
    if not confirmed:
        raise ERPError("Đổi trạng thái là thao tác ghi. Hãy xin xác nhận rồi gọi lại với confirmed=true.")
    task = _task_id(task_id)
    detail = client.execute(
        "TaskDetail",
        "query TaskDetail($name: String!) { taskDetail(name: $name) }",
        {"name": task},
    )
    if not _belongs_to_allowed_project(detail):
        raise ERPError("Task không thuộc hoặc không xác minh được thuộc PROJ-0049.")
    payload = client.execute(
        "UpdateTaskStatus",
        "mutation UpdateTaskStatus($name: String!, $status: String!) { updateTaskStatus(name: $name, status: $status) }",
        {"name": task, "status": _clean_text(status, field="Trạng thái", maximum=80)},
    )
    return _compact_json(payload)


@mcp.tool(annotations=WRITE)
def erp_add_task_comment(task_id: str, content: str, confirmed: bool = False) -> str:
    """Thêm comment văn bản vào Task trong PROJ-0049. Cần confirmed=true sau xác nhận rõ của người dùng."""
    if not confirmed:
        raise ERPError("Thêm comment là thao tác ghi. Hãy xin xác nhận rồi gọi lại với confirmed=true.")
    task = _task_id(task_id)
    detail = client.execute(
        "TaskDetail",
        "query TaskDetail($name: String!) { taskDetail(name: $name) }",
        {"name": task},
    )
    if not _belongs_to_allowed_project(detail):
        raise ERPError("Task không thuộc hoặc không xác minh được thuộc PROJ-0049.")
    payload = client.execute(
        "AddTaskComment",
        "mutation AddTaskComment($name: String!, $content: String!) { addTaskComment(name: $name, content: $content) }",
        {"name": task, "content": _clean_text(content, field="Nội dung comment", maximum=6000)},
    )
    return _compact_json(payload)


if __name__ == "__main__":
    mcp.run(transport="stdio")
