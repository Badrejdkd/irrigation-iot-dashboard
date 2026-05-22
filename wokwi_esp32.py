# ─── Imports ────────────────────────────────────────────
import network, time, ujson, random
from machine import Pin
import dht
from umqtt.simple import MQTTClient

# ─── Configuration — meme broker que le consumer ────────
DHTPIN    = 4
SSID      = "Wokwi-GUEST"
WIFI_PASS = ""
MQTT_HOST = "1ce520eab52a4627914aef266aff8647.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USER = "emsi1234"
MQTT_PASS = "Emsi1234"
TOPIC     = "irrigation/soil"
DEVICE_ID = "esp32_wokwi_01"
INTERVAL  = 5

dht_sensor = dht.DHT22(Pin(DHTPIN))
client = None

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(SSID, WIFI_PASS)
        for _ in range(30):
            if wlan.isconnected(): break
            time.sleep(0.5)
    print("WiFi OK: " + wlan.ifconfig()[0])

def connect_mqtt():
    global client
    for attempt in range(5):
        try:
            client = MQTTClient(DEVICE_ID, MQTT_HOST,
                                port=MQTT_PORT, user=MQTT_USER,
                                password=MQTT_PASS, ssl=True,
                                ssl_params={"server_hostname": MQTT_HOST},
                                keepalive=60)
            client.connect()
            print("MQTT connecte !")
            return
        except OSError as e:
            wait = 0.5 * (2 ** attempt)
            print("MQTT erreur: {} - retry dans {}s".format(e, wait))
            time.sleep(wait)
    client = None

def read_sensor():
    try:
        dht_sensor.measure()
        return dht_sensor.temperature(), dht_sensor.humidity()
    except:
        return None, None

def publish_safe(payload):
    global client
    if client is None: connect_mqtt()
    if client is None: return
    try:
        client.publish(TOPIC, payload, qos=1)
    except OSError as e:
        print("Publish error: " + str(e))
        try: client.disconnect()
        except: pass
        client = None
        time.sleep(3)

def get_timestamp():
    t = time.localtime()
    return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
        t[0], t[1], t[2], t[3], t[4], t[5]
    )

def main():
    connect_wifi()
    connect_mqtt()
    count = 0
    while True:
        temp, hum = read_sensor()
        if temp is not None:
            count += 1
            humidity = int(round(hum))
            ts = get_timestamp()
            # Format exact demande par l'exercice :
            # "Humidite du sol: 54% | Date: 2000-01-01 00:06:43"
            payload = "Humidite du sol: {}% | Date: {}".format(humidity, ts)
            publish_safe(payload)
            print("[#{}] {}".format(count, payload))
        time.sleep(INTERVAL)

main()
