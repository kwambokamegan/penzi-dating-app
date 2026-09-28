from flask import Flask, request, jsonify
from flask_cors import CORS
from sms_handler import handle_message

app = Flask(__name__)
CORS(app)

@app.route("/sms", methods=["POST"])
def sms():
    data = request.get_json()
    phone = data.get("phone", "").strip()
    message = data.get("message", "").strip()

    if not phone or not message:
        return jsonify({"reply": "Missing phone or message."}), 400

    reply = handle_message(phone, message)
    return jsonify({"reply": reply})

from db import get_connection


@app.route("/api/stats", methods=["GET"])
def stats():
    conn = get_connection()
    if conn is None:
        return jsonify({"error": "DB connection failed"}), 500
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS total FROM users")
    total_users = cursor.fetchone()["total"]

    cursor.execute(
        "SELECT COUNT(*) AS total FROM users WHERE registration_stage = 'complete'"
    )
    complete_profiles = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM match_searches")
    total_searches = cursor.fetchone()["total"]

    cursor.execute(
        "SELECT COUNT(*) AS total FROM interest_requests WHERE status = 'notified'"
    )
    pending_requests = cursor.fetchone()["total"]

    cursor.close()
    conn.close()

    return jsonify({
        "total_users": total_users,
        "complete_profiles": complete_profiles,
        "total_searches": total_searches,
        "pending_requests": pending_requests
    })


@app.route("/api/users", methods=["GET"])
def users_list():
    conn = get_connection()
    if conn is None:
        return jsonify({"error": "DB connection failed"}), 500
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT phone_number, name, age, gender, county, town, registration_stage
        FROM users ORDER BY id DESC LIMIT 20
        """
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(rows)


@app.route("/api/interest-requests", methods=["GET"])
def interest_requests_list():
    conn = get_connection()
    if conn is None:
        return jsonify({"error": "DB connection failed"}), 500
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT requester_phone, target_phone, status, created_at
        FROM interest_requests ORDER BY id DESC LIMIT 20
        """
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(rows)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
