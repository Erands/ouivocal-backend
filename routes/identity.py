"""HTTP adapters for the implemented identity service operations."""

from flask import Blueprint, jsonify, request
import jwt
import psycopg

from identity import service as identity_service
from identity.config import IdentityConfigurationError
from identity.database import connection
from identity.repository import Repository
from identity.security import decode_access_token
from identity.validation import ValidationError


identity_bp = Blueprint("identity", __name__, url_prefix="/identity")


def _request_data() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError("A JSON object is required")
    return data


def _run(operation, success_status: int = 200):
    try:
        with connection() as conn:
            result = operation(Repository(conn))
    except (IdentityConfigurationError, psycopg.Error):
        return jsonify(error="Identity service is unavailable"), 503
    except (ValidationError, ValueError):
        return jsonify(error="Invalid identity request"), 400
    except LookupError:
        return jsonify(error="Identity resource was not found"), 404
    except PermissionError:
        return jsonify(error="Invalid credentials"), 401
    return jsonify(result), success_status


def _current_user_id() -> str:
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise PermissionError("Authentication is required")
    try:
        return decode_access_token(token.strip())
    except jwt.InvalidTokenError as error:
        raise PermissionError("Authentication is required") from error


@identity_bp.post("/register")
def register():
    return _run(lambda repo: identity_service.register(repo, _request_data()), 201)


@identity_bp.post("/login")
def login():
    data = _request_data()
    return _run(lambda repo: identity_service.login(repo, data.get("email"), data.get("password")))


@identity_bp.post("/refresh")
def refresh():
    data = _request_data()
    return _run(lambda repo: identity_service.refresh(repo, data.get("refresh_token")))


@identity_bp.get("/users/search")
def search_users():
    try:
        current_user_id = _current_user_id()
    except IdentityConfigurationError:
        return jsonify(error="Identity service is unavailable"), 503
    except PermissionError:
        return jsonify(error="Authentication is required"), 401
    return _run(
        lambda repo: identity_service.search_users(
            repo, current_user_id, request.args.get("q")
        )
    )


@identity_bp.post("/conversations")
def create_conversation():
    try:
        current_user_id = _current_user_id()
    except IdentityConfigurationError:
        return jsonify(error="Identity service is unavailable"), 503
    except PermissionError:
        return jsonify(error="Authentication is required"), 401
    return _run(
        lambda repo: identity_service.create_direct_conversation(
            repo, current_user_id, _request_data()
        ),
        201,
    )


def inactive():
    return jsonify(error="Identity operation is not activated"), 503


for rule, methods in [
    ("/logout", ["POST"]),
    ("/me", ["GET", "PATCH"]),
    ("/ouivocal-id/check", ["GET"]),
    ("/users/<ouivocal_id>", ["GET"]),
    ("/me/languages", ["GET", "PUT"]),
    ("/conversations", ["GET"]),
]:
    identity_bp.add_url_rule(
        rule,
        endpoint=rule.replace("/", "_").replace("<", "").replace(">", "") or "root",
        view_func=inactive,
        methods=methods,
    )
