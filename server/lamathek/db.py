from flask import Flask, g
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


engine = None
SessionLocal = None


def init_db(app: Flask) -> None:
    global engine, SessionLocal
    engine = create_engine(
        app.config["SQLALCHEMY_DATABASE_URI"],
        connect_args={"check_same_thread": False},
    )
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
