"""OpenAPI 3.1 document of the JSON API, built from the routes' ``@responds``.

``lamathek openapi`` writes it to ``lamathek/domain/openapi.json``; the web client
generates its zod schemas from that file (``npm run generate:api``). Request
bodies and query parameters are not described yet.
"""

import json
import re
from http import HTTPStatus
from pathlib import Path
from typing import Any

from flask import Flask
from pydantic import TypeAdapter
from pydantic.json_schema import GenerateJsonSchema

from lamathek.contract import JSON, ContractViolation, contract_of
from lamathek.contract.models import ErrorResponse

OPENAPI_PATH = Path(__file__).resolve().parent.parent / "domain" / "openapi.json"

_REF = "#/components/schemas/{model}"
_METHOD_ORDER = ("get", "post", "put", "patch", "delete")
_PARAM = re.compile(r"<(?:(\w+):)?(\w+)>")


def _path_and_parameters(rule: str) -> tuple[str, list[dict]]:
    parameters = []
    for converter, name in _PARAM.findall(rule):
        schema = {"type": "integer"} if converter == "int" else {"type": "string"}
        parameters.append({"name": name, "in": "path", "required": True, "schema": schema})
    return _PARAM.sub(lambda m: "{" + m.group(2) + "}", rule), parameters


def _summary(view) -> str | None:
    doc = (getattr(view, "__doc__", None) or "").strip()
    return doc.splitlines()[0] if doc else None


def build_openapi(app: Flask) -> dict[str, Any]:
    routes = []
    for rule in app.url_map.iter_rules():
        if not rule.rule.startswith("/api/"):
            continue
        view = app.view_functions[rule.endpoint]
        contract = contract_of(view)
        if contract is None:
            raise ContractViolation(f"route {rule.endpoint} declares no @responds")
        routes.append((rule, view, contract))

    bodies = {ErrorResponse}
    bodies.update(c.body for _, _, c in routes if c.body is not None and c.mimetype == JSON)
    generator = GenerateJsonSchema(ref_template=_REF)
    schemas, definitions = generator.generate_definitions(
        [(body, "validation", _adapter_core_schema(body)) for body in bodies]
    )

    def body_schema(body) -> dict:
        return schemas[(body, "validation")]

    paths: dict[str, dict] = {}
    for rule, view, contract in sorted(routes, key=lambda r: r[0].rule):
        path, parameters = _path_and_parameters(rule.rule)
        status = str(contract.status)
        success: dict[str, Any] = {"description": HTTPStatus(contract.status).phrase}
        if contract.mimetype != JSON:
            success["content"] = {
                contract.mimetype: {"schema": {"type": "string", "format": "binary"}}
            }
        elif contract.body is not None:
            success["content"] = {JSON: {"schema": body_schema(contract.body)}}
        for method in sorted(
            (m.lower() for m in rule.methods if m not in ("HEAD", "OPTIONS")),
            key=_METHOD_ORDER.index,
        ):
            operation: dict[str, Any] = {
                "operationId": rule.endpoint,
                "tags": [rule.endpoint.split(".")[0]],
            }
            summary = _summary(view)
            if summary:
                operation["summary"] = summary
            if parameters:
                operation["parameters"] = parameters
            operation["responses"] = {
                status: success,
                "default": {"$ref": "#/components/responses/Error"},
            }
            paths.setdefault(path, {})[method] = operation

    return {
        "openapi": "3.1.0",
        "info": {
            "title": "LaMathek API",
            "version": "1",
            "description": "Generated from the Pydantic models in lamathek/contract "
            "(`lamathek openapi`). Do not edit.",
        },
        "paths": paths,
        "components": {
            "schemas": {name: _without_titles(s) for name, s in sorted(definitions.items())},
            "responses": {
                "Error": {
                    "description": "Error",
                    "content": {JSON: {"schema": body_schema(ErrorResponse)}},
                }
            },
        },
    }


def _without_titles(node: Any, *, property_map: bool = False) -> Any:
    """Drop Pydantic's generated titles; component names and descriptions say it all."""
    if isinstance(node, list):
        return [_without_titles(item) for item in node]
    if not isinstance(node, dict):
        return node
    return {
        key: _without_titles(value, property_map=key == "properties" and not property_map)
        for key, value in node.items()
        # In a "properties" map, "title" is a field name, not a title.
        if property_map or key != "title"
    }


def _adapter_core_schema(body):
    return TypeAdapter(body).core_schema


def render_openapi(app: Flask) -> str:
    return json.dumps(build_openapi(app), indent=2, ensure_ascii=False) + "\n"


def export_app() -> Flask:
    """An app instance only for reading routes: no database file, no worker."""
    from lamathek.app import create_app
    from lamathek.config import Config

    class ExportConfig(Config):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = "sqlite://"
        API_CONTRACT_CHECK = False

    return create_app(ExportConfig)


def write_openapi(path: Path = OPENAPI_PATH) -> Path:
    path.write_text(render_openapi(export_app()), encoding="utf-8")
    return path
