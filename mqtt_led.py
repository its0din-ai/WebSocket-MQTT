"""
Nama : Muhammad Wahyu Syafi'uddin
NIM  : L200210056
"""

import logging
import signal
import sys
import json
import paho.mqtt.client as mqtt
from time import sleep
from gpiozero import Device, PWMLED
from gpiozero.pins.pigpio import PiGPIOFactory
from paho import mqtt as tlsmqtt

# Initialize Logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("main")
logger.setLevel(logging.INFO)

# Initialize GPIO
Device.pin_factory = PiGPIOFactory()

# Global Variables
LED_GPIO_PIN = [16, 20, 21]
BROKER_HOST = "06e17a32c5744a7a82b019fd767940b3.s2.eu.hivemq.cloud"
BROKER_PORT = 8883
MQTT_USR = "luci.x666"
MQTT_PWD = "Pass1234"
CLIENT_IDS = ["LEDClient0", "LEDClient1", "LEDClient2"]
TOPICS = ["led0", "led1", "led2"]
clients = [None, None, None]
leds = [None, None, None]

def init_leds():
    """Create and initialise LED Objects"""
    global leds
    leds = [PWMLED(pin) for pin in LED_GPIO_PIN]
    for led in leds:
        led.off()

def set_led_level(led_index, data):
    """Set LED State based on data"""
    level = None

    if "level" in data:
        level = data["level"]

        if isinstance(level, (int, float)) or str(level).isdigit():
            level = max(0, min(100, int(level)))
            leds[led_index].value = level / 100
            logger.info("LED {} at brightness {}%".format(led_index, level))
        else:
            logger.info("Request for unknown LED level of '{}'. We'll turn it Off instead.".format(level))
            leds[led_index].value = 0
    else:
        logger.info("Message '{}' did not contain property 'level'.".format(data))

def on_connect(client, user_data, flags, connection_result_code):
    """Callback called when our program connects to the MQTT Broker."""
    if connection_result_code == 0:
        logger.info("Connected to MQTT Broker")
        for i, topic in enumerate(TOPICS):
            client.subscribe(topic, qos=2)
    else:
        logger.error("Failed to connect to MQTT Broker: " + mqtt.connack_string(connection_result_code))

def on_disconnect(client, user_data, disconnection_result_code):
    """Called disconnects from MQTT Broker."""
    logger.error("Disconnected from MQTT Broker")

def on_message(client, userdata, msg):
    """Callback called when a message is received on a subscribed topic."""
    logger.debug("Received message for topic {}: {}".format(msg.topic, msg.payload))

    data = None
    try:
        data = json.loads(msg.payload.decode("UTF-8"))
    except json.JSONDecodeError as e:
        logger.error("JSON Decode Error: " + msg.payload.decode("UTF-8"))

    for i, topic in enumerate(TOPICS):
        if msg.topic == topic:
            set_led_level(i, data)

def signal_handler(sig, frame):
    """Capture Control+C and disconnect from Broker."""
    logger.info("You pressed Control + C. Shutting down, please wait...")
    for client in clients:
        client.disconnect()
    for led in leds:
        led.off()
    sys.exit(0)

def init_mqtt():
    global clients
    clients = [mqtt.Client(client_id=client_id, clean_session=False) for client_id in CLIENT_IDS]

    for client in clients:
        client.enable_logger()
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_message = on_message
        client.tls_set(tls_version=tlsmqtt.client.ssl.PROTOCOL_TLS)
        client.username_pw_set(MQTT_USR, MQTT_PWD)
        client.connect(BROKER_HOST, BROKER_PORT)

init_leds()
init_mqtt()

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    logger.info("Listening for messages on topics {}. Press Control + C to exit.".format(TOPICS))

    for client in clients:
        client.loop_start()

    signal.pause()
