from sqlalchemy.orm import Session

from lamathek.models.inventory import Inventory
from lamathek.services.inventories import (
    format_content_responsible_users,
    users_with_inventory_permission,
)
from lamathek.models.journal import LoanJournalEntry
from lamathek.models.loan import Loan, LoanLine
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
def user_ref_json(user: User) -> dict:
    """Name only, for actors in journals: no contact data (D0005)."""
    return {"id": user.id, "name": user.name}


def user_to_json(user: User, *, include_phone: bool = True, include_sub: bool = False) -> dict:
    """Contact view of a user. The OIDC subject is only for the user themself and superusers."""
    body = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "isSuperuser": user.is_superuser,
        "hasLogin": not (user.oidc_sub or "").startswith("local:"),
    }
    if include_phone:
        body["phone"] = user.phone or ""
    if include_sub:
        body["sub"] = user.oidc_sub
    return body


def audit_event_to_json(event: AuditEvent, session: Session) -> dict:
    actor = (
        session.get(User, event.actor_user_id) if event.actor_user_id is not None else None
    )
    target = (
        session.get(User, event.target_user_id) if event.target_user_id is not None else None
    )
    return {
        "id": event.id,
        "action": event.action,
        "reason": event.reason,
        "detail": event.detail,
        "createdAt": event.created_at.isoformat() if event.created_at else None,
        "actor": user_to_json(actor, include_sub=True) if actor is not None else None,
        "targetUser": user_to_json(target, include_sub=True) if target is not None else None,
    }


def inventory_to_json(
    inventory: Inventory,
    *,
    cover_photo_id: int | None = None,
    include_photos: bool = False,
    can_manage: bool | None = None,
) -> dict:
    data = {
        "id": inventory.id,
        "name": inventory.name,
        "visibility": inventory.visibility,
        "address": inventory.address,
        "latitude": inventory.latitude,
        "longitude": inventory.longitude,
        "notes": inventory.notes,
        "coverPhotoId": cover_photo_id,
    }
    if can_manage is not None:
        data["canManage"] = can_manage
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
        "calendarBundesland": settings.calendar_bundesland,
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
    usage_count: int | None = None,
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
    if usage_count is not None:
        data["usageCount"] = usage_count
    if include_photos:
        data["photos"] = photos_to_json(list(material_type.photos))
    return data


def repair_to_json(repair: Repair) -> dict:
    return {
        "id": repair.id,
        "recordedOn": repair.recorded_on.isoformat(),
        "note": repair.note,
        "resolutionKind": repair.resolution_kind,
    }


def damage_to_json(damage: Damage) -> dict:
    return {
        "id": damage.id,
        "recordedOn": damage.recorded_on.isoformat(),
        "note": damage.note,
        "severe": damage.severe,
        "kind": damage.kind,
        "open": damage.repair is None,
        "repair": repair_to_json(damage.repair) if damage.repair else None,
        "photos": photos_to_json(list(damage.photos)),
    }


def piece_to_json(
    piece: Piece, *, cover_photo_id: int | None = None, lost: bool = False
) -> dict:
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
        "lost": lost,
        **material_item_fields_to_json(piece),
    }


def piece_detail_to_json(
    piece: Piece,
    *,
    cover_photo_id: int | None = None,
    lost: bool = False,
    found_again_eligible: bool = False,
    warnings: list[dict] | None = None,
) -> dict:
    return {
        **piece_to_json(piece, cover_photo_id=cover_photo_id, lost=lost),
        "inventoryId": piece.material_type.inventory_id,
        "photos": photos_to_json(list(piece.photos)),
        "damages": [damage_to_json(d) for d in piece.damages],
        "foundAgainEligible": found_again_eligible,
        "warnings": warnings or [],
    }


def set_to_json(material_set: MaterialSet, *, cover_photo_id: int | None = None) -> dict:
    return {
        "id": material_set.id,
        "inventoryId": material_set.inventory_id,
        "name": material_set.name,
        "shortName": material_set.short_name,
        "coverPhotoId": cover_photo_id,
        "assignmentPieceIds": [
            piece.id
            for piece in material_set.pieces
            if piece.set_role == SET_ROLE_ASSIGNMENT
        ],
        "optionalPieceIds": [
            piece.id
            for piece in material_set.pieces
            if piece.set_role == SET_ROLE_OPTIONAL
        ],
        "assignmentStockTypeIds": [
            line.material_type_id
            for line in material_set.stock_lines
            if line.role == SET_ROLE_ASSIGNMENT
        ],
        "optionalStockTypeIds": [
            line.material_type_id
            for line in material_set.stock_lines
            if line.role == SET_ROLE_OPTIONAL
        ],
    }


def set_detail_to_json(material_set: MaterialSet, *, cover_photo_id: int | None = None) -> dict:
    assignment_pieces = []
    optional_pieces = []
    for piece in material_set.pieces:
        if piece.material_type is None:
            continue
        data = piece_to_json(piece)
        if piece.set_role == SET_ROLE_ASSIGNMENT:
            assignment_pieces.append(data)
        elif piece.set_role == SET_ROLE_OPTIONAL:
            optional_pieces.append(data)

    assignment_stock = []
    optional_stock = []
    for line in material_set.stock_lines:
        material_type = line.material_type
        if material_type is None:
            continue
        row = {
            "id": line.id,
            "materialTypeId": line.material_type_id,
            "materialTypeName": material_type.name,
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


def _origin_json(line: LoanLine) -> dict:
    return {
        "originSetId": line.origin_set_id,
        "originSetName": line.origin_set_name,
        "originSetRole": line.origin_set_role,
    }


def _loan_line_to_json(line: LoanLine, *, warnings: list[dict] | None = None) -> dict:
    origin = _origin_json(line)
    base = {
        "id": line.id,
        "status": line.status,
        "note": line.note or "",
        "reason": line.reason or "",
        "replacesLineId": line.replaces_line_id,
        "splitFromLineId": line.split_from_line_id,
        "requestNotified": bool(line.request_notified),
        "returnedQuantity": line.returned_quantity,
        "statusBeforeEnd": line.status_before_end,
        "warnings": warnings or [],
        **origin,
    }
    if line.piece_id is not None and line.piece is not None:
        return {
            **base,
            "kind": "piece",
            "pieceId": line.piece_id,
            "pieceName": line.piece.name,
            "materialTypeName": line.piece.material_type.name,
        }
    if line.material_type_id is not None and line.material_type is not None:
        return {
            **base,
            "kind": "stock",
            "materialTypeId": line.material_type_id,
            "materialTypeName": line.material_type.name,
            "quantity": line.quantity,
            "consumable": line.material_type.consumable,
        }
    return {**base, "kind": "unknown"}


def loan_to_json(
    loan: Loan,
    *,
    cover_photo_id: int | None = None,
    viewer: User | None = None,
    session: Session | None = None,
) -> dict:
    borrower_phone = ""
    contact_phone = ""
    if viewer is not None and session is not None:
        from lamathek.services.inventories import user_can_manage_inventory
        from lamathek.services.loan_access import user_is_borrower

        if user_can_manage_inventory(session, viewer, loan.inventory):
            borrower_phone = loan.borrower_user.phone or ""
        if user_is_borrower(viewer, loan) and loan.contact_user is not None:
            contact_phone = loan.contact_user.phone or ""
    inventory_name = loan.inventory.name if loan.inventory is not None else ""
    return {
        "id": loan.id,
        "inventoryId": loan.inventory_id,
        "inventoryName": inventory_name,
        "kind": loan.kind,
        "phase": loan.phase,
        "groupId": loan.group_id,
        "groupName": loan.group.name if loan.group else "",
        "borrowerUserId": loan.borrower_user_id,
        "borrowerUserName": loan.borrower_user.name or loan.borrower_user.email or "",
        "borrowerPhone": borrower_phone,
        "contactUserId": loan.contact_user_id,
        "contactUserName": (
            loan.contact_user.name or loan.contact_user.email or ""
            if loan.contact_user
            else None
        ),
        "contactPhone": contact_phone or None,
        "eventId": loan.event_id,
        "eventName": loan.event.name if loan.event else None,
        "wishPickupOn": loan.wish_pickup_on.isoformat() if loan.wish_pickup_on else None,
        "wishReturnOn": loan.wish_return_on.isoformat() if loan.wish_return_on else None,
        "pickupOn": loan.pickup_on.isoformat() if loan.pickup_on else None,
        "returnOn": loan.return_on.isoformat() if loan.return_on else None,
        "pickupNote": loan.pickup_note or "",
        "returnNote": loan.return_note or "",
        "coverPhotoId": cover_photo_id,
    }


def loan_detail_to_json(
    loan: Loan,
    *,
    cover_photo_id: int | None = None,
    viewer: User | None = None,
    session: Session | None = None,
) -> dict:
    from lamathek.models.loan import PHOTO_ROLE_PICKUP, PHOTO_ROLE_RETURN
    from lamathek.services.loan_conflicts import enrich_loan_detail_warnings

    pickup_photos = [p for p in loan.photos if p.loan_photo_role == PHOTO_ROLE_PICKUP]
    return_photos = [p for p in loan.photos if p.loan_photo_role == PHOTO_ROLE_RETURN]
    loan_warnings: list[dict] = []
    line_warning_map: dict[int, list[dict]] = {}
    if session is not None:
        loan_warnings, line_warning_map = enrich_loan_detail_warnings(session, loan)
    return {
        **loan_to_json(
            loan, cover_photo_id=cover_photo_id, viewer=viewer, session=session
        ),
        "warnings": loan_warnings,
        "pickupPhotos": photos_to_json(pickup_photos),
        "returnPhotos": photos_to_json(return_photos),
        "lines": [
            _loan_line_to_json(line, warnings=line_warning_map.get(line.id))
            for line in loan.lines
        ],
        "hasPendingMailChanges": any(line.mail_pending for line in loan.lines),
        "hasUnnotifiedRequestedLines": any(
            line.status == "requested" and not line.request_notified for line in loan.lines
        ),
    }


def journal_entry_to_json(entry: LoanJournalEntry) -> dict:
    import json

    payload: dict = {}
    try:
        parsed = json.loads(entry.payload or "{}")
        if isinstance(parsed, dict):
            payload = parsed
    except json.JSONDecodeError:
        payload = {"raw": entry.payload}
    actor = entry.actor_user
    real_actor = entry.real_actor_user
    return {
        "id": entry.id,
        "createdAt": entry.created_at.isoformat() if entry.created_at else None,
        "kind": entry.kind,
        "payload": payload,
        "loanId": entry.loan_id,
        "pieceId": entry.piece_id,
        "loanLineId": entry.loan_line_id,
        "actor": user_ref_json(actor) if actor is not None else None,
        "realActor": user_ref_json(real_actor) if real_actor is not None else None,
    }


def stock_to_json(
    material_type: MaterialType,
    *,
    cover_photo_id: int | None = None,
    lot_cover_photo_ids: dict[int, int | None] | None = None,
) -> dict:
    from sqlalchemy.orm import object_session

    from lamathek.models.material import ITEM_STATUS_ACTIVE
    from lamathek.services.stock_losses import lot_available_quantity, open_lost_by_lot

    lots = list(material_type.stock_lots)
    lot_covers = lot_cover_photo_ids or {}
    session = object_session(material_type)
    lost = open_lost_by_lot(session, [lot.id for lot in lots]) if session else {}
    return {
        "materialTypeId": material_type.id,
        "materialTypeName": material_type.name,
        "unit": material_type.unit,
        "variants": variants_to_json(material_type),
        # What can be lent: Soll-Anzahl of active lots minus open losses.
        "quantity": sum(
            lot_available_quantity(lot, lost.get(lot.id, 0))
            for lot in lots
            if lot.status == ITEM_STATUS_ACTIVE
        ),
        "lostQuantity": sum(lost.values()),
        "coverPhotoId": cover_photo_id,
        "lots": [
            {
                "id": lot.id,
                "label": lot.label,
                "variant": stock_lot_variant_to_json(lot),
                "quantity": lot.quantity,
                "lostQuantity": lost.get(lot.id, 0),
                "coverPhotoId": lot_covers.get(lot.id),
                "photos": photos_to_json(list(lot.photos)),
                **material_item_fields_to_json(lot),
            }
            for lot in lots
        ],
    }
