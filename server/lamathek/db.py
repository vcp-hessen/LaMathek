from flask import Flask, g
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


engine = None
SessionLocal = None


def init_db(app: Flask) -> None:
    global engine, SessionLocal
    def _sqlite_connect(dbapi_connection, _connection_record):
        if dbapi_connection.__class__.__module__.startswith("sqlite3"):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    engine = create_engine(
        app.config["SQLALCHEMY_DATABASE_URI"],
        connect_args={"check_same_thread": False},
    )
    if engine.dialect.name == "sqlite":
        from sqlalchemy import event

        event.listen(engine, "connect", _sqlite_connect)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    @app.teardown_appcontext
    def close_db_session(_exc=None):
        session = g.pop("db_session", None)
        if session is not None:
            session.close()


def get_session() -> Session:
    if "db_session" not in g:
        g.db_session = SessionLocal()
    return g.db_session
