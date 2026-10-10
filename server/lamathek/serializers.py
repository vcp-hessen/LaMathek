from sqlalchemy.orm import Session

from lamathek.models.inventory import Inventory
from lamathek.services.inventories import (
    format_content_responsible_users,
    users_with_inventory_permission,
)
from lamathek.models.loan import (
    RETURN_OUTCOME_LOSS,
    RETURN_OUTCOME_RETURNED,
    Loan,
    LoanLine,
    LoanReturn,
)
from lamathek.models.damage import Damage, Repair
from lamathek.models.category import Category
from lamathek.models.material import MaterialType, Piece
from lamathek.services.variants import (
    piece_variant_to_json,
    stock_lot_variant_to_json,
    variants_to_json,
)
from lamathek.models.set import SET_ROLE_ASSIGNMENT, SET_ROLE_OPTIONAL, MaterialSet
from lamathek.models.settings import InstallationSettings
from lamathek.models.user import User


def user_to_json(user: User) -> dict:
    return {
        "id": user.id,
        "sub": user.oidc_sub,
        "name": user.name,
        "email": user.email,
        "isSuperuser": user.is_superuser,
        "role": user.role,
    }


def inventory_to_json(inventory: Inventory) -> dict:
    return {
        "id": inventory.id,
        "name": inventory.name,
        "address": inventory.address,
        "latitude": inventory.latitude,
        "longitude": inventory.longitude,
        "notes": inventory.notes,
    }


def settings_to_json(settings: InstallationSettings, session: Session) -> dict:
    managers = users_with_inventory_permission(session)
    return {
        "title": settings.title,
        "subtitle": settings.subtitle,
        "legalName": settings.legal_name,
        "legalAddress": settings.legal_address,
        "email": settings.email,
        "website": settings.website,
        "phone": settings.phone,
        "representedBy": settings.represented_by,
        "register": settings.register,
        "contentResponsible": format_content_responsible_users(managers),
        "mapLatitude": settings.map_latitude,
        "mapLongitude": settings.map_longitude,
    }


def category_to_json(category: Category) -> dict:
    return {"id": category.id, "name": category.name}


def material_type_to_json(material_type: MaterialType) -> dict:
    category = material_type.category
    return {
        "id": material_type.id,
        "inventoryId": material_type.inventory_id,
        "name": material_type.name,
        "shortName": material_type.short_name,
        "description": material_type.description,
        "tracking": material_type.tracking,
        "unit": material_type.unit,
        "consumable": material_type.consumable,
        "categoryId": material_type.category_id,
        "categoryName": category.name if category is not None else None,
        "variants": variants_to_json(material_type),
    }


def repair_to_json(repair: Repair) -> dict:
    return {
        "id": repair.id,
        "recordedOn": repair.recorded_on.isoformat(),
        "note": repair.note,
    }


def damage_to_json(damage: Damage) -> dict:
    return {
        "id": damage.id,
        "recordedOn": damage.recorded_on.isoformat(),
        "note": damage.note,
        "severe": damage.severe,
        "open": damage.repair is None,
        "repair": repair_to_json(damage.repair) if damage.repair else None,
    }


def piece_to_json(piece: Piece) -> dict:
    return {
        "id": piece.id,
        "materialTypeId": piece.material_type_id,
        "materialTypeName": piece.material_type.name,
        "name": piece.name,
        "variant": piece_variant_to_json(piece),
        "setId": piece.set_id,
        "setRole": piece.set_role,
        "setName": piece.material_set.name if piece.material_set else None,
    }


def piece_detail_to_json(piece: Piece) -> dict:
    return {
        **piece_to_json(piece),
        "inventoryId": piece.material_type.inventory_id,
        "damages": [damage_to_json(d) for d in piece.damages],
    }


def set_to_json(material_set: MaterialSet) -> dict:
    return {
        "id": material_set.id,
        "inventoryId": material_set.inventory_id,
        "name": material_set.name,
        "shortName": material_set.short_name,
    }


def set_detail_to_json(material_set: MaterialSet) -> dict:
    assignment_pieces = []
    optional_pieces = []
    for piece in material_set.pieces:
        data = piece_to_json(piece)
        if piece.set_role == SET_ROLE_ASSIGNMENT:
            assignment_pieces.append(data)
        elif piece.set_role == SET_ROLE_OPTIONAL:
            optional_pieces.append(data)

    assignment_stock = []
    optional_stock = []
    for line in material_set.stock_lines:
        row = {
            "id": line.id,
            "materialTypeId": line.material_type_id,
            "materialTypeName": line.material_type.name,
            "role": line.role,
            "quantity": line.quantity,
        }
        if line.role == SET_ROLE_ASSIGNMENT:
            assignment_stock.append(row)
        else:
            optional_stock.append(row)

    return {
        **set_to_json(material_set),
        "assignmentPieces": sorted(assignment_pieces, key=lambda p: p["name"]),
        "optionalPieces": sorted(optional_pieces, key=lambda p: p["name"]),
        "assignmentStock": sorted(assignment_stock, key=lambda r: r["materialTypeName"]),
        "optionalStock": sorted(optional_stock, key=lambda r: r["materialTypeName"]),
    }


def group_to_json(group) -> dict:
    return {"id": group.id, "name": group.name}


def event_to_json(event) -> dict:
    return {"id": event.id, "name": event.name}


def _line_return_totals(line: LoanLine) -> tuple[int, int]:
    returned = 0
    lost = 0
    for row in line.return_lines:
        qty = row.quantity if row.quantity is not None else 1
        if row.outcome == RETURN_OUTCOME_RETURNED:
            returned += qty
        elif row.outcome == RETURN_OUTCOME_LOSS:
            lost += qty
    return returned, lost


def _line_return_fields(line: LoanLine) -> dict:
    returned, lost = _line_return_totals(line)
    if line.material_type_id is not None and line.quantity is not None:
        outstanding = max(0, line.quantity - returned - lost)
        return {
            "returnedQuantity": returned,
            "lostQuantity": lost,
            "outstandingQuantity": outstanding,
            "settled": outstanding == 0,
        }
    settled = returned + lost >= 1
    return {
        "returnedQuantity": returned,
        "lostQuantity": lost,
        "outstandingQuantity": 0 if settled else 1,
        "settled": settled,
    }


def _origin_json(line: LoanLine) -> dict:
    return {
        "originSetId": line.origin_set_id,
        "originSetName": line.origin_set_name,
        "originSetRole": line.origin_set_role,
    }


def _loan_line_to_json(line: LoanLine) -> dict:
    return_fields = _line_return_fields(line)
    origin = _origin_json(line)
    if line.piece_id is not None and line.piece is not None:
        return {
            "id": line.id,
            "kind": "piece",
            "pieceId": line.piece_id,
            "pieceName": line.piece.name,
            "materialTypeName": line.piece.material_type.name,
            **origin,
            **return_fields,
        }
    if line.material_type_id is not None and line.material_type is not None:
        return {
            "id": line.id,
            "kind": "stock",
            "materialTypeId": line.material_type_id,
            "materialTypeName": line.material_type.name,
            "quantity": line.quantity,
            **origin,
            **return_fields,
        }
    return {"id": line.id, "kind": "unknown", **origin, **return_fields}


def _loan_return_to_json(loan_return: LoanReturn) -> dict:
    return {
        "id": loan_return.id,
        "recordedOn": loan_return.recorded_on.isoformat(),
        "lines": [
            {
                "loanLineId": line.loan_line_id,
                "outcome": line.outcome,
                "quantity": line.quantity,
            }
            for line in loan_return.lines
        ],
    }


def loan_to_json(loan: Loan) -> dict:
    return {
        "id": loan.id,
        "inventoryId": loan.inventory_id,
        "kind": loan.kind,
        "status": loan.status,
        "groupId": loan.group_id,
        "groupName": loan.group.name if loan.group else "",
        "responsibleUserId": loan.responsible_user_id,
        "responsibleUserName": loan.responsible_user.name or loan.responsible_user.email or "",
        "eventId": loan.event_id,
        "eventName": loan.event.name if loan.event else None,
        "startsOn": loan.starts_on.isoformat() if loan.starts_on else None,
        "endsOn": loan.ends_on.isoformat() if loan.ends_on else None,
    }


def loan_detail_to_json(loan: Loan) -> dict:
    return {
        **loan_to_json(loan),
        "lines": [_loan_line_to_json(line) for line in loan.lines],
        "returns": [_loan_return_to_json(r) for r in loan.returns],
    }


def stock_to_json(material_type: MaterialType) -> dict:
    lots = list(material_type.stock_lots)
    return {
        "materialTypeId": material_type.id,
        "materialTypeName": material_type.name,
        "unit": material_type.unit,
        "variants": variants_to_json(material_type),
        "quantity": sum(lot.quantity for lot in lots),
        "lots": [
            {
                "id": lot.id,
                "label": lot.label,
                "variant": stock_lot_variant_to_json(lot),
                "quantity": lot.quantity,
            }
            for lot in lots
        ],
    }
