"""
mqtt_consumer.py
Partie 2 — Backend IoT Irrigation
- Connexion HiveMQ Cloud (TLS/8883)
- Souscription topic : irrigation/soil
- Parse : "Humidite du sol: 54% | Date: 2000-01-01 00:06:43"
- Stockage MongoDB : { "humidity": 54, "timestamp": "2000-01-01 00:06:43" }
"""

import re
import ssl
import logging
from datetime import datetime

import paho.mqtt.client as mqtt
from pymongo import MongoClient

# ─── Configuration MQTT ────────────────────────────────────────────────────────
MQTT_SERVER = "1ce520eab52a4627914aef266aff8647.s1.eu.hivemq.cloud"
MQTT_PORT   = 8883
MQTT_USER   = "emsi1234"
MQTT_PASS   = "Emsi1234"
MQTT_TOPIC  = "irrigation/soil"

# ─── Configuration MongoDB ─────────────────────────────────────────────────────
MONGO_URI  = "mongodb+srv://badre:123@cluster0.efcymvu.mongodb.net/?appName=Cluster0"
DB_NAME    = "irrigation_db"
COLL_NAME  = "soil_data"
ALERT_THR  = 30

# ─── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ─── MongoDB setup ─────────────────────────────────────────────────────────────
try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_client.server_info()
    db         = mongo_client[DB_NAME]
    collection = db[COLL_NAME]
    log.info("MongoDB connecte !")
except Exception as e:
    log.error("Erreur MongoDB : %s", e)
    exit(1)


# ─── Parse message texte ───────────────────────────────────────────────────────
def parse_message(payload: str) -> dict | None:
    """
    Parse le format : "Humidite du sol: 54% | Date: 2000-01-01 00:06:43"
    Retourne : { "humidity": 54, "timestamp": "2000-01-01 00:06:43" }
    """
    pattern = r"Humidite du sol:\s*(\d+)%\s*\|\s*Date:\s*(.+)"
    match = re.search(pattern, payload, re.IGNORECASE)
    if not match:
        log.warning("Format invalide : %s", payload)
        return None

    humidity  = int(match.group(1))
    timestamp = match.group(2).strip()

    # Validation date
    try:
        datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        log.warning("Date invalide : %s", timestamp)
        return None

    return {
        "humidity":  humidity,
        "timestamp": timestamp
    }


# ─── Sauvegarde MongoDB ────────────────────────────────────────────────────────
def save_to_mongo(document: dict) -> None:
    result = collection.insert_one(document)
    log.info(
        "Stocke -> humidity=%d%% | timestamp=%s | _id=%s",
        document["humidity"],
        document["timestamp"],
        result.inserted_id,
    )


# ─── Callbacks MQTT ────────────────────────────────────────────────────────────
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        log.info("Connecte au broker MQTT : %s", MQTT_SERVER)
        client.subscribe(MQTT_TOPIC, qos=1)
        log.info("Souscription au topic : %s", MQTT_TOPIC)
    else:
        log.error("Echec de connexion MQTT, code : %s", reason_code)


def on_message(client, userdata, msg):
    payload = msg.payload.decode("utf-8").strip()
    log.info("Message recu [%s] : %s", msg.topic, payload)

    document = parse_message(payload)
    if document:
        if document["humidity"] < ALERT_THR:
            log.warning("ALERTE - Humidite faible : %d%%", document["humidity"])
        save_to_mongo(document)


def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
    log.warning("Deconnecte (code %s). Reconnexion...", reason_code)


# ─── Main ──────────────────────────────────────────────────────────────────────
def main():
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="irrigation_consumer",
        clean_session=True,
    )
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.tls_set(
        ca_certs=None, certfile=None, keyfile=None,
        cert_reqs=ssl.CERT_REQUIRED,
        tls_version=ssl.PROTOCOL_TLS_CLIENT,
    )
    client.on_connect    = on_connect
    client.on_message    = on_message
    client.on_disconnect = on_disconnect

    log.info("Connexion a %s:%d ...", MQTT_SERVER, MQTT_PORT)
    client.connect(MQTT_SERVER, MQTT_PORT, keepalive=60)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        log.info("Arret du consumer.")
    finally:
        client.disconnect()
        mongo_client.close()


if __name__ == "__main__":
    main()
