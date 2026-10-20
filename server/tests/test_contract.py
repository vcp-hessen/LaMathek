"""API contract (#16): routes declare their answers, the check catches drift,
the OpenAPI document is current, and the routes the other tests rarely call
answer as declared."""

import io
from typing import get_args

import pytest
from flask import jsonify
from PIL import Image

from lamathek.bundesland import CALENDAR_BUNDESLAND_CODES
from lamathek.contract import ContractViolation, contract_of, models as api, responds
from lamathek.contract.openapi import OPENAPI_PATH, export_app, render_openapi
from lamathek.models.loan import VALID_LINE_STATUSES, VALID_LOAN_PHASES

from conftest import app_with_db, login
from test_availability import World, _day


def test_every_api_route_declares_its_answer():
    app = export_app()
    undeclared = [
        rule.rule
        for rule in app.url_map.iter_rules()
        if rule.rule.startswith("/api/") and contract_of(app.view_functions[rule.endpoint]) is None
    ]
    assert undeclared == []


def test_openapi_document_is_current():
    assert OPENAPI_PATH.read_text(encoding="utf-8") == render_openapi(export_app()), (
        "lamathek/domain/openapi.json is stale: run `lamathek openapi`, then "
        "`npm run generate:api` in web/"
    )


def test_enumerations_match_the_domain():
    assert set(get_args(api.LoanPhase.__value__)) == VALID_LOAN_PHASES
    assert set(get_args(api.LoanLineStatus.__value__)) == VALID_LINE_STATUSES
    assert set(get_args(api.CalendarBundesland.__value__)) == CALENDAR_BUNDESLAND_CODES


@pytest.fixture
def drift_app():
    app, tmp = app_with_db()

    def add(path, view):
        app.add_url_rule(path, path.strip("/").replace("/", "_"), view)

    add("/api/t/ok", responds(api.Health)(lambda: jsonify({"status": "ok"})))
    add("/api/t/missing-key", responds(api.AuthMode)(lambda: jsonify({})))
    add("/api/t/extra-key", responds(api.Health)(lambda: jsonify({"status": "ok", "x": 1})))
    add("/api/t/wrong-type", responds(api.Category)(lambda: jsonify({"id": "1", "name": "A"})))
    add("/api/t/wrong-status", responds(api.Health, status=201)(lambda: jsonify({"status": "ok"})))
    add("/api/t/undeclared", lambda: jsonify({"status": "ok"}))
    add("/api/t/bad-error", responds(api.Health)(lambda: (jsonify({"message": "no"}), 400)))
    add("/api/t/good-error", responds(api.Health)(lambda: (jsonify({"error": "nope"}), 409)))
    yield app.test_client()
    tmp.cleanup()


def test_the_check_accepts_matching_answers(drift_app):
    assert drift_app.get("/api/t/ok").status_code == 200
    assert drift_app.get("/api/t/good-error").status_code == 409


@pytest.mark.parametrize(
    "path, message",
    [
        ("/api/t/missing-key", "devBypass"),
        ("/api/t/extra-key", "Extra inputs are not permitted"),
        ("/api/t/wrong-type", "valid integer"),
        ("/api/t/wrong-status", "status 200, declared 201"),
        ("/api/t/undeclared", "declares no @responds"),
        ("/api/t/bad-error", "error"),
    ],
)
def test_the_check_catches_drift(drift_app, path, message):
    with pytest.raises(ContractViolation, match=message):
        drift_app.get(path)


def _jpeg() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (16, 12), color=(10, 120, 40)).save(buffer, format="JPEG")
    return buffer.getvalue()


def _upload(client, path: str) -> int:
    response = client.post(path, data={"file": (io.BytesIO(_jpeg()), "f.jpg", "image/jpeg")})
    assert response.status_code == 201, response.get_json()
    return response.get_json()["id"]


def test_rarely_called_routes_answer_as_declared(tmp_path, monkeypatch):
    """Every request below is checked against its model by the contract check."""
    monkeypatch.setenv("MEDIA_PATH", str(tmp_path / "media"))
    w = World()
    c = w.client
    try:
        assert c.get("/api/health").status_code == 200

        # Inventar, Set, Mengenposten, Schaden: photos, cover, deletion.
        w.as_("mgr")
        inv_photo = _upload(c, f"/api/inventories/{w.inv}/photos")
        _upload(c, f"/api/inventories/{w.inv}/photos")
        assert c.post(f"/api/photos/{inv_photo}/make-cover").status_code == 200
        assert c.delete(f"/api/photos/{inv_photo}").status_code == 204

        kohte = w.piece("Kohte 1")
        jurte = c.post(f"/api/inventories/{w.inv}/sets", json={"name": "Jurte"}).get_json()
        assert c.patch(f"/api/sets/{jurte['id']}", json={"name": "Jurte 1"}).status_code == 200
        _upload(c, f"/api/sets/{jurte['id']}/photos")

        heringe = w.stock("Hering", 20)
        stocks = c.get(f"/api/inventories/{w.inv}/stocks").get_json()
        lot_id = next(r for r in stocks if r["materialTypeId"] == heringe)["lots"][0]["id"]
        _upload(c, f"/api/inventories/{w.inv}/stock-lots/{lot_id}/photos")
        spare = c.post(
            f"/api/inventories/{w.inv}/stocks/{heringe}/lots", json={"quantity": 3}
        ).get_json()
        spare_lot = max(lot["id"] for lot in spare["lots"])
        assert c.delete(f"/api/inventories/{w.inv}/stock-lots/{spare_lot}").status_code == 204

        damage = c.post(
            f"/api/pieces/{kohte}/damages",
            json={"recordedOn": _day(0), "severe": False, "note": "Riss"},
        ).get_json()
        _upload(c, f"/api/damages/{damage['id']}/photos")

        # Verleih: Box, Ersatz, Mailvorschau, Kalender.
        assert c.get("/api/users/borrowers").status_code == 200
        w.as_("borrower")
        assert c.patch("/api/me", json={"phone": "+49 6421 1"}).status_code == 200
        added = c.post(
            f"/api/inventories/{w.inv}/loans/draft-lines",
            json={"materialTypeId": heringe, "quantity": 2},
        )
        assert added.status_code == 201, added.get_json()
        draft = c.get(f"/api/inventories/{w.inv}/loans/draft")
        assert draft.status_code == 200 and draft.get_json()["id"] == added.get_json()["id"]
        assert c.get("/api/groups").status_code == 200
        assert c.get("/api/events").status_code == 200

        kohte_2 = w.piece("Kohte 2")
        loan = w.loan([{"pieceId": kohte}], 3, 5)
        assert w.confirm(loan).status_code == 200
        line = w.detail(loan)["lines"][0]["id"]
        replaced = c.post(
            f"/api/loans/{loan}/actions/replace",
            json={"originalLineId": line, "reason": "Riss", "replacement": {"pieceId": kohte_2}},
        )
        assert replaced.status_code == 200, replaced.get_json()
        preview = c.get(f"/api/loans/{loan}/mail-preview", query_string={"action": "confirm"})
        assert preview.status_code == 200, preview.get_json()

        assert c.get(f"/api/inventories/{w.inv}/calendar").status_code == 200
        assert c.get("/api/me/calendar/contact").status_code == 200
        feed = c.post(
            "/api/me/calendar-feeds",
            json={"label": "Lager", "scope": "contact", "inventoryId": w.inv},
        )
        assert feed.status_code == 201, feed.get_json()
        login(c, "nobody")
        ics = c.get(feed.get_json()["path"])
        assert ics.status_code == 200 and b"BEGIN:VCALENDAR" in ics.data
    finally:
        w.close()
