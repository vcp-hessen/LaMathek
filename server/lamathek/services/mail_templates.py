import base64
from datetime import date
from pathlib import Path

from flask import current_app, has_app_context

from lamathek.config import Config
from lamathek.db import get_session
from lamathek.i18n import DEFAULT_LOCALE, message, resolve_locale, t, t_list
from lamathek.models.loan import (
    LINE_STATUS_DRAFT,
    LOAN_KIND_PERMANENT,
    LOAN_PHASE_CLOSED,
    LOAN_PHASE_DRAFT,
    LOAN_PHASE_HANDOVER,
    LOAN_PHASE_PACK,
    LOAN_PHASE_RETURN,
    LOAN_PHASE_RESTOCK,
    LOAN_PHASE_REVIEW,
    is_workflow_loan_phase,
)
from lamathek.services.loan_workflow_steps import open_workflow_step
from lamathek.services.settings import get_installation_settings


def _cfg(name: str, default=None):
    if has_app_context():
        return current_app.config.get(name, default)
    return getattr(Config, name, default)


def _single_line(raw: str) -> str:
    parts = [part.strip() for part in raw.replace("\r", "\n").split("\n") if part.strip()]
    return ", ".join(parts)


def _join_parts(*parts: str) -> str:
    return " · ".join(part for part in parts if part)


def _website_href(raw: str) -> str:
    trimmed = raw.strip()
    if not trimmed:
        return ""
    if trimmed.lower().startswith(("http://", "https://")):
        return trimmed
    return f"https://{trimmed}"


def mail_logo_src() -> str:
    """Inline PNG (same as web/public/app-icon.png) for mail clients without SVG."""
    packaged = (
        Path(__file__).resolve().parent.parent / "templates" / "mail" / "app-icon.png"
    )
    if packaged.is_file():
        encoded = base64.standard_b64encode(packaged.read_bytes()).decode("ascii")
        return f"data:image/png;base64,{encoded}"
    return ""


def mail_base_context() -> dict:
    session = get_session()
    settings = get_installation_settings(session)
    frontend_url = str(_cfg("FRONTEND_URL", "") or "").strip().rstrip("/")
    legal_name = (settings.legal_name or "").strip()
    title = (settings.title or "").strip()
    website_raw = (settings.website or "").strip()
    website_href = _website_href(website_raw)
    provider_label = legal_name or title
    impressum_url = f"{frontend_url}/impressum" if frontend_url else ""
    privacy_url = f"{frontend_url}/datenschutz" if frontend_url else ""
    legal_address = _single_line(settings.legal_address or "")
    contact_email = (settings.email or "").strip()
    phone = (settings.phone or "").strip()
    represented_by = _single_line(settings.represented_by or "")
    register = _single_line(settings.register or "")
    footer_identity = _join_parts(legal_name, legal_address)
    footer_meta = _join_parts(represented_by, register)
    locale = resolve_locale(DEFAULT_LOCALE)
    return {
        "installation_title": settings.title,
        "installation_subtitle": settings.subtitle,
        "frontend_url": frontend_url,
        "logo_src": mail_logo_src(),
        "provider_label": provider_label,
        "website_raw": website_raw,
        "website_href": website_href,
        "impressum_url": impressum_url,
        "privacy_url": privacy_url,
        "legal_name": legal_name,
        "legal_address": legal_address,
        "contact_email": contact_email,
        "phone": phone,
        "represented_by": represented_by,
        "register": register,
        "footer_identity": footer_identity,
        "footer_meta": footer_meta,
        "html_lang": t("mail.htmlLang", locale=locale),
        "impressum_label": t("mail.impressum", locale=locale),
        "privacy_label": t("mail.privacy", locale=locale),
    }


def format_mail_subject(raw_subject: str, bracket_label: str) -> str:
    subject = raw_subject.strip()
    label = bracket_label.strip()
    if not label:
        return subject
    prefix = f"[{label}] "
    if subject.startswith(prefix) or subject.startswith(f"[{label}]"):
        return subject
    return f"{prefix}{subject}"


_BLANK_GROUP = {"", "—", "-"}


def _format_date(value: date | None, locale: str) -> str:
    if value is None:
        return ""
    if resolve_locale(locale) == "de":
        return value.strftime("%d.%m.%Y")
    return value.isoformat()


def _person_name(user) -> str:
    if user is None:
        return ""
    return (user.name or user.email or "").strip()


def _loan_title(loan) -> str:
    event = (loan.event.name or "").strip() if loan.event is not None else ""
    if event:
        return event
    group = (loan.group.name or "").strip() if loan.group is not None else ""
    if group in _BLANK_GROUP:
        return ""
    return group


def _workflow_step_label(step: str | None, locale: str) -> str:
    if not step:
        return ""
    key = f"mail.workflowStep.{step}"
    label = t(key, locale=locale)
    if label == key:
        return step
    return label


def _loan_phase_label(phase: str, locale: str) -> str:
    from lamathek.models.loan import is_workflow_loan_phase

    if not is_workflow_loan_phase(phase):
        key = f"mail.loanPhase.{phase}"
        label = t(key, locale=locale)
        if label == key:
            return phase
        return label
    workflow = _workflow_step_label(phase, locale)
    if workflow and workflow != phase:
        return workflow
    key = f"mail.loanPhase.{phase}"
    label = t(key, locale=locale)
    if label == key:
        return phase
    return label


def _line_status_label(status: str, locale: str) -> str:
    key = f"mail.lineStatus.{status}"
    label = t(key, locale=locale)
    if label == key:
        return status
    return label


def _line_item(line, locale: str, *, changed: bool = False) -> dict:
    origin = (line.origin_set_name or "").strip()
    if line.piece is not None:
        name = line.piece.name
        title = (
            t("mail.linePieceFromSet", locale=locale, name=name, set=origin)
            if origin
            else t("mail.linePiece", locale=locale, name=name)
        )
    elif line.material_type is not None:
        name = line.material_type.name
        quantity = line.quantity
        title = (
            t(
                "mail.lineStockFromSet",
                locale=locale,
                name=name,
                quantity=quantity,
                set=origin,
            )
            if origin
            else t("mail.lineStock", locale=locale, name=name, quantity=quantity)
        )
    else:
        title = t("mail.lineFallback", locale=locale, id=line.id)
    status_text = t(
        "mail.lineStatusLabel",
        locale=locale,
        status=_line_status_label(line.status, locale),
    )
    reason = (line.reason or "").strip()
    detail_parts = [status_text]
    if reason:
        detail_parts.append(t("mail.reason", locale=locale, reason=reason))
    status_label = _line_status_label(line.status, locale)
    material_subtitle = ""
    if line.piece is not None:
        material_subtitle = _line_material_type_name(line)
    return {
        "title": title,
        "detail": " · ".join(detail_parts),
        "status": status_label,
        "changed": changed,
        "reason": reason,
        "material_subtitle": material_subtitle,
    }


_WORKFLOW_TRAIL_STEPS = (
    LOAN_PHASE_REVIEW,
    LOAN_PHASE_PACK,
    LOAN_PHASE_HANDOVER,
    LOAN_PHASE_RETURN,
    LOAN_PHASE_RESTOCK,
)


def _workflow_trail(loan, locale: str, mail_step: str | None) -> list[dict]:
    phase = loan.phase
    if phase == "closed":
        current_index = len(_WORKFLOW_TRAIL_STEPS)
    elif phase in _WORKFLOW_TRAIL_STEPS:
        current_index = _WORKFLOW_TRAIL_STEPS.index(phase)
    else:
        current_index = -1

    trail: list[dict] = []
    for index, step in enumerate(_WORKFLOW_TRAIL_STEPS):
        if phase == "closed" or index < current_index:
            state = "done"
        elif index == current_index:
            state = "current"
        else:
            state = "upcoming"
        trail.append(
            {
                "label": _workflow_step_label(step, locale),
                "state": state,
                "closed_here": bool(mail_step and mail_step == step),
            }
        )
    return trail


def _loan_dates_line(loan, locale: str) -> str:
    pickup = _format_date(loan.pickup_on, locale)
    return_date = _format_date(loan.return_on, locale)
    label = t("mail.fact.date", locale=locale)
    if loan.kind == LOAN_KIND_PERMANENT:
        if pickup:
            return f"{label}: {pickup}"
        return ""
    if pickup and return_date:
        return f"{label}: {pickup} - {return_date}"
    if pickup:
        return f"{label}: {pickup}"
    if return_date:
        return f"{label}: {return_date}"
    return ""


def _loan_mail_header(loan, locale: str) -> dict:
    inventory = (loan.inventory.name or "").strip() if loan.inventory is not None else ""
    meta_parts: list[str] = []
    borrower = _person_name(loan.borrower_user)
    if borrower:
        meta_parts.append(f"{t('mail.fact.borrower', locale=locale)} {borrower}")
    contact = _person_name(loan.contact_user)
    if contact:
        meta_parts.append(f"{t('mail.fact.contact', locale=locale)} {contact}")
    group = (loan.group.name or "").strip() if loan.group is not None else ""
    if group not in _BLANK_GROUP:
        meta_parts.append(f"{t('mail.fact.group', locale=locale)} {group}")
    return {
        "inventory_name": inventory,
        "meta_line": _join_parts(*meta_parts),
        "dates_line": _loan_dates_line(loan, locale),
    }


def _loan_display_title(loan) -> str:
    event = (loan.event.name or "").strip() if loan.event is not None else ""
    if event:
        return event
    group = (loan.group.name or "").strip() if loan.group is not None else ""
    if group not in _BLANK_GROUP:
        return group
    return _loan_title(loan) or ""


def _line_material_type_name(line) -> str:
    if line.material_type is not None:
        return (line.material_type.name or "").strip()
    piece = line.piece
    if piece is not None and piece.material_type is not None:
        return (piece.material_type.name or "").strip()
    return ""


_PHASE_AFTER_MAIL_STEP = {
    LOAN_PHASE_REVIEW: LOAN_PHASE_PACK,
    LOAN_PHASE_PACK: LOAN_PHASE_HANDOVER,
    LOAN_PHASE_HANDOVER: LOAN_PHASE_RETURN,
    LOAN_PHASE_RETURN: LOAN_PHASE_RESTOCK,
    LOAN_PHASE_RESTOCK: LOAN_PHASE_CLOSED,
}


def _phase_after_mail_step(mail_step: str | None) -> str | None:
    if mail_step is None:
        return None
    return _PHASE_AFTER_MAIL_STEP.get(mail_step)


def _next_step_hint(phase_key: str, audience: str, locale: str) -> str:
    if phase_key == LOAN_PHASE_DRAFT:
        hint_key = "mail.nextStep.draft"
        label = t(hint_key, locale=locale)
        return label if label != hint_key else ""

    audience_key = f"mail.nextStep.{phase_key}.{audience}"
    label = t(audience_key, locale=locale)
    if label != audience_key:
        return label

    legacy_key = f"mail.nextStep.{phase_key}"
    legacy = t(legacy_key, locale=locale)
    if legacy != legacy_key:
        return legacy
    return ""


def _loan_mail_summary(
    loan,
    locale: str,
    *,
    mail_step: str | None,
    audience: str,
) -> dict:
    hint_phase = _phase_after_mail_step(mail_step)
    if hint_phase is None:
        phase = loan.phase
        if phase == LOAN_PHASE_CLOSED:
            hint_phase = "closed"
        elif phase == LOAN_PHASE_DRAFT:
            hint_phase = "draft"
        elif is_workflow_loan_phase(phase):
            hint_phase = phase
        else:
            open_step = open_workflow_step(loan)
            hint_phase = open_step or "review"
    return {
        "workflow_trail": _workflow_trail(loan, locale, mail_step),
        "loan_mail_header": _loan_mail_header(loan, locale),
        "loan_display_title": _loan_display_title(loan),
        "next_step_hint": _next_step_hint(hint_phase, audience, locale),
    }


_STEP_MAIL_ACTION = {
    "review": "confirm",
    "pack": "pack",
    "handover": "pickup",
    "return": "report_return",
    "restock": "restock",
}


def _use_receipt_copy(mail_step: str | None, action: str) -> bool:
    if not mail_step:
        return False
    if action == "changes":
        return True
    return _STEP_MAIL_ACTION.get(mail_step) == action


def _step_receipt_message(mail_step: str, audience: str, locale: str) -> dict | None:
    found = message(f"mail.stepReceipt.{mail_step}.{audience}", locale=locale)
    return found if isinstance(found, dict) else None


def _loan_message(action: str, audience: str, variant: str, locale: str) -> dict:
    if variant:
        specific = message(f"mail.loan.{action}.{audience}{variant}", locale=locale)
        if specific is not None:
            return specific
    found = message(f"mail.loan.{action}.{audience}", locale=locale)
    if found is not None:
        return found
    return message("mail.loan.fallback", locale=locale) or {}


def render_loan_action_mail(
    session,
    loan,
    action: str,
    line_ids: list[int],
    *,
    actor,
    audience: str,
    variant: str = "",
    locale: str = DEFAULT_LOCALE,
    mail_step: str | None = None,
) -> tuple[str, str, str]:
    del session
    locale = resolve_locale(locale)
    copy = _loan_message(action, audience, variant, locale)
    step_label = _workflow_step_label(mail_step, locale) or "—"
    values = {
        "borrower": _person_name(loan.borrower_user),
        "actor": _person_name(actor),
        "inventory": loan.inventory.name if loan.inventory is not None else "",
        "step": step_label,
    }
    if _use_receipt_copy(mail_step, action) and step_label != "—" and mail_step:
        receipt = _step_receipt_message(mail_step, audience, locale)
        if receipt is not None:
            subject = str(receipt.get("subject", t("mail.loan.fallback.subject", locale=locale)))
            subject = subject.format(**values)
            heading = str(receipt.get("heading", t("mail.loan.fallback.heading", locale=locale)))
            heading = heading.format(**values)
            body = receipt.get("body")
            if isinstance(body, list):
                paragraphs = [str(part).format(**values) for part in body]
            else:
                paragraphs = t_list("mail.loan.fallback.body", locale=locale)
        else:
            subject = t("mail.receipt.subject", locale=locale, step=step_label)
            heading = t("mail.receipt.heading", locale=locale, step=step_label)
            if audience == "managers":
                name = values["borrower"] or values["actor"]
            else:
                name = values["actor"]
            paragraphs = [t("mail.receipt.body", locale=locale, name=name)]
    else:
        subject = str(copy.get("subject", t("mail.loan.fallback.subject", locale=locale)))
        subject = subject.format(**values)
        heading = str(copy.get("heading", t("mail.loan.fallback.heading", locale=locale)))
        heading = heading.format(**values)
        body = copy.get("body")
        if isinstance(body, list):
            paragraphs = [str(part).format(**values) for part in body]
        else:
            paragraphs = t_list("mail.loan.fallback.body", locale=locale)
    loan_name = _loan_title(loan)
    if loan_name:
        subject = t(
            "mail.subjectWithLoan",
            locale=locale,
            subject=subject,
            loan_name=loan_name,
        )
    changed_ids = set(line_ids)
    overview_lines = sorted(
        [line for line in loan.lines if line.status != LINE_STATUS_DRAFT],
        key=lambda line: line.id,
    )
    items = [
        _line_item(line, locale, changed=line.id in changed_ids)
        for line in overview_lines
    ]
    frontend_url = str(_cfg("FRONTEND_URL", "") or "").strip().rstrip("/")
    action_url = (
        f"{frontend_url}/inventories/{loan.inventory_id}/loans/{loan.id}"
        if frontend_url
        else ""
    )
    summary = _loan_mail_summary(loan, locale, mail_step=mail_step, audience=audience)
    inventory_name = (loan.inventory.name or "").strip() if loan.inventory is not None else ""
    return render_mail(
        "loan_action",
        locale=locale,
        subject=subject,
        subject_bracket=inventory_name,
        heading=heading,
        paragraphs=paragraphs,
        **summary,
        items=items,
        items_heading=t("mail.section.positions", locale=locale) if items else "",
        phase_heading=t("mail.section.phase", locale=locale),
        summary_heading=t("mail.section.summary", locale=locale),
        next_heading=t("mail.section.next", locale=locale),
        table_position_label=t("mail.table.position", locale=locale),
        table_status_label=t("mail.table.status", locale=locale),
        line_changed_label=t("mail.lineChanged", locale=locale),
        action_url=action_url,
        action_label=t("mail.openLoan", locale=locale) if action_url else "",
    )


def preview_loan_action_mail(
    session,
    loan,
    action: str,
    line_ids: list[int],
    *,
    actor,
    audience: str,
    variant: str = "",
    locale: str = DEFAULT_LOCALE,
    mail_step: str | None = None,
) -> dict:
    subject, text, html = render_loan_action_mail(
        session,
        loan,
        action,
        line_ids,
        actor=actor,
        audience=audience,
        variant=variant,
        locale=locale,
        mail_step=mail_step,
    )
    return {"subject": subject, "text": text, "html": html}


def render_mail(template: str, **context) -> tuple[str, str, str]:
    """Return (subject, plain text, html) for a mail template name without extension."""
    locale = resolve_locale(context.get("locale") if isinstance(context.get("locale"), str) else None)
    variables = {
        **mail_base_context(),
        "html_lang": t("mail.htmlLang", locale=locale),
        "impressum_label": t("mail.impressum", locale=locale),
        "privacy_label": t("mail.privacy", locale=locale),
        **context,
    }
    env = current_app.jinja_env
    raw_subject = (
        env.get_template(f"mail/{template}.subject.txt").render(variables).strip()
    )
    bracket = variables.get("subject_bracket")
    if bracket is None:
        bracket = variables.get("installation_title", "")
    subject = format_mail_subject(raw_subject, str(bracket or ""))
    text = env.get_template(f"mail/{template}.txt").render(variables)
    html = env.get_template(f"mail/{template}.html").render(variables)
    return subject, text, html
