from datetime import date, timedelta

from lamathek.db import get_session
from lamathek.services.users import upsert_user_from_oidc, user_by_id

from conftest import login as _login


def borrower_id(client, sub: str = "borrower") -> int:
    with client.application.app_context():
        session = get_session()
        user = upsert_user_from_oidc(
            session, sub=sub, name=sub, email=f"{sub}@test.example", force_superuser=False
        )
        user.phone = "+491234567890"
        session.commit()
        return user.id


def manager_id(client, sub: str = "mgr") -> int:
    with client.application.app_context():
        session = get_session()
        user = upsert_user_from_oidc(
            session, sub=sub, name=sub, email=f"{sub}@test.example", force_superuser=False
        )
        session.commit()
        return user.id


def setup_inventory(client, *, visibility: str = "internal") -> int:
    _login(client, "su")
    inv = client.post(
        "/api/inventories",
        json={"name": "Donnerskopf", "visibility": visibility},
    )
    assert inv.status_code == 201
    inv_id = inv.get_json()["id"]
    mgr = manager_id(client)
    perm = client.put(
        f"/api/inventories/{inv_id}/permissions",
        json={"userIds": [mgr]},
    )
    assert perm.status_code == 200
    return inv_id


def _user_sub(client, user_id: int) -> str:
    with client.application.app_context():
        user = user_by_id(get_session(), user_id)
        assert user is not None
        return user.oidc_sub


def _grant_reader_if_internal(client, inv_id: int, user_id: int) -> None:
    _login(client, "su")
    inventory = client.get(f"/api/inventories/{inv_id}").get_json()
    if inventory.get("visibility") == "active":
        return
    current = client.get(f"/api/inventories/{inv_id}/permissions").get_json()
    manage_ids = [user["id"] for user in current["users"]]
    if user_id in manage_ids:
        return
    reader_ids = [user["id"] for user in current.get("readers", [])]
    if user_id not in reader_ids:
        reader_ids.append(user_id)
    if not manage_ids:
        manage_ids = [manager_id(client)]
    saved = client.put(
        f"/api/inventories/{inv_id}/permissions",
        json={"userIds": manage_ids, "readerUserIds": reader_ids},
    )
    assert saved.status_code == 200, saved.get_json()


def create_loan(
    client,
    inv_id: int,
    borrower_user_id: int,
    *,
    as_borrower: bool = True,
    grant_read: bool = True,
    **extra,
):
    if as_borrower and grant_read:
        _grant_reader_if_internal(client, inv_id, borrower_user_id)
    if as_borrower:
        _login(client, _user_sub(client, borrower_user_id))
    payload = {"groupName": "Stamm A", "borrowerUserId": borrower_user_id, **extra}
    return client.post(f"/api/inventories/{inv_id}/loans", json=payload)


def add_piece_line(client, loan_id: int, piece_id: int):
    return client.post(f"/api/loans/{loan_id}/lines", json={"pieceId": piece_id})


def submit_request(client, loan_id: int):
    start = date.today() + timedelta(days=7)
    end = start + timedelta(days=14)
    return client.post(
        f"/api/loans/{loan_id}/actions/request",
        json={"pickupOn": start.isoformat(), "returnOn": end.isoformat()},
    )


def confirm_all_lines(client, loan_id: int, contact_user_id: int, line_ids: list[int]):
    patched = client.patch(
        f"/api/loans/{loan_id}",
        json={"contactUserId": contact_user_id},
    )
    assert patched.status_code == 200, patched.get_json()
    return client.post(
        f"/api/loans/{loan_id}/actions/confirm",
        json={"lineIds": line_ids},
    )


def complete_workflow_step(client, loan_id: int):
    return client.post(f"/api/loans/{loan_id}/actions/complete-step")


def pack_lines(client, loan_id: int, line_ids: list[int]):
    return client.post(
        f"/api/loans/{loan_id}/actions/pack",
        json={"lineIds": line_ids},
    )


def pickup_lines(client, loan_id: int, line_ids: list[int]):
    return client.post(
        f"/api/loans/{loan_id}/actions/pickup",
        json={"lineIds": line_ids},
    )


def confirm_pickup_restock(
    client,
    loan_id: int,
    mgr_id: int,
    line_ids: list[int],
    *,
    as_manager: bool = True,
):
    _login(client, "borrower")
    submit_request(client, loan_id)
    _login(client, "mgr" if as_manager else "borrower")
    confirm_all_lines(client, loan_id, mgr_id, line_ids)
    complete_workflow_step(client, loan_id)
    pack_lines(client, loan_id, line_ids)
    complete_workflow_step(client, loan_id)
    pickup_lines(client, loan_id, line_ids)
