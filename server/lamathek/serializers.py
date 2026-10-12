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
from lamathek.models.material import MaterialType, Piece, StockLot
from lamathek.services.variants import (
    piece_variant_to_json,
    stock_lot_variant_to_json,
    variants_to_json,
)
from lamathek.models.set import SET_ROLE_ASSIGNMENT, SET_ROLE_OPTIONAL, MaterialSet
from lamathek.models.settings import InstallationSettings
from lamathek.models.audit import AuditEvent
from lamathek.models.user import User
from lamathek.services.photos import photos_to_json


def user_to_json(user: User) -> dict:
    return {
        "id": user.id,
        "sub": user.oidc_sub,
        "name": user.name,
        "email": user.email,
        "isSuperuser": user.is_superuser,
    }


def audit_event_to_json(event: AuditEvent, session: Session) -> dict:
    actor = session.get(User, event.actor_user_id)
    target = (
        session.get(User, event.target_user_id) if event.target_user_id is not None else None
    )
    return {
        "id": event.id,
        "action": event.action,
        "reason": event.reason,
        "detail": event.detail,
        "createdAt": event.created_at.isoformat() if event.created_at else None,
        "actor": user_to_json(actor) if actor is not None else None,
        "targetUser": user_to_json(target) if target is not None else None,
    }


def inventory_to_json(
    inventory: Inventory,
    *,
    cover_photo_id: int | None = None,
    include_photos: bool = False,
) -> dict:
    data = {
        "id": inventory.id,
        "name": inventory.name,
        "address": inventory.address,
        "latitude": inventory.latitude,
        "longitude": inventory.longitude,
        "notes": inventory.notes,
        "coverPhotoId": cover_photo_id,
    }
    if include_photos:
        data["photos"] = photos_to_json(list(inventory.photos))
    return data


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
        "hostName": settings.host_name,
        "hostAddress": settings.host_address,
        "hostPrivacyUrl": settings.host_privacy_url,
        "authProviderName": settings.auth_provider_name,
        "authProviderSameHost": settings.auth_provider_same_host,
        "authorityName": settings.authority_name,
        "authorityUrl": settings.authority_url,
    }


def category_to_json(category: Category) -> dict:
    return {"id": category.id, "name": category.name}


def material_item_fields_to_json(item: Piece | StockLot) -> dict:
    return {
        "acquiredYear": item.acquired_year,
        "note": item.note,
        "source": item.source,
        "status": item.status,
        "serialNumber": item.serial_number,
        "newValueCents": item.new_value_cents,
    }


def material_type_to_json(
    material_type: MaterialType,
    *,
    cover_photo_id: int | None = None,
    include_photos: bool = False,
) -> dict:
    category = material_type.category
    data = {
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
        "manufacturer": material_type.manufacturer,
        "modelName": material_type.model_name,
        "variants": variants_to_json(material_type),
        "coverPhotoId": cover_photo_id,
    }
    if include_photos:
        data["photos"] = photos_to_json(list(material_type.photos))
    return data


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
        "photos": photos_to_json(list(damage.photos)),
    }


def piece_to_json(piece: Piece, *, cover_photo_id: int | None = None) -> dict:
    return {
        "id": piece.id,
        "materialTypeId": piece.material_type_id,
        "materialTypeName": piece.material_type.name,
        "name": piece.name,
        "variant": piece_variant_to_json(piece),
        "setId": piece.set_id,
        "setRole": piece.set_role,
        "setName": piece.material_set.name if piece.material_set else None,
        "coverPhotoId": cover_photo_id,
        **material_item_fields_to_json(piece),
    }


def piece_detail_to_json(piece: Piece, *, cover_photo_id: int | None = None) -> dict:
    return {
        **piece_to_json(piece, cover_photo_id=cover_photo_id),
        "inventoryId": piece.material_type.inventory_id,
        "photos": photos_to_json(list(piece.photos)),
        "damages": [damage_to_json(d) for d in piece.damages],
    }


def set_to_json(material_set: MaterialSet, *, cover_photo_id: int | None = None) -> dict:
    return {
        "id": material_set.id,
        "inventoryId": material_set.inventory_id,
        "name": material_set.name,
        "shortName": material_set.short_name,
        "coverPhotoId": cover_photo_id,
    }


def set_detail_to_json(material_set: MaterialSet, *, cover_photo_id: int | None = None) -> dict:
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
        **set_to_json(material_set, cover_photo_id=cover_photo_id),
        "photos": photos_to_json(list(material_set.photos)),
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


def loan_to_json(loan: Loan, *, cover_photo_id: int | None = None) -> dict:
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
        "coverPhotoId": cover_photo_id,
    }


def loan_detail_to_json(loan: Loan, *, cover_photo_id: int | None = None) -> dict:
    return {
        **loan_to_json(loan, cover_photo_id=cover_photo_id),
        "photos": photos_to_json(list(loan.photos)),
        "lines": [_loan_line_to_json(line) for line in loan.lines],
        "returns": [_loan_return_to_json(r) for r in loan.returns],
    }


def stock_to_json(
    material_type: MaterialType,
    *,
    cover_photo_id: int | None = None,
    lot_cover_photo_ids: dict[int, int | None] | None = None,
) -> dict:
    from lamathek.models.material import ITEM_STATUS_ACTIVE

    lots = list(material_type.stock_lots)
    lot_covers = lot_cover_photo_ids or {}
    return {
        "materialTypeId": material_type.id,
        "materialTypeName": material_type.name,
        "unit": material_type.unit,
        "variants": variants_to_json(material_type),
        "quantity": sum(
            lot.quantity for lot in lots if lot.status == ITEM_STATUS_ACTIVE
        ),
        "coverPhotoId": cover_photo_id,
        "lots": [
            {
                "id": lot.id,
                "label": lot.label,
                "variant": stock_lot_variant_to_json(lot),
                "quantity": lot.quantity,
                "coverPhotoId": lot_covers.get(lot.id),
                "photos": photos_to_json(list(lot.photos)),
                **material_item_fields_to_json(lot),
            }
            for lot in lots
        ],
    }
