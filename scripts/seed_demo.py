#!/usr/bin/env python3
"""Load example Inventar data into the local dev database (see .env.dev)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "server"
sys.path.insert(0, str(SERVER))

ENV_FILE = ROOT / ".env.dev"
DEMO_INVENTORY_NAME = "Landesbüro (Beispiel)"


def _load_env() -> None:
    if not ENV_FILE.is_file():
        print(f"Missing {ENV_FILE}", file=sys.stderr)
        sys.exit(1)
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key.strip(), value)


def main() -> None:
    _load_env()
    os.environ.setdefault("LAMATHEK_ENV", "dev")

    from sqlalchemy import select

    from lamathek.app import create_app
    from lamathek.db import get_session
    from lamathek.models.inventory import Inventory
    from lamathek.models.set import SET_ROLE_ASSIGNMENT, SET_ROLE_OPTIONAL
    from lamathek.services.inventories import create_inventory
    from lamathek.services.loans import add_piece_line, add_set_assignment_lines, create_loan
    from lamathek.services.material import (
        create_material_type,
        create_piece,
        create_stock_lot,
    )
    from lamathek.services.sets import (
        create_set,
        set_piece_membership,
        upsert_stock_line,
    )
    from lamathek.services.users import upsert_user_from_oidc

    app = create_app()
    with app.app_context():
        session = get_session()

        existing = session.scalar(
            select(Inventory).where(Inventory.name == DEMO_INVENTORY_NAME)
        )
        if existing is not None:
            print(f"Demo inventar already exists: {DEMO_INVENTORY_NAME} (id={existing.id})")
            return

        ver = upsert_user_from_oidc(
            session,
            sub="dev:verantwortliche",
            name="Max Verantwortliche",
            email="ver@example.local",
            force_superuser=False,
        )
        inventory = create_inventory(session, DEMO_INVENTORY_NAME)

        kohte = create_material_type(
            session,
            inventory,
            name="Kohtenplane",
            tracking="piece",
            variants=[{"label": "Randstreifen", "values": ["0 cm", "10 cm", "35 cm"]}],
        )
        brett = create_material_type(
            session,
            inventory,
            name="Brettspiel",
            tracking="piece",
            variants=[],
        )
        heringe = create_material_type(
            session,
            inventory,
            name="Heringe",
            tracking="stock",
            variants=[],
        )
        seile = create_material_type(
            session,
            inventory,
            name="Seile",
            tracking="stock",
            variants=[],
        )

        plane_a = create_piece(
            session, inventory, kohte.id, "Plane A", {"Randstreifen": "10 cm"}
        )
        plane_b = create_piece(
            session, inventory, kohte.id, "Plane B", {"Randstreifen": "35 cm"}
        )
        catan = create_piece(session, inventory, brett.id, "Catan", None)
        beamer = create_piece(session, inventory, brett.id, "Beamer", None)

        create_stock_lot(
            session, inventory, heringe.id, label=None, variant=None, quantity=48
        )
        create_stock_lot(
            session, inventory, seile.id, label=None, variant=None, quantity=24
        )

        jurte = create_set(session, inventory, "Jurte (Beispiel)")
        set_piece_membership(session, jurte, plane_a.id, SET_ROLE_ASSIGNMENT)
        set_piece_membership(session, jurte, plane_b.id, SET_ROLE_ASSIGNMENT)
        set_piece_membership(session, jurte, catan.id, SET_ROLE_OPTIONAL)
        upsert_stock_line(session, jurte, heringe.id, SET_ROLE_ASSIGNMENT, 12)
        upsert_stock_line(session, jurte, seile.id, SET_ROLE_OPTIONAL, 6)

        loan = create_loan(
            session,
            inventory,
            group_name="Stamm Falken",
            borrower_user_id=ver.id,
            event_name="Pfingstlager 2026",
            pickup_on=None,
            return_on=None,
        )
        add_set_assignment_lines(session, loan, jurte.id)
        add_piece_line(session, loan, beamer.id)

        print(f"Created demo inventar «{DEMO_INVENTORY_NAME}» (id={inventory.id})")
        print(f"  Materialarten: Kohtenplane, Brettspiel, Heringe, Seile")
        print(f"  Set «Jurte (Beispiel)» with Zuordnung and Optionals")
        print(f"  Planned Verleih for Gruppe «Stamm Falken» (Verantwortliche*r: {ver.name})")


if __name__ == "__main__":
    main()
