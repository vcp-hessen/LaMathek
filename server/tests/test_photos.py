import io
import os
import tempfile
from pathlib import Path

from PIL import Image

from lamathek.app import create_app
from lamathek.config import Config
from lamathek import db
from lamathek.db import Base, get_session
from lamathek.services.photo_storage import original_path, thumb_path
from lamathek.services.settings import get_installation_settings
from lamathek.services.users import upsert_user_from_oidc


def _tiny_jpeg() -> bytes:
    image = Image.new("RGB", (32, 24), color=(200, 40, 40))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def _app_with_db():
    tmp = tempfile.TemporaryDirectory()
    db_path = os.path.join(tmp.name, "test.sqlite3")
    media_path = os.path.join(tmp.name, "media")
    os.environ["MEDIA_PATH"] = media_path

    class TestConfig(Config):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
        TESTING = True

    app = create_app(TestConfig)
    with app.app_context():
        Base.metadata.create_all(db.engine)
        get_installation_settings(get_session())
    return app, tmp, Path(media_path)


def _login(client, sub: str):
    with client.session_transaction() as sess:
        sess["user"] = {"sub": sub, "name": sub, "email": None}


def _setup_inventory_and_piece(client):
    _login(client, "su")
    inv = client.post("/api/inventories", json={"name": "Donnerskopf"})
    assert inv.status_code == 201
    inventory_id = inv.get_json()["id"]
    mt = client.post(
        f"/api/inventories/{inventory_id}/material-types",
        json={"name": "Kohte", "tracking": "piece", "variants": []},
    )
    assert mt.status_code == 201
    material_type_id = mt.get_json()["id"]
    piece = client.post(
        f"/api/inventories/{inventory_id}/pieces",
        json={"materialTypeId": material_type_id, "name": "K1"},
    )
    assert piece.status_code == 201
    return inventory_id, material_type_id, piece.get_json()["id"]


def test_upload_stores_webp_and_thumbnail():
    app, tmp, media_root = _app_with_db()
    try:
        with app.app_context():
            session = get_session()
            upsert_user_from_oidc(
                session,
                sub="su",
                name="SU",
                email=None,
                force_superuser=True,
            )
            session.commit()

        client = app.test_client()
        _, _, piece_id = _setup_inventory_and_piece(client)

        response = client.post(
            f"/api/pieces/{piece_id}/photos",
            data={"file": (io.BytesIO(_tiny_jpeg()), "test.jpg")},
            content_type="multipart/form-data",
        )
        assert response.status_code == 201
        photo_id = response.get_json()["id"]
        assert original_path(photo_id).is_file()
        assert thumb_path(photo_id, 160).is_file()
        assert original_path(photo_id).read_bytes()[:4] == b"RIFF"

        file_response = client.get(f"/api/photos/{photo_id}?size=160")
        assert file_response.status_code == 200
        assert file_response.mimetype == "image/webp"
    finally:
        tmp.cleanup()
        os.environ.pop("MEDIA_PATH", None)


def test_invalid_upload_rejected():
    app, tmp, _media_root = _app_with_db()
    try:
        with app.app_context():
            session = get_session()
            upsert_user_from_oidc(
                session,
                sub="su",
                name="SU",
                email=None,
                force_superuser=True,
            )
            session.commit()

        client = app.test_client()
        _, _, piece_id = _setup_inventory_and_piece(client)
        response = client.post(
            f"/api/pieces/{piece_id}/photos",
            data={"file": (io.BytesIO(b"not-an-image"), "bad.jpg")},
            content_type="multipart/form-data",
        )
        assert response.status_code == 400
        assert response.get_json()["error"] == "invalid_image"
    finally:
        tmp.cleanup()
        os.environ.pop("MEDIA_PATH", None)


def test_piece_delete_removes_photo_files():
    app, tmp, _media_root = _app_with_db()
    try:
        with app.app_context():
            session = get_session()
            upsert_user_from_oidc(
                session,
                sub="su",
                name="SU",
                email=None,
                force_superuser=True,
            )
            session.commit()

        client = app.test_client()
        inventory_id, _, piece_id = _setup_inventory_and_piece(client)
        upload = client.post(
            f"/api/pieces/{piece_id}/photos",
            data={"file": (io.BytesIO(_tiny_jpeg()), "test.jpg")},
            content_type="multipart/form-data",
        )
        photo_id = upload.get_json()["id"]
        assert original_path(photo_id).is_file()

        deleted = client.delete(f"/api/pieces/{piece_id}")
        assert deleted.status_code == 204
        assert not original_path(photo_id).is_file()
        assert not thumb_path(photo_id, 160).exists()
    finally:
        tmp.cleanup()
        os.environ.pop("MEDIA_PATH", None)


def test_piece_list_cover_falls_back_to_material_type():
    app, tmp, _media_root = _app_with_db()
    try:
        with app.app_context():
            session = get_session()
            upsert_user_from_oidc(
                session,
                sub="su",
                name="SU",
                email=None,
                force_superuser=True,
            )
            session.commit()

        client = app.test_client()
        inventory_id, material_type_id, piece_id = _setup_inventory_and_piece(client)
        type_photo = client.post(
            f"/api/material-types/{material_type_id}/photos",
            data={"file": (io.BytesIO(_tiny_jpeg()), "ref.jpg")},
            content_type="multipart/form-data",
        )
        assert type_photo.status_code == 201
        ref_id = type_photo.get_json()["id"]

        listed = client.get(f"/api/inventories/{inventory_id}/pieces")
        assert listed.status_code == 200
        row = next(item for item in listed.get_json() if item["id"] == piece_id)
        assert row["coverPhotoId"] == ref_id
    finally:
        tmp.cleanup()
        os.environ.pop("MEDIA_PATH", None)
