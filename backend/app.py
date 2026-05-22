"""
app.py
Partie 4 — Dashboard Web temps réel
"""

from flask import Flask, render_template, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import logging

# ─── Configuration ─────────────────────────────────────────────────────────────
MONGO_URI  = "mongodb+srv://badre:123@cluster0.efcymvu.mongodb.net/?appName=Cluster0"
DB_NAME    = "irrigation_db"
COLL_NAME  = "soil_data"
ALERT_THR  = 30

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

# ─── MongoDB ───────────────────────────────────────────────────────────────────
try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_client.server_info()
    collection = mongo_client[DB_NAME][COLL_NAME]
    print("MongoDB connecte !")
except Exception as e:
    print("Erreur MongoDB :", e)
    collection = None


# ─── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/api/latest")
def get_latest():
    if collection is None:
        return jsonify({}), 500
    doc = collection.find_one({}, {"_id": 0}, sort=[("_id", -1)])
    return jsonify(doc or {})


@app.route("/api/history")
def get_history():
    if collection is None:
        return jsonify([]), 500
    docs = list(collection.find({}, {"_id": 0})
                          .sort("_id", -1)
                          .limit(50))
    docs.reverse()
    return jsonify(docs)


@app.route("/api/stats")
def get_stats():
    if collection is None:
        return jsonify({}), 500
    docs = list(collection.find({}, {"_id": 0})
                          .sort("_id", -1)
                          .limit(50))
    humidities = [d.get("humidity", 0) for d in docs if d.get("humidity") is not None]
    latest     = docs[-1] if docs else {}

    return jsonify({
        "total":        collection.count_documents({}),
        "latest":       latest,
        "avg_humidity": round(sum(humidities) / len(humidities), 1) if humidities else 0,
        "min_humidity": min(humidities) if humidities else 0,
        "max_humidity": max(humidities) if humidities else 0,
        "alert":        latest.get("humidity", 100) < ALERT_THR if latest else False,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
