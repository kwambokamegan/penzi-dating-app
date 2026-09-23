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

if __name__ == "__main__":
    app.run(debug=True, port=5000)
