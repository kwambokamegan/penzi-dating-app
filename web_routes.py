import os
from functools import wraps

from dotenv import load_dotenv
from flask import Blueprint, jsonify, request, send_from_directory, session

import messages
import services

load_dotenv()

bp = Blueprint("web", __name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def register(app):
    secret = os.getenv("SECRET_KEY")
    if not secret:
        raise RuntimeError("SECRET_KEY is missing from .env")
    app.secret_key = secret
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.register_blueprint(bp)


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        phone = session.get("phone")
        user = services.user_by_phone(phone) if phone else None
        if user is None:
            session.clear()
            return jsonify({"error": messages.LOGIN_REQUIRED}), 401
        return view(user, *args, **kwargs)
    return wrapper


@bp.route("/inbox.html")
def inbox_page():
    return send_from_directory(BASE_DIR, "inbox.html")


@bp.route("/api/login/request", methods=["POST"])
def login_request():
    data = request.get_json(silent=True) or {}
    reply = services.request_login_code(str(data.get("phone", "")))
    return jsonify({"message": reply})


@bp.route("/api/login/verify", methods=["POST"])
def login_verify():
    data = request.get_json(silent=True) or {}
    user, error = services.verify_login_code(
        str(data.get("phone", "")), str(data.get("code", ""))
    )
    if error:
        return jsonify({"error": error}), 401
    session.clear()
    session["phone"] = user["phone_number"]
    return jsonify({"ok": True, "name": messages.first_name(user["name"])})


@bp.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})


@bp.route("/api/me/interests", methods=["GET"])
@login_required
def my_interests(user):
    data = services.my_interests(user)
    data["name"] = messages.first_name(user["name"])
    return jsonify(data)


@bp.route("/api/me/interests/<int:interest_id>/respond", methods=["POST"])
@login_required
def respond(user, interest_id):
    data = request.get_json(silent=True) or {}
    accept = data.get("accept")
    if not isinstance(accept, bool):
        return jsonify({"error": "accept must be true or false"}), 400
    ok, reply = services.respond_to_interest(user, interest_id, accept)
    return jsonify({"ok": ok, "reply": reply}), (200 if ok else 400)


from sms_handler import handle_message


@bp.route("/api/me/command", methods=["POST"])
@login_required
def command(user):
    data = request.get_json(silent=True) or {}
    text = str(data.get("message", "")).strip()
    if not text:
        return jsonify({"error": "Please type a message."}), 400
    return jsonify({"reply": handle_message(user["phone_number"], text)})


@bp.route("/api/login/password", methods=["POST"])
def login_password():
    data = request.get_json(silent=True) or {}
    user, error = services.login_with_password(
        str(data.get("phone", "")), str(data.get("password", ""))
    )
    if error:
        return jsonify({"error": error}), 401
    session.clear()
    session["phone"] = user["phone_number"]
    return jsonify({"ok": True, "name": messages.first_name(user["name"])})


@bp.route("/api/password/set", methods=["POST"])
def password_set():
    data = request.get_json(silent=True) or {}
    user, error = services.set_password_with_code(
        str(data.get("phone", "")),
        str(data.get("code", "")),
        str(data.get("password", "")),
    )
    if error:
        return jsonify({"error": error}), 400
    session.clear()
    session["phone"] = user["phone_number"]
    return jsonify({"ok": True, "message": messages.PASSWORD_SET_OK})



@bp.route("/api/setup/check", methods=["POST"])
def setup_check():
    data = request.get_json(silent=True) or {}
    user = services.setup_user(str(data.get("phone", "")), str(data.get("token", "")))
    if user is None:
        return jsonify({"ok": False}), 200
    return jsonify({"ok": True, "name": messages.first_name(user["name"]),
                    "phone": user["phone_number"]})


@bp.route("/api/setup/set", methods=["POST"])
def setup_set():
    data = request.get_json(silent=True) or {}
    user, error = services.set_first_password(
        str(data.get("phone", "")), str(data.get("token", "")),
        str(data.get("password", "")),
    )
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"ok": True})



@bp.route("/welcome.html")
def welcome_page():
    return send_from_directory(BASE_DIR, "welcome.html")


@bp.route("/welcome.jpg")
def welcome_photo():
    return send_from_directory(BASE_DIR, "welcome.jpg")
