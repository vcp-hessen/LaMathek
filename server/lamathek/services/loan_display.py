"""Verleih-Bezeichnungen für UI, PDF und Kalender."""

from __future__ import annotations

from flask import current_app, has_app_context

from lamathek.config import Config
from lamathek.models.loan import Loan

_BLANK_GROUP = {"", "—", "-"}


def _cfg(name: str, default=None):
    if has_app_context():
        return current_app.config.get(name, default)
    return getattr(Config, name, default)


def loan_display_title(loan: Loan) -> str:
    if loan.event is not None and (loan.event.name or "").strip():
        return loan.event.name.strip()
    if loan.group is not None and (loan.group.name or "").strip() not in _BLANK_GROUP:
        return loan.group.name.strip()
    return f"Verleih #{loan.id}"


def loan_group_label(loan: Loan) -> str:
    if loan.group is None:
        return ""
    name = (loan.group.name or "").strip()
    if name in _BLANK_GROUP:
        return ""
    return name


def loan_borrower_label(loan: Loan) -> str:
    user = loan.borrower_user
    if user is None:
        return ""
    return (user.name or user.email or "").strip()


def loan_detail_url(loan: Loan) -> str:
    frontend_url = str(_cfg("FRONTEND_URL", "") or "").strip().rstrip("/")
    if not frontend_url:
        return ""
    return f"{frontend_url}/inventories/{loan.inventory_id}/loans/{loan.id}"


def ics_text_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\n", "\\n")
        .replace(";", "\\;")
        .replace(",", "\\,")
    )


def ics_loan_description(loan: Loan) -> str:
    lines: list[str] = []
    group = loan_group_label(loan)
    if group:
        lines.append(f"Gruppe: {group}")
    borrower = loan_borrower_label(loan)
    if borrower:
        lines.append(f"Ausleihende: {borrower}")
    url = loan_detail_url(loan)
    if url:
        lines.append(f"Link: {url}")
    return ics_text_escape("\n".join(lines))
