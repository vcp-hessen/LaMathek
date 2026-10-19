"""Mail-Outbox: steps never depend on SMTP, mails retry and can be resent."""

from datetime import timedelta

from sqlalchemy import select

from lamathek.db import get_session
from lamathek.models.journal import LoanJournalEntry
from lamathek.models.mail import MailOutbox
from lamathek.services.loan_notifications import set_mail_sender_for_tests
from lamathek.services.outbox import _claim, process_outbox_once, utcnow
from test_availability import World


class Mailbox:
    def __init__(self):
        self.sent: list[dict] = []
        self.fail = False

    def __call__(self, to, subject, text, html, cc, attachments=None):
        if self.fail:
            raise RuntimeError("smtp down")
        self.sent.append({"to": to, "attachments": attachments or []})


def _rows(w: World) -> list[MailOutbox]:
    with w.app.app_context():
        session = get_session()
        rows = session.scalars(select(MailOutbox).order_by(MailOutbox.id)).all()
        session.expunge_all()
        return rows


def _drain(w: World, *, at=None) -> None:
    with w.app.app_context():
        process_outbox_once(get_session(), at)


def _journal_kinds(w: World, loan_id: int) -> list[str]:
    with w.app.app_context():
        return [
            e.kind
            for e in get_session().scalars(
                select(LoanJournalEntry).where(LoanJournalEntry.loan_id == loan_id)
            )
        ]


def test_step_completes_when_smtp_fails_and_mail_retries_later():
    box = Mailbox()
    set_mail_sender_for_tests(box)
    w = World()
    try:
        kohte = w.piece()
        box.fail = True
        loan = w.loan([{"pieceId": kohte}], 5, 7)  # the request mails fail
        detail = w.detail(loan)
        assert detail["phase"] == "review"
        assert {m["status"] for m in detail["mails"]} == {"pending"}
        assert all(m["attempts"] == 1 and m["lastError"] == "smtp down" for m in detail["mails"])
        assert _journal_kinds(w, loan).count("workflow.complete_step") == 1

        box.fail = False
        _drain(w)  # not due yet: backoff
        assert box.sent == []
        _drain(w, at=utcnow() + timedelta(minutes=2))
        assert sorted(m["to"] for m in box.sent) == ["borrower@test.example", "mgr@test.example"]
        assert {m["status"] for m in w.detail(loan)["mails"]} == {"sent"}
        assert _journal_kinds(w, loan).count("mail.sent") == 2
    finally:
        set_mail_sender_for_tests(None)
        w.close()


def test_mail_gives_up_after_all_attempts_and_can_be_resent():
    box = Mailbox()
    set_mail_sender_for_tests(box)
    w = World()
    try:
        kohte = w.piece()
        box.fail = True
        loan = w.loan([{"pieceId": kohte}], 5, 7)
        later = utcnow()
        for _ in range(6):
            later += timedelta(hours=7)
            _drain(w, at=later)
        mails = w.detail(loan)["mails"]
        assert {m["status"] for m in mails} == {"failed"}
        assert "mail.failed" in _journal_kinds(w, loan)

        box.fail = False
        w.as_("borrower")
        assert w.client.post(f"/api/loans/{loan}/mails/{mails[0]['id']}/resend").status_code == 403
        w.as_("mgr")
        resent = w.client.post(f"/api/loans/{loan}/mails/{mails[0]['id']}/resend")
        assert resent.status_code == 200
        queued = {m["id"]: m for m in resent.get_json()["mails"]}
        assert (queued[mails[0]["id"]]["status"], queued[mails[0]["id"]]["attempts"]) == ("pending", 0)
        statuses = {m["id"]: m["status"] for m in w.detail(loan)["mails"]}
        assert statuses[mails[0]["id"]] == "sent"
        w.as_("su")
        failed = w.client.get("/api/mail/outbox").get_json()
        assert [m["id"] for m in failed] == [mails[1]["id"]]
    finally:
        set_mail_sender_for_tests(None)
        w.close()


def test_pdf_lists_go_to_materialwarte_only_and_not_with_the_request():
    box = Mailbox()
    set_mail_sender_for_tests(box)
    w = World()
    try:
        kohte = w.piece()
        loan = w.loan([{"pieceId": kohte}], 5, 7)
        assert all(m["attachments"] == [] for m in box.sent)
        box.sent.clear()
        assert w.confirm(loan).status_code == 200
        assert w.step(loan).status_code == 200  # closes review → Packliste
        by_to = {m["to"]: m for m in box.sent}
        assert by_to["borrower@test.example"]["attachments"] == []
        manager_files = [a[0] for a in by_to["mgr@test.example"]["attachments"]]
        assert len(manager_files) == 1 and manager_files[0].startswith("lamathek-pack-")
    finally:
        set_mail_sender_for_tests(None)
        w.close()


def test_borrower_without_address_is_journaled_not_queued():
    box = Mailbox()
    set_mail_sender_for_tests(box)
    w = World()
    try:
        with w.app.app_context():
            from lamathek.models.user import User

            session = get_session()
            session.get(User, w.bor).email = None
            session.commit()
        kohte = w.piece()
        loan = w.loan([{"pieceId": kohte}], 5, 7)
        assert [m["to"] for m in box.sent] == ["mgr@test.example"]
        assert "mail.skipped" in _journal_kinds(w, loan)
    finally:
        set_mail_sender_for_tests(None)
        w.close()


def test_a_claimed_mail_is_not_claimed_twice():
    box = Mailbox()
    set_mail_sender_for_tests(box)
    w = World()
    try:
        w.app.config["OUTBOX_DRAIN_IN_TESTS"] = False
        kohte = w.piece()
        w.loan([{"pieceId": kohte}], 5, 7)
        now = utcnow()
        with w.app.app_context():
            first = _claim(get_session(), now)
        with w.app.app_context():
            second = _claim(get_session(), now)
        assert len(first) == 2 and second == []
        # After the lease expires (crashed worker) the mail is picked up again.
        with w.app.app_context():
            assert sorted(_claim(get_session(), now + timedelta(minutes=6))) == sorted(first)
    finally:
        set_mail_sender_for_tests(None)
        w.close()


def test_background_worker_sends_right_after_the_commit(tmp_path):
    """The real thread (off in other tests): enqueue → commit → delivered."""
    import time

    from lamathek.app import create_app
    from lamathek.config import Config
    from lamathek import db
    from lamathek.db import Base
    from lamathek.services.outbox import enqueue

    class WorkerConfig(Config):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path / 'w.sqlite3'}"
        SECRET_KEY = "worker-test"
        DEBUG = False
        TESTING = False
        MAIL_OUTBOX_WORKER = True

    box = Mailbox()
    set_mail_sender_for_tests(box)
    try:
        app = create_app(WorkerConfig)
        with app.app_context():
            Base.metadata.create_all(db.engine)
            session = get_session()
            enqueue(session, kind="test", to="a@example.org", subject="s", text="t")
            session.commit()
        deadline = time.time() + 5
        while not box.sent and time.time() < deadline:
            time.sleep(0.05)
        assert [m["to"] for m in box.sent] == ["a@example.org"]
    finally:
        set_mail_sender_for_tests(None)


def test_without_smtp_no_mail_is_queued_and_the_journal_says_so():
    set_mail_sender_for_tests(None)  # the real sender, and no SMTP in tests
    w = World()
    try:
        kohte = w.piece()
        loan = w.loan([{"pieceId": kohte}], 5, 7)
        assert _rows(w) == []
        assert "mail.skipped" in _journal_kinds(w, loan)
    finally:
        w.close()
