"""Response models of the JSON API: what the web client receives (#16, ADR 0021).

Serializers keep building plain dicts; these models only describe them. Every
``/api`` route names its model with ``@responds``; tests and the dev server check
each answer against it, and ``lamathek openapi`` exports the OpenAPI document the
client's zod schemas are generated from.

Rule: every key is always present. "Not applicable" or "not visible to you" is
``null``, never a missing key. Field names are snake_case here and camelCase on
the wire.
"""

import datetime as dt
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from typing_extensions import TypeAliasType


class ApiModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        alias_generator=to_camel,
        use_attribute_docstrings=True,
    )


# --- Enumerations ------------------------------------------------------------------

LoanKind = TypeAliasType("LoanKind", Literal["short", "permanent"])
LoanPhase = TypeAliasType(
    "LoanPhase",
    Literal["draft", "review", "pack", "handover", "return", "restock", "closed"],
)
LoanLineStatus = TypeAliasType(
    "LoanLineStatus",
    Literal[
        "draft",
        "requested",
        "confirmed",
        "packed",
        "picked_up",
        "return_reported",
        "restocked",
        "unavailable",
        "not_packed",
        "not_picked_up",
        "not_returned",
        "withdrawn",
    ],
)
SetRole = TypeAliasType("SetRole", Literal["assignment", "optional"])
Tracking = TypeAliasType("Tracking", Literal["piece", "stock"])
MaterialItemStatus = TypeAliasType("MaterialItemStatus", Literal["active", "retired"])
InventoryVisibility = TypeAliasType(
    "InventoryVisibility", Literal["internal", "active", "archived"]
)
OutboxStatus = TypeAliasType("OutboxStatus", Literal["pending", "sending", "sent", "failed"])
StockLossKind = TypeAliasType("StockLossKind", Literal["lost", "consumed"])
CalendarFeedScope = TypeAliasType(
    "CalendarFeedScope", Literal["borrower", "contact", "inventory"]
)
CalendarBundesland = TypeAliasType(
    "CalendarBundesland",
    Literal[
        "BW", "BY", "BE", "BB", "HB", "HH", "HE", "MV",
        "NI", "NW", "RP", "SL", "SN", "ST", "SH", "TH",
    ],
)
MailTestStatus = TypeAliasType("MailTestStatus", Literal["pending", "sent", "failed"])

VariantMap = dict[str, str]
"""Variant label → value, e.g. ``{"Länge": "3 m"}``; empty without variants."""


# --- Users -------------------------------------------------------------------------


class PhotoMeta(ApiModel):
    id: int
    sort_order: int


class User(ApiModel):
    """Contact view of a person."""

    id: int
    name: str | None
    email: str | None
    is_superuser: bool
    has_login: bool
    """False for people without a login (created by Materialwart*innen)."""
    phone: str | None
    """Null where the viewer may not see it (D0005)."""


class UserWithSub(User):
    """A person including the login subject (themself and superusers only)."""

    sub: str


class ManagedUser(User):
    inventory_ids: list[int]
    can_edit_contact: bool
    """Phone and email are only sent and editable where the viewer may change them."""


class UserRef(ApiModel):
    """Actor in journals: name only, no contact data (D0005)."""

    id: int
    name: str | None


class ImpersonationState(ApiModel):
    actor: UserWithSub | None
    reason: str
    started_at: dt.datetime


class Me(UserWithSub):
    impersonation: ImpersonationState | None


class AuditEvent(ApiModel):
    id: int
    action: str
    reason: str | None
    detail: dict[str, Any] | None
    created_at: dt.datetime
    actor: UserWithSub | None
    target_user: UserWithSub | None


# --- Installation ------------------------------------------------------------------


class InstallationSettings(ApiModel):
    title: str
    subtitle: str
    legal_name: str
    legal_address: str
    email: str
    website: str
    phone: str
    represented_by: str
    register_entry: str = Field(alias="register")
    """Registereintrag (Vereinsregister) for the Impressum."""
    content_responsible: str
    map_latitude: float
    map_longitude: float
    host_name: str
    host_address: str
    host_privacy_url: str
    auth_provider_name: str
    auth_provider_same_host: bool
    authority_name: str
    authority_url: str
    calendar_bundesland: CalendarBundesland


class Health(ApiModel):
    status: Literal["ok"]


class AuthMode(ApiModel):
    dev_bypass: bool


class GeocodeResult(ApiModel):
    latitude: float
    longitude: float


# --- Inventories -------------------------------------------------------------------


class Inventory(ApiModel):
    id: int
    name: str
    visibility: InventoryVisibility
    address: str | None
    latitude: float | None
    longitude: float | None
    notes: str | None
    cover_photo_id: int | None
    can_manage: bool
    """Whether the viewer is Materialwart*in here (else: Leserecht)."""


class InventoryDetail(Inventory):
    photos: list[PhotoMeta]


class InventoryPermissions(ApiModel):
    user_ids: list[int]
    """Materialwart*innen."""
    reader_user_ids: list[int]
    """People with Leserecht (see and request)."""
    users: list[User]
    readers: list[User]


# --- Material ----------------------------------------------------------------------


class Category(ApiModel):
    id: int
    name: str


class VariantAxis(ApiModel):
    label: str
    values: list[str]


class MaterialItemFields(ApiModel):
    acquired_year: int | None
    note: str | None
    source: str | None
    status: MaterialItemStatus
    serial_number: str | None
    new_value_cents: int | None


class MaterialType(ApiModel):
    id: int
    inventory_id: int
    name: str
    short_name: str | None
    description: str | None
    tracking: Tracking
    unit: str | None
    consumable: bool
    category_id: int | None
    category_name: str | None
    manufacturer: str | None
    model_name: str | None
    variants: list[VariantAxis]
    cover_photo_id: int | None
    usage_count: int
    """Einzelteile or Mengenposten of this type; only an unused type can be deleted."""
    photos: list[PhotoMeta]


class Piece(MaterialItemFields):
    id: int
    material_type_id: int
    material_type_name: str
    name: str
    variant: VariantMap
    set_id: int | None
    set_role: SetRole | None
    set_name: str | None
    cover_photo_id: int | None
    lost: bool
    """Open Totalverlust."""


class PieceBatch(ApiModel):
    pieces: list[Piece]
    set_id: int | None
    """The Set the pieces were put into, if any."""


class Repair(ApiModel):
    id: int
    recorded_on: dt.date
    note: str | None
    resolution_kind: str


class Damage(ApiModel):
    id: int
    recorded_on: dt.date
    note: str | None
    severe: bool
    kind: str
    open: bool
    repair: Repair | None
    photos: list[PhotoMeta]


class LoanWarning(ApiModel):
    """A conflict or hint from the availability check (D0007); also inside 409 errors."""

    code: str
    line_id: int | None
    piece_id: int | None
    material_type_id: int | None
    other_loan_id: int | None
    other_loan_title: str | None
    other_inventory_id: int | None
    item_label: str | None
    """What the warning is about, e.g. "12 × Seil (3 m)"."""
    available: int | None
    """Menge conflicts: what the Inventar has."""
    occupied: int | None
    """Menge conflicts: the peak already in use on one day."""
    requested: int | None


class PieceDetail(Piece):
    inventory_id: int
    photos: list[PhotoMeta]
    damages: list[Damage]
    found_again_eligible: bool
    warnings: list[LoanWarning]
    """Verleihe that still count on a lost or severely damaged piece."""


class StockLot(MaterialItemFields):
    """A Mengenposten: one Materialart in one variant combination (#12)."""

    id: int
    label: str | None
    variant: VariantMap
    quantity: int
    """Soll-Anzahl; never lowered by an open loss."""
    lost_quantity: int
    """Part of it that is lost and not yet resolved."""
    cover_photo_id: int | None
    photos: list[PhotoMeta]


class StockRow(ApiModel):
    """A Menge: a Materialart counted in Mengenposten."""

    material_type_id: int
    material_type_name: str
    unit: str | None
    variants: list[VariantAxis]
    quantity: int
    """What can be lent: active lots minus open losses."""
    lost_quantity: int
    cover_photo_id: int | None
    lots: list[StockLot]


class StockLoss(ApiModel):
    """Verlust or Verbrauch of a quantity, booked against a Mengenposten (D0009)."""

    id: int
    stock_lot_id: int
    material_type_id: int
    loan_line_id: int | None
    loan_id: int | None
    kind: StockLossKind
    quantity: int
    recorded_on: dt.date
    reason: str
    open: bool
    resolution: str | None
    resolved_on: dt.date | None
    resolution_note: str


# --- Sets --------------------------------------------------------------------------


class SetSummary(ApiModel):
    id: int
    inventory_id: int
    name: str
    short_name: str | None
    cover_photo_id: int | None
    assignment_piece_ids: list[int]
    optional_piece_ids: list[int]
    assignment_stock_type_ids: list[int]
    optional_stock_type_ids: list[int]


class SetStockLine(ApiModel):
    id: int
    material_type_id: int
    material_type_name: str
    stock_variant: VariantMap
    role: SetRole
    quantity: int


class SetDetail(SetSummary):
    photos: list[PhotoMeta]
    assignment_pieces: list[Piece]
    optional_pieces: list[Piece]
    assignment_stock: list[SetStockLine]
    optional_stock: list[SetStockLine]


# --- Loans -------------------------------------------------------------------------


class Group(ApiModel):
    id: int
    name: str


class Event(ApiModel):
    id: int
    name: str


class Loan(ApiModel):
    """A Verleih as listed."""

    id: int
    inventory_id: int
    inventory_name: str
    kind: LoanKind
    phase: LoanPhase
    group_id: int | None
    """No Gruppe yet on a draft (D0003)."""
    group_name: str
    borrower_user_id: int
    borrower_user_name: str
    borrower_phone: str
    """Empty unless the viewer is Materialwart*in of the Inventar."""
    contact_user_id: int | None
    contact_user_name: str | None
    contact_phone: str | None
    """Only for the Ausleihende*n."""
    event_id: int | None
    event_name: str | None
    wish_pickup_on: dt.date | None
    wish_return_on: dt.date | None
    pickup_on: dt.date | None
    return_on: dt.date | None
    pickup_note: str
    return_note: str
    cover_photo_id: int | None


class _LoanLineBase(ApiModel):
    id: int
    status: LoanLineStatus
    note: str
    reason: str
    replaces_line_id: int | None
    split_from_line_id: int | None
    request_notified: bool
    returned_quantity: int | None
    status_before_end: LoanLineStatus | None
    warnings: list[LoanWarning]
    origin_set_id: int | None
    origin_set_name: str | None
    origin_set_role: SetRole | None


class LoanLinePiece(_LoanLineBase):
    kind: Literal["piece"]
    piece_id: int
    piece_name: str
    material_type_name: str


class LoanLineStock(_LoanLineBase):
    kind: Literal["stock"]
    material_type_id: int
    material_type_name: str
    stock_variant: VariantMap
    """One variant combination per line (#12)."""
    quantity: int
    consumable: bool


LoanLine = TypeAliasType(
    "LoanLine",
    Annotated[Union[LoanLinePiece, LoanLineStock], Field(discriminator="kind")],
)


class SkippedPiece(ApiModel):
    """A Set piece left out when adding the Set (retired, lost, severely damaged)."""

    piece_id: int
    piece_name: str
    code: str


class OutboxMail(ApiModel):
    """A mail in the outbox (D0012): queued with the step, sent by the server."""

    id: int
    kind: str
    loan_id: int | None
    audience: str | None
    to: str
    subject: str
    pdf_kind: str | None
    status: OutboxStatus
    attempts: int
    last_error: str | None
    created_at: dt.datetime
    sent_at: dt.datetime | None
    next_attempt_at: dt.datetime | None


class LoanDetail(Loan):
    """A Verleih with its positions, warnings and mails."""

    warnings: list[LoanWarning]
    pickup_photos: list[PhotoMeta]
    return_photos: list[PhotoMeta]
    lines: list[LoanLine]
    has_pending_mail_changes: bool
    has_unnotified_requested_lines: bool
    mails: list[OutboxMail]
    """Outbox rows of this Verleih; empty unless the viewer is Materialwart*in."""
    skipped_pieces: list[SkippedPiece]
    """Only filled right after adding a Set."""


class JournalEntry(ApiModel):
    id: int
    created_at: dt.datetime
    kind: str
    payload: dict[str, Any]
    loan_id: int | None
    piece_id: int | None
    loan_line_id: int | None
    actor: UserRef | None
    real_actor: UserRef | None
    """Superuser who acted while impersonating ``actor``."""


class MailPreview(ApiModel):
    subject: str
    text: str
    html: str


# --- Calendar and dashboard --------------------------------------------------------


class CalendarItem(ApiModel):
    loan_id: int
    inventory_id: int
    inventory_name: str
    title: str
    phase: LoanPhase
    pickup_on: dt.date
    return_on: dt.date | None
    permanent: bool
    as_borrower: bool
    as_contact: bool


class CalendarItems(ApiModel):
    items: list[CalendarItem]


class CalendarFeed(ApiModel):
    id: int
    label: str
    scope: CalendarFeedScope
    inventory_id: int | None
    inventory_name: str
    created_at: dt.datetime


class CalendarFeeds(ApiModel):
    items: list[CalendarFeed]


class CalendarFeedCreated(CalendarFeed):
    token: str
    """Shown once; only its hash is stored."""
    path: str


class DashboardLoan(ApiModel):
    id: int
    inventory_id: int
    inventory_name: str
    title: str
    phase: LoanPhase
    return_on: dt.date | None


class DashboardCards(ApiModel):
    conflicts: list[DashboardLoan]
    stuck_mails: list[DashboardLoan]
    open_requests: list[DashboardLoan]
    waiting: list[DashboardLoan]
    returns_due: list[DashboardLoan]
    overdue: list[DashboardLoan]
    open_actions: list[DashboardLoan]
    my_loans: list[DashboardLoan]


class Dashboard(ApiModel):
    welcome_name: str
    can_manage: bool
    cards: DashboardCards


# --- Mail diagnostics --------------------------------------------------------------


class MailStatus(ApiModel):
    configured: bool
    host: str
    port: int
    from_address: str
    mode: str
    has_credentials: bool


class MailTestStarted(ApiModel):
    id: str


class MailTestJob(ApiModel):
    status: MailTestStatus
    detail: str | None


# --- Errors ------------------------------------------------------------------------


class ErrorResponse(ApiModel):
    """Every 4xx/5xx answer of the API."""

    error: str
    """Code, translated by the client (``errors.<code>``)."""
    conflicts: list[LoanWarning] = []
    """Only for availability errors (409)."""
