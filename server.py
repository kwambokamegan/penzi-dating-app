from flask import Flask, request, jsonify
from flask_cors import CORS

import services
from sms_handler import handle_message

app = Flask(__name__)
CORS(app)


@app.errorhandler(ConnectionError)
def database_down(error):
    return jsonify({"error": "Database unavailable"}), 500


@app.route("/sms", methods=["POST"])
def sms():
    data = request.get_json() or {}
    phone = data.get("phone", "").strip()
    message = data.get("message", "").strip()
    if not phone or not message:
        return jsonify({"reply": "Missing phone or message."}), 400
    return jsonify({"reply": handle_message(phone, message)})


@app.route("/api/stats", methods=["GET"])
def stats():
    return jsonify(services.dashboard_stats())


@app.route("/api/users", methods=["GET"])
def users():
    return jsonify(services.recent_users())


@app.route("/api/interest-requests", methods=["GET"])
def interest_requests():
    return jsonify(services.recent_interests())


@app.route("/api/outbox/<phone>", methods=["GET"])
def outbox(phone):
    return jsonify(services.pending_messages_for(phone))


@app.route("/api/followups/run", methods=["POST"])
def run_followups():
    minutes = request.args.get(
        "minutes", default=services.DETAILS_FOLLOWUP_MINUTES, type=int
    )
    return jsonify({"sent": services.send_details_followups(minutes)})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
