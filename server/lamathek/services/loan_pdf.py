"""Verleih PDF lists (pack, handover, return)."""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

import qrcode
from flask import current_app, has_app_context
from weasyprint import HTML

from lamathek.config import Config
from lamathek.models.loan import (
    LINE_STATUS_DRAFT,
    LOAN_PHASE_CLOSED,
    LOAN_PHASE_HANDOVER,
    LOAN_PHASE_PACK,
    LOAN_PHASE_RESTOCK,
    LOAN_PHASE_RETURN,
    Loan,
)
from lamathek.models.user import User
from lamathek.services.loan_display import loan_detail_url, loan_display_title, loan_group_label
from lamathek.services.settings import get_installation_settings
from sqlalchemy.orm import Session

_PDF_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "pdf"

PdfKind = Literal["pack", "handover", "return"]

_PDF_TITLES: dict[PdfKind, str] = {
    "pack": "Packliste",
    "handover": "Abholliste",
    "return": "Rückgabeliste",
}

_PHASE_MIN: dict[PdfKind, frozenset[str]] = {
    "pack": frozenset(
        {LOAN_PHASE_PACK, LOAN_PHASE_HANDOVER, LOAN_PHASE_RETURN, LOAN_PHASE_RESTOCK, LOAN_PHASE_CLOSED}
    ),
    "handover": frozenset(
        {LOAN_PHASE_HANDOVER, LOAN_PHASE_RETURN, LOAN_PHASE_RESTOCK, LOAN_PHASE_CLOSED}
    ),
    "return": frozenset({LOAN_PHASE_RETURN, LOAN_PHASE_RESTOCK, LOAN_PHASE_CLOSED}),
}

_MAIL_STEP_PDF: dict[str, PdfKind] = {
    "review": "pack",
    "pack": "handover",
    "handover": "return",
}


def _cfg(name: str, default=None):
    if has_app_context():
        return current_app.config.get(name, default)
    return getattr(Config, name, default)


def pdf_kind_for_mail_step(mail_step: str | None) -> PdfKind | None:
    if not mail_step:
        return None
    return _MAIL_STEP_PDF.get(mail_step)


def pdf_access_allowed(loan: Loan, kind: PdfKind, *, mail_step: str | None = None) -> bool:
    if mail_step is not None and _MAIL_STEP_PDF.get(mail_step) == kind:
        return True
    return loan.phase in _PHASE_MIN[kind]


@dataclass(frozen=True)
class PdfRow:
    item_label: str
    material_type_name: str
    set_label: str
    sort_key: tuple[str, str]


def _format_loan_date(value: date | None) -> str:
    if value is None:
        return "—"
    return value.strftime("%d.%m.%Y")


def _instance_now() -> datetime:
    """Wall clock in LAMATHEK_INSTANCE_TIMEZONE from UTC (unabhängig von TZ=)."""
    tz_name = _cfg("INSTANCE_TIMEZONE", Config.INSTANCE_TIMEZONE)
    return datetime.now(timezone.utc).astimezone(ZoneInfo(tz_name))


def _instance_generator_label(instance_name: str, instance_subtitle: str) -> str:
    title = instance_name.strip() or "LaMathek"
    subtitle = instance_subtitle.strip()
    if subtitle:
        return f"LaMathek — {title}, {subtitle}"
    return f"LaMathek — {title}"


def _qr_data_uri(url: str) -> str:
    if not url:
        return ""
    img = qrcode.make(url, box_size=4, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    encoded = base64.standard_b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def pdf_rows_for_loan(loan: Loan) -> list[dict]:
    rows: list[PdfRow] = []
    for line in loan.lines:
        if line.status == LINE_STATUS_DRAFT:
            continue
        origin = (line.origin_set_name or "").strip()
        if line.piece is not None:
            mt_name = (
                line.piece.material_type.name.strip()
                if line.piece.material_type is not None
                else ""
            )
            item_label = line.piece.name.strip()
            rows.append(
                PdfRow(
                    item_label=item_label,
                    material_type_name=mt_name,
                    set_label=origin,
                    sort_key=(mt_name.casefold(), item_label.casefold()),
                )
            )
        elif line.material_type is not None and line.quantity is not None:
            mt_name = line.material_type.name.strip()
            qty = line.quantity
            item_label = f"{qty}×"
            rows.append(
                PdfRow(
                    item_label=item_label,
                    material_type_name=mt_name,
                    set_label=origin,
                    sort_key=(mt_name.casefold(), f"{qty:04d}"),
                )
            )
    rows.sort(key=lambda row: row.sort_key)
    return [
        {
            "itemLabel": row.item_label,
            "materialTypeName": row.material_type_name,
            "setLabel": row.set_label,
        }
        for row in rows
    ]


def pdf_filename(loan: Loan, kind: PdfKind) -> str:
    title = loan_display_title(loan).replace("/", "-")[:40]
    return f"lamathek-{kind}-{loan.id}-{title}.pdf"


def _pdf_document_meta(
    loan: Loan,
    kind: PdfKind,
    *,
    instance_name: str,
    instance_subtitle: str,
    contact_name: str,
    borrower_name: str,
) -> dict[str, str]:
    list_title = _PDF_TITLES[kind]
    loan_title = loan_display_title(loan)
    inventory_name = (loan.inventory.name or "").strip() if loan.inventory else ""
    group_name = loan_group_label(loan)
    pickup = _format_loan_date(loan.pickup_on)
    ret = _format_loan_date(loan.return_on)
    created = _instance_now()

    pdf_title = f"{list_title} — {loan_title}"
    description_lines = [
        f"Verleih: {loan_title}",
        f"Gruppe: {group_name or '—'}",
    ]
    if borrower_name:
        description_lines.append(f"Ausleihende*r: {borrower_name}")
    if inventory_name:
        description_lines.append(f"Inventar: {inventory_name}")
    description_lines.append(f"Datum: {pickup} – {ret}")
    if contact_name:
        description_lines.append(f"Materialwart*in: {contact_name}")

    keyword_parts = [list_title, "Verleih", "LaMathek"]
    if inventory_name:
        keyword_parts.append(inventory_name)
    if group_name:
        keyword_parts.append(group_name)

    pdf_author = contact_name.strip() or "—"

    return {
        "pdf_title": pdf_title,
        "pdf_author": pdf_author,
        "pdf_generator": _instance_generator_label(instance_name, instance_subtitle),
        "pdf_description_lines": description_lines,
        "pdf_keywords": ", ".join(keyword_parts),
        "pdf_created_iso": created.isoformat(timespec="seconds"),
        "generated_at": created.strftime("%d.%m.%Y %H:%M"),
    }


def render_loan_pdf(session: Session, loan: Loan, kind: PdfKind) -> bytes:
    detail_url = loan_detail_url(loan)
    settings = get_installation_settings(session)
    instance_name = (settings.title or "").strip() or "LaMathek"
    instance_subtitle = (settings.subtitle or "").strip()
    contact_name = ""
    if loan.contact_user is not None:
        contact_name = (loan.contact_user.name or loan.contact_user.email or "").strip()
    borrower_name = ""
    if loan.borrower_user is not None:
        borrower_name = (loan.borrower_user.name or loan.borrower_user.email or "").strip()
    doc_meta = _pdf_document_meta(
        loan,
        kind,
        instance_name=instance_name,
        instance_subtitle=instance_subtitle,
        contact_name=contact_name,
        borrower_name=borrower_name,
    )
    context = {
        "title": _PDF_TITLES[kind],
        **doc_meta,
        "loan_title": loan_display_title(loan),
        "group_name": loan_group_label(loan),
        "inventory_name": (loan.inventory.name or "").strip() if loan.inventory else "",
        "borrower_name": borrower_name,
        "contact_name": contact_name,
        "pickup_on": _format_loan_date(loan.pickup_on),
        "return_on": _format_loan_date(loan.return_on),
        "instance_name": instance_name,
        "rows": pdf_rows_for_loan(loan),
        "show_signature": kind in {"handover", "return"},
        "qr_src": _qr_data_uri(detail_url),
        "detail_url": detail_url,
    }
    env = current_app.jinja_env
    html = env.get_template(f"pdf/{kind}_list.html").render(context)
    return HTML(string=html, base_url=_PDF_TEMPLATE_DIR.as_uri() + "/").write_pdf()


def pdf_attachment_for_mail(
    session: Session, loan: Loan, mail_step: str | None
) -> tuple[str, bytes, str] | None:
    kind = pdf_kind_for_mail_step(mail_step)
    if kind is None or not pdf_access_allowed(loan, kind, mail_step=mail_step):
        return None
    data = render_loan_pdf(session, loan, kind)
    return (pdf_filename(loan, kind), data, "application/pdf")
