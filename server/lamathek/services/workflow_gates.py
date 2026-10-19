"""Shared Verleih line-action gating (lamathek/domain/workflow_gates.json, also read by web)."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources


@lru_cache(maxsize=1)
def workflow_gates() -> dict:
    gates = resources.files("lamathek") / "domain" / "workflow_gates.json"
    return json.loads(gates.read_text(encoding="utf-8"))


def line_action_steps(action: str, line_status: str) -> tuple[str, ...] | None:
    for rule in workflow_gates()["lineActions"]:
        if rule["action"] == action and rule["lineStatus"] == line_status:
            return tuple(rule["steps"])
    return None


def workflow_step_for_line_status(status: str) -> str | None:
    return workflow_gates()["lineStatusToStep"].get(status)


def open_workflow_step_from_open_statuses(open_statuses: set[str]) -> str | None:
    if not open_statuses:
        return None
    status_to_step = workflow_gates()["lineStatusToStep"]
    for status in workflow_gates()["openStepPriority"]:
        if status in open_statuses:
            return status_to_step[status]
    return None
