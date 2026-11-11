"""Router registration. Every module router is mounted under /api/v1."""
from importlib import import_module

from fastapi import FastAPI

MODULES = [
    "auth", "admin", "students", "lifecycle", "loans", "repayments", "parties", "risk", "cases", "field",
    "comms", "grievances", "portal", "reports", "audit", "dashboard", "search", "notifications",
]


def register_routers(app: FastAPI) -> None:
    for name in MODULES:
        try:
            mod = import_module(f"app.modules.{name}.api")
        except ModuleNotFoundError as exc:
            if exc.name and exc.name.startswith(f"app.modules.{name}"):
                continue
            raise
        app.include_router(mod.router, prefix="/api/v1")
