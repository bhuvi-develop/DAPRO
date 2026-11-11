"""Shared test fixtures.

Tests run against a dedicated database (dapro_test) on the compose PostgreSQL, created fresh per session,
migrated with Alembic (as the owner) and seeded with the DEMO dataset. The API under test connects as
dapro_app, so row-level security is exercised for real. Set DAPRO_TEST_TESTCONTAINERS=1 to start a
throwaway PostgreSQL 16 with Testcontainers instead.
"""
import os
import re

TEST_DB = os.environ.get("DAPRO_TEST_DB", "dapro_test")


def _swap_db(url: str, name: str) -> str:
    return re.sub(r"/[^/]+$", f"/{name}", url)


if os.environ.get("DAPRO_TEST_TESTCONTAINERS") == "1":  # pragma: no cover
    from testcontainers.postgres import PostgresContainer

    _pg = PostgresContainer("postgres:16.4-alpine", username="dapro_owner", password="owner", dbname=TEST_DB)
    _pg.start()
    _base = _pg.get_connection_url().replace("psycopg2", "psycopg")
    os.environ["DAPRO_DATABASE_OWNER_URL"] = _base
    os.environ["DAPRO_DATABASE_URL"] = re.sub(r"//[^@]+@", "//dapro_app:dapro_app@", _base)
    os.environ["DAPRO_APP_DB_PASSWORD"] = "dapro_app"
else:
    os.environ["DAPRO_DATABASE_OWNER_URL"] = _swap_db(os.environ["DAPRO_DATABASE_OWNER_URL"], TEST_DB)
    os.environ["DAPRO_DATABASE_URL"] = _swap_db(os.environ["DAPRO_DATABASE_URL"], TEST_DB)
os.environ["DAPRO_ENV"] = "test"
os.environ["DAPRO_CELERY_EAGER"] = "true"
os.environ["DAPRO_LOGIN_RATE_PER_MINUTE"] = "100000"
os.environ.setdefault("DAPRO_STORAGE_DIR", "/tmp/dapro-test-storage")

import pytest  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

DEMO_PASSWORD = os.environ.get("DAPRO_DEMO_PASSWORD", "Demo@12345")

USERS = {
    "platform": "platform.admin@dapro.demo", "college_admin": "priya.admin@nbit.demo",
    "college_officer": "officer@nbit.demo", "rce_admin": "admin@rce.demo", "bank_admin": "admin@anb.demo",
    "loan_ops": "ravi.ops@anb.demo", "investigator": "investigator@anb.demo", "manager": "meena.manager@anb.demo",
    "manager_all": "head.followup@anb.demo", "field": "karthik.field@anb.demo", "field2": "nithya.field@anb.demo",
    "auditor": "sanjay.audit@anb.demo", "mfb_ops": "ops@mfb.demo", "mfb_manager": "manager@mfb.demo",
    "iso_college": "admin@isocollege.demo", "iso_bank": "ops@isobank.demo",
}


def _create_database():
    if os.environ.get("DAPRO_TEST_TESTCONTAINERS") == "1":
        return
    admin = create_engine(_swap_db(os.environ["DAPRO_DATABASE_OWNER_URL"], "postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as c:
        c.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)"))
        c.execute(text(f"CREATE DATABASE {TEST_DB}"))
    admin.dispose()


@pytest.fixture(scope="session", autouse=True)
def database():
    _create_database()
    from alembic import command
    from alembic.config import Config

    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "migrations"))
    command.upgrade(cfg, "head")
    from app.core.db import OwnerSessionLocal
    from app.seed.run import seed_all

    db = OwnerSessionLocal()
    seed_all(db)
    db.commit()
    db.close()
    yield


@pytest.fixture(scope="session")
def client(database):
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


_tokens: dict[str, str] = {}


def login(client, who: str) -> dict:
    if who not in _tokens:
        r = client.post("/api/v1/auth/login", json={"email": USERS.get(who, who), "password": DEMO_PASSWORD})
        assert r.status_code == 200, r.text
        _tokens[who] = r.json()["access_token"]
    return {"Authorization": f"Bearer {_tokens[who]}"}


@pytest.fixture(scope="session")
def auth(client):
    return lambda who: login(client, who)


@pytest.fixture()
def owner_db():
    from app.core.db import OwnerSessionLocal

    db = OwnerSessionLocal()
    yield db
    db.rollback()
    db.close()
