from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

import messages
import repository
import services
from sms_handler import handle_message

app = Flask(__name__)
CORS(app)

@app.route("/")
def simulator_home():
    return send_from_directory(".", "simulator.html")


@app.route("/simulator.html")
def simulator_page():
    return send_from_directory(".", "simulator.html")



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


@app.route("/api/greeting/<phone>", methods=["GET"])
def greeting(phone):
    """
    Welcome message for a number that has neither registered nor
    activated yet. Returns {"reply": null} for everyone else.
    """
    phone = phone.strip()
    user = repository.get_user_by_phone(phone)
    if user is None and not repository.is_activated(phone):
        return jsonify({"reply": messages.NOT_ACTIVATED})
    return jsonify({"reply": None})


@app.route("/api/outbox/<phone>", methods=["GET"])
def outbox(phone):
    return jsonify(services.pending_messages_for(phone))


@app.route("/api/followups/run", methods=["POST"])
def run_followups():
    minutes = request.args.get(
        "minutes", default=services.DETAILS_FOLLOWUP_MINUTES, type=int
    )
    return jsonify({"sent": services.send_details_followups(minutes)})


import web_routes

web_routes.register(app)


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=False, port=5000)
