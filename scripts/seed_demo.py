#!/usr/bin/env python3
"""Fill the dev database with demo data: two Inventare, a Jurte set, Verleihe in each phase.

    python scripts/seed_demo.py --reset    # delete DB + media, migrate, seed
    ./scripts/dev.sh --seed                # same, then start the dev stack

Master data goes through the services; Verleihe walk the real API with the
Flask test client, so the workflow rules apply exactly as in the app. Mails are
never sent. Dates are relative to today in the instance timezone.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))
os.environ.setdefault("LAMATHEK_ENV", "dev")
# Demo mails go to example addresses: never start the sender, drop them at the end.
os.environ["MAIL_OUTBOX_WORKER"] = "0"

DEMO_PHONE = "+49 6421 000000"


class Api:
    """Test client that signs in as a given user and fails loudly on errors."""

    def __init__(self, app):
        self.client = app.test_client()

    def as_user(self, user) -> "Api":
        with self.client.session_transaction() as sess:
            sess.pop("impersonation", None)
            sess["user"] = {"sub": user.oidc_sub, "name": user.name, "email": user.email}
        return self

    def _call(self, method: str, path: str, body: dict | None, expect: tuple[int, ...]):
        response = self.client.open(
            path,
            method=method,
            json=body,
            headers={"X-Requested-With": "lamathek"},
        )
        if response.status_code not in expect:
            raise RuntimeError(
                f"{method} {path} → {response.status_code}: {response.get_data(as_text=True)}"
            )
        return response.get_json()

    def post(self, path: str, body: dict | None = None):
        return self._call("POST", path, body or {}, (200, 201))

    def patch(self, path: str, body: dict):
        return self._call("PATCH", path, body, (200,))


def reset_database() -> None:
    from lamathek.config import Config, media_path

    url = Config.SQLALCHEMY_DATABASE_URI
    if not url.startswith("sqlite:///"):
        sys.exit(f"--reset only supports SQLite, got {url}")
    db_file = Path(url.removeprefix("sqlite:///"))
    for path in (db_file, Path(f"{db_file}-wal"), Path(f"{db_file}-shm")):
        path.unlink(missing_ok=True)
    shutil.rmtree(media_path(), ignore_errors=True)
    print(f"Reset {db_file}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reset", action="store_true", help="delete the database first")
    args = parser.parse_args()

    from lamathek.cli import upgrade_database

    if args.reset:
        reset_database()
    upgrade_database()

    from lamathek.app import create_app
    from lamathek.db import get_session
    from lamathek.models.inventory import Inventory

    app = create_app()
    with app.app_context():
        session = get_session()
        if session.query(Inventory).count():
            sys.exit("Database already has Inventare. Use --reset to start over.")
        seed(app, session)


def seed(app, session) -> None:
    from lamathek.config import Config
    from lamathek.models.inventory import (
        INVENTORY_VISIBILITY_ACTIVE,
        INVENTORY_VISIBILITY_INTERNAL,
    )
    from lamathek.models.set import SET_ROLE_ASSIGNMENT
    from lamathek.services.inventories import create_inventory, replace_permissions
    from lamathek.services.loan_notifications import set_mail_sender_for_tests
    from lamathek.services.material import (
        create_material_type,
        create_piece,
        create_stock_lot,
    )
    from lamathek.services.sets import create_set, set_piece_membership, upsert_stock_line
    from lamathek.services.users import create_local_user, upsert_user_from_oidc
    from lamathek.timezone import instance_today

    def no_mail(*_args, **_kwargs):
        return None

    set_mail_sender_for_tests(no_mail)

    # --- Users ----------------------------------------------------------------
    dev = upsert_user_from_oidc(
        session,
        sub=Config.AUTH_DEV_SUB or "dev:local",
        name=Config.AUTH_DEV_NAME or "Dev User",
        email=Config.AUTH_DEV_EMAIL or "dev@local",
        force_superuser=True,
    )
    mara = upsert_user_from_oidc(
        session, sub="seed:mara", name="Mara Matwart", email="mara@example.org",
        force_superuser=False,
    )
    lea = upsert_user_from_oidc(
        session, sub="seed:lea", name="Lea Leiterin", email="lea@example.org",
        force_superuser=False,
    )
    lea.phone = "+49 151 00000001"
    mara.phone = "+49 151 00000002"
    session.commit()
    create_local_user(
        session, name="Paul Platzwart", phone="+49 151 00000003", email="paul@example.org"
    )

    # --- Inventare --------------------------------------------------------------
    donnerskopf = create_inventory(
        session,
        "Landesmaterial Donnerskopf",
        address="Donnerskopf, 61239 Ober-Mörlen",
        latitude=50.3606,
        longitude=8.6347,
        notes="Schlüssel bei Mara. Material im Keller, Zelte im Schuppen.",
        visibility=INVENTORY_VISIBILITY_ACTIVE,
    )
    buero = create_inventory(
        session,
        "Landesbüro",
        address="Marburg",
        visibility=INVENTORY_VISIBILITY_INTERNAL,
    )
    replace_permissions(session, donnerskopf, [mara.id])
    replace_permissions(session, buero, [mara.id], reader_user_ids=[lea.id])

    # --- Material Donnerskopf ---------------------------------------------------
    def piece_type(name: str, short: str | None = None, **kw):
        return create_material_type(
            session, donnerskopf, name, "piece", None, short_name=short,
            category_name="Zelt", **kw,
        )

    def stock_type(name: str, quantity: int, *, category: str, unit: str = "Stück"):
        mt = create_material_type(
            session, donnerskopf, name, "stock", None, unit=unit, category_name=category
        )
        create_stock_lot(
            session, donnerskopf, mt.id, label=None, variant=None, quantity=quantity
        )
        return mt

    halbdach = piece_type("Halbdach", "HD", manufacturer="Tortuga")
    dv = piece_type("Doppelviereckplane", "DV", manufacturer="Tortuga")
    abdeck = piece_type("Jurten-Abdeckplane", "AP")
    zarge = create_material_type(
        session, donnerskopf, "Zargeskiste", "piece", None, category_name="Kiste"
    )

    halbdaecher = [create_piece(session, donnerskopf, halbdach.id, f"HD {i}", None) for i in (1, 2, 3)]
    dvs = [create_piece(session, donnerskopf, dv.id, f"DV {i}", None) for i in range(1, 9)]
    abdecks = [create_piece(session, donnerskopf, abdeck.id, f"AP {i}", None) for i in (1, 2)]
    zursula = create_piece(session, donnerskopf, zarge.id, "Zursula", None)
    zarge_2 = create_piece(session, donnerskopf, zarge.id, "Zarge 2", None)

    # Stock lines on a Set or Verleih carry no variant, so lengths are own Materialarten.
    seil_3 = stock_type("Seil 3 m", 20, category="Zelt")
    seil_4 = stock_type("Seil 4 m", 6, category="Zelt")
    teleskop = stock_type("Teleskopstange 2 m", 20, category="Zelt")
    steckstange = stock_type("Steckstange 4,5 m", 2, category="Zelt")
    hering = stock_type("Hering", 40, category="Zelt")

    # --- Set Jurte 1 -------------------------------------------------------------
    jurte = create_set(session, donnerskopf, "Jurte 1", short_name="J1")
    for piece in [*halbdaecher[:2], *dvs[:6], abdecks[0], zursula]:
        set_piece_membership(session, jurte, piece.id, SET_ROLE_ASSIGNMENT)
    for mt, qty in ((seil_3, 12), (seil_4, 3), (teleskop, 12), (steckstange, 1), (hering, 12)):
        upsert_stock_line(session, jurte, mt.id, SET_ROLE_ASSIGNMENT, qty)

    # --- Material Landesbüro -----------------------------------------------------
    beamer = create_material_type(session, buero, "Beamer", "piece", None, category_name="Technik")
    create_piece(session, buero, beamer.id, "Beamer 1", None)
    flyer = create_material_type(
        session, buero, "Flyer Landeslager", "stock", None, unit="Stück", consumable=True
    )
    create_stock_lot(session, buero, flyer.id, label="Karton 1", variant=None, quantity=500)

    # --- Verleihe ---------------------------------------------------------------
    api = Api(app)
    today = instance_today()

    def day(offset: int) -> str:
        return (today + timedelta(days=offset)).isoformat()

    def new_loan(group: str, event: str | None, *, lines: list[dict], **extra) -> dict:
        api.as_user(lea)
        loan = api.post(
            f"/api/inventories/{donnerskopf.id}/loans",
            {"groupName": group, "eventName": event, "borrowerUserId": lea.id, **extra},
        )
        for line in lines:
            loan = api.post(f"/api/loans/{loan['id']}/lines", line)
        return loan

    def request(loan: dict, pickup: int, ret: int | None) -> dict:
        api.as_user(lea)
        body = {"pickupOn": day(pickup)}
        if ret is not None:
            body["returnOn"] = day(ret)
        return api.post(f"/api/loans/{loan['id']}/actions/request", body)

    def line_ids(loan: dict, status: str) -> list[int]:
        return [ln["id"] for ln in loan["lines"] if ln["status"] == status]

    def step(loan: dict, action: str, status: str, *, user=None) -> dict:
        api.as_user(user or mara)
        lid = line_ids(loan, status)
        loan = api.post(f"/api/loans/{loan['id']}/actions/{action}", {"lineIds": lid})
        return api.post(f"/api/loans/{loan['id']}/actions/complete-step")

    def confirm(loan: dict) -> dict:
        api.as_user(mara)
        api.patch(f"/api/loans/{loan['id']}", {"contactUserId": mara.id})
        return step(loan, "confirm", "requested")

    jurte_line = [{"setId": jurte.id}]

    # Abgeschlossen: Jurte war vor einem Monat draußen, bis auf zwei Heringe zurück.
    closed = new_loan("Stamm Habicht", "Pfingstlager", lines=jurte_line)
    closed = request(closed, -40, -33)
    closed = confirm(closed)
    closed = step(closed, "pack", "confirmed")
    closed = step(closed, "pickup", "packed", user=lea)
    closed = step(closed, "report-return", "picked_up", user=lea)
    api.as_user(mara)
    # Two Heringe did not come back: an open Verlust on the Mengenposten.
    entries = [
        {"lineId": ln["id"], "returnedQuantity": 10, "reason": "Im Wald geblieben"}
        if ln.get("materialTypeId") == hering.id
        else {"lineId": ln["id"]}
        for ln in closed["lines"]
        if ln["status"] == "return_reported"
    ]
    closed = api.post(f"/api/loans/{closed['id']}/actions/restock", {"entries": entries})
    api.post(f"/api/loans/{closed['id']}/actions/complete-step")

    # Packen nächste Woche: Jurte bestätigt.
    packing = new_loan("Stamm Habicht", "Herbstfahrt", lines=jurte_line)
    packing = request(packing, 7, 10)
    confirm(packing)

    # Anfrage, die sich mit „Packen nächste Woche“ überschneidet (Konfliktwarnung).
    overlap = new_loan("Stamm Falke", "Hajk", lines=jurte_line)
    request(overlap, 9, 12)

    # Abgeholt und überfällig: drittes Halbdach, zweite Zarge, Heringe.
    overdue = new_loan(
        "Stamm Falke",
        "Wochenendfahrt",
        lines=[
            {"pieceId": halbdaecher[2].id},
            {"pieceId": zarge_2.id},
            {"materialTypeId": hering.id, "quantity": 10},
        ],
    )
    overdue = request(overdue, -10, -3)
    overdue = confirm(overdue)
    overdue = step(overdue, "pack", "confirmed")
    step(overdue, "pickup", "packed", user=lea)

    # Dauerleihgabe: Teleskopstangen für den Stammesgrund.
    permanent = new_loan(
        "Stamm Habicht",
        None,
        kind="permanent",
        lines=[{"materialTypeId": teleskop.id, "quantity": 4}],
    )
    permanent = request(permanent, -60, None)
    permanent = confirm(permanent)
    permanent = step(permanent, "pack", "confirmed")
    step(permanent, "pickup", "packed", user=lea)

    # Entwurf: Lea plant das Sommerlager.
    new_loan("Stamm Habicht", "Sommerlager", lines=[{"pieceId": dvs[6].id}, {"pieceId": dvs[7].id}])

    from lamathek.models.mail import MailOutbox

    session.query(MailOutbox).delete()
    session.commit()
    set_mail_sender_for_tests(None)
    print(
        "Demo data ready: 2 Inventare, Set „Jurte 1“, 6 Verleihe.\n"
        f"Sign in with the dev bypass as {dev.name} (Superuser)."
    )


if __name__ == "__main__":
    main()
