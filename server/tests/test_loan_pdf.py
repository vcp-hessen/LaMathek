import pytest

from conftest import app_with_db as _app_with_db, login as _login
from lamathek.db import get_session
from lamathek.services.users import upsert_user_from_oidc
from loan_helpers import (
    add_piece_line,
    borrower_id,
    complete_workflow_step,
    confirm_all_lines,
    create_loan,
    manager_id,
    setup_inventory,
    submit_request,
)


def _bootstrap(app):
    with app.app_context():
        session = get_session()
        upsert_user_from_oidc(
            session, sub="su", name="SU", email=None, force_superuser=True
        )
        session.commit()


weasyprint = pytest.importorskip("weasyprint")


def test_pack_pdf_after_review_complete():
    app, tmp = _app_with_db()
    try:
        app.config["FRONTEND_URL"] = "https://example.test"
        _bootstrap(app)
        client = app.test_client()
        inv_id = setup_inventory(client)
        bor_id = borrower_id(client)
        mgr_id = manager_id(client)

        mt = client.post(
            f"/api/inventories/{inv_id}/material-types",
            json={"name": "Zelt", "tracking": "piece"},
        )
        type_id = mt.get_json()["id"]
        piece = client.post(
            f"/api/inventories/{inv_id}/pieces",
            json={"materialTypeId": type_id, "name": "Jurte"},
        )
        piece_id = piece.get_json()["id"]

        loan = create_loan(client, inv_id, bor_id)
        loan_id = loan.get_json()["id"]
        add_piece_line(client, loan_id, piece_id)
        submit_request(client, loan_id)

        _login(client, "mgr")
        lines = client.get(f"/api/loans/{loan_id}").get_json()["lines"]
        confirm_all_lines(client, loan_id, mgr_id, [lines[0]["id"]])

        denied = client.get(f"/api/loans/{loan_id}/pdf/pack")
        assert denied.status_code == 409

        complete_workflow_step(client, loan_id)
        loan_body = client.get(f"/api/loans/{loan_id}").get_json()
        assert loan_body["phase"] == "pack"

        pdf = client.get(f"/api/loans/{loan_id}/pdf/pack")
        assert pdf.status_code == 200
        assert pdf.mimetype == "application/pdf"
        assert pdf.data[:4] == b"%PDF"
    finally:
        tmp.cleanup()
