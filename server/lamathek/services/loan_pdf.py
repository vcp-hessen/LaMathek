"""Verleih PDF lists (pack, handover, return)."""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from typing import Literal

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
from lamathek.services.loan_display import loan_detail_url, loan_display_title
from sqlalchemy.orm import Session

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
    material_type_name: str
    piece_name: str
    set_label: str
    sort_key: tuple[str, str]


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
            piece_name = line.piece.name.strip()
            rows.append(
                PdfRow(
                    material_type_name=mt_name,
                    piece_name=piece_name,
                    set_label=origin,
                    sort_key=(mt_name.casefold(), piece_name.casefold()),
                )
            )
        elif line.material_type is not None and line.quantity is not None:
            mt_name = line.material_type.name.strip()
            piece_name = f"{line.quantity}× {mt_name}"
            rows.append(
                PdfRow(
                    material_type_name=mt_name,
                    piece_name=piece_name,
                    set_label=origin,
                    sort_key=(mt_name.casefold(), piece_name.casefold()),
                )
            )
    rows.sort(key=lambda row: row.sort_key)
    return [
        {
            "materialTypeName": row.material_type_name,
            "pieceName": row.piece_name,
            "setLabel": row.set_label,
        }
        for row in rows
    ]


def pdf_filename(loan: Loan, kind: PdfKind) -> str:
    title = loan_display_title(loan).replace("/", "-")[:40]
    return f"lamathek-{kind}-{loan.id}-{title}.pdf"


def render_loan_pdf(session: Session, loan: Loan, kind: PdfKind) -> bytes:
    del session
    detail_url = loan_detail_url(loan)
    context = {
        "title": _PDF_TITLES[kind],
        "loan_title": loan_display_title(loan),
        "inventory_name": (loan.inventory.name or "").strip() if loan.inventory else "",
        "borrower_name": (loan.borrower_user.name or loan.borrower_user.email or "").strip()
        if loan.borrower_user
        else "",
        "rows": pdf_rows_for_loan(loan),
        "show_signature": kind in {"handover", "return"},
        "qr_src": _qr_data_uri(detail_url),
        "detail_url": detail_url,
    }
    env = current_app.jinja_env
    html = env.get_template(f"pdf/{kind}_list.html").render(context)
    return HTML(string=html).write_pdf()


def pdf_attachment_for_mail(
    session: Session, loan: Loan, mail_step: str | None
) -> tuple[str, bytes, str] | None:
    kind = pdf_kind_for_mail_step(mail_step)
    if kind is None or not pdf_access_allowed(loan, kind, mail_step=mail_step):
        return None
    data = render_loan_pdf(session, loan, kind)
    return (pdf_filename(loan, kind), data, "application/pdf")
