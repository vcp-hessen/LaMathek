"""The API contract (#16, ADR 0021): each /api route declares what it answers.

``@responds(Model)`` goes right below the route decorator::

    @loans_bp.get("/loans/<int:loan_id>")
    @responds(LoanDetail)
    @require_login
    def get_loan(user, loan_id): ...

Under test and in the dev server every answer is validated against it (errors
against ``ErrorResponse``); a mismatch raises ``ContractViolation`` instead of
reaching the client. Production does not validate.
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from flask import Flask, Response, current_app, request
from pydantic import TypeAdapter, ValidationError

from lamathek.contract.models import ErrorResponse

JSON = "application/json"


@dataclass(frozen=True)
class Contract:
    status: int
    body: Any
    """Type of the JSON body; None for an empty body."""
    mimetype: str = JSON


class ContractViolation(AssertionError):
    """An answer that does not match its declared model."""


def responds(body: Any, *, status: int = 200, mimetype: str = JSON):
    """Declare the success answer of a route: ``body`` is a model, ``list[Model]``,
    ``Model | None``, ``None`` (empty, use with 204) or ``bytes`` (with a mimetype)."""

    def decorate(view):
        view.api_contract = Contract(status=status, body=body, mimetype=mimetype)
        return view

    return decorate


def contract_of(view) -> Contract | None:
    return getattr(view, "api_contract", None)


@lru_cache(maxsize=None)
def _adapter(body: Any) -> TypeAdapter:
    return TypeAdapter(body)


def _validate_json(body: Any, response: Response, what: str) -> None:
    if not response.is_json:
        raise ContractViolation(f"{what}: expected JSON, got {response.mimetype}")
    try:
        _adapter(body).validate_json(response.get_data(), strict=True)
    except ValidationError as exc:
        raise ContractViolation(f"{what} does not match its model:\n{exc}") from None


def check_response(response: Response) -> None:
    """Raise ContractViolation if an /api answer does not match its contract."""
    what = f"{request.method} {request.path}"
    if response.status_code >= 400:
        _validate_json(ErrorResponse, response, f"{what} → {response.status_code}")
        return
    view = current_app.view_functions.get(request.endpoint) if request.endpoint else None
    contract = contract_of(view)
    if contract is None:
        raise ContractViolation(f"{what}: route {request.endpoint} declares no @responds")
    if contract.mimetype != JSON:
        # Files: 304 is the browser cache at work.
        if response.status_code not in (contract.status, 304):
            raise ContractViolation(f"{what}: status {response.status_code}, declared {contract.status}")
        if response.status_code == contract.status and response.mimetype != contract.mimetype:
            raise ContractViolation(f"{what}: {response.mimetype}, declared {contract.mimetype}")
        return
    if response.status_code != contract.status:
        raise ContractViolation(f"{what}: status {response.status_code}, declared {contract.status}")
    if contract.body is None:
        if response.get_data():
            raise ContractViolation(f"{what}: declared an empty body")
        return
    _validate_json(contract.body, response, what)


def register_contract_check(app: Flask) -> None:
    """Validate answers when testing or debugging (``API_CONTRACT_CHECK`` overrides)."""
    enabled = app.config.get("API_CONTRACT_CHECK")
    if enabled is None:
        enabled = bool(app.config.get("TESTING") or app.config.get("DEBUG"))
    if not enabled:
        return

    @app.after_request
    def _check_contract(response: Response) -> Response:
        if request.path.startswith("/api/") and request.method not in ("HEAD", "OPTIONS"):
            check_response(response)
        return response
