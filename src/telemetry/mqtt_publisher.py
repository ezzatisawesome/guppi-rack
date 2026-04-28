"""MQTT publisher for real-time telemetry streaming."""

import logging
import threading
import time
from typing import Optional

import paho.mqtt.client as mqtt

from server.mqtt_config import MqttConfig

logger = logging.getLogger(__name__)


class MqttPublisher:
    """Publishes telemetry measurements to an MQTT broker.
    
    Features:
    - Automatic reconnection on disconnect
    - Last Will & Testament for rack liveness detection
    - Retained messages for instant value on new subscriptions
    - Thread-safe publishing
    """

    def __init__(self, config: MqttConfig, rig_id: str):
        self.config = config
        self.rig_id = rig_id
        self._client: Optional[mqtt.Client] = None
        self._connected = False
        self._lock = threading.Lock()

    def _topic(self, *parts: str) -> str:
        """Build an MQTT topic with an optional configured base prefix."""
        prefix = self.config.base_topic.strip("/")
        body = "/".join(part.strip("/") for part in parts if part)
        return f"{prefix}/{body}" if prefix else body

    def connect(self) -> bool:
        """Connect to the MQTT broker with LWT."""
        client_id = f"{self.config.client_id_prefix}-{self.rig_id}-{int(time.time())}"
        self._client = mqtt.Client(
            client_id=client_id,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )
        
        # Authentication
        self._client.username_pw_set(self.config.username, self.config.password)
        
        # Last Will & Testament — published automatically if we disconnect unexpectedly
        status_topic = self._topic("status", self.rig_id, "online")
        self._client.will_set(status_topic, payload="false", qos=1, retain=True)
        
        # Callbacks
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        
        try:
            logger.info(f"Connecting to MQTT broker at {self.config.broker_host}:{self.config.broker_port}")
            self._client.connect(self.config.broker_host, self.config.broker_port, keepalive=60)
            self._client.loop_start()  # Start background network loop
            logger.info("MQTT publisher initialized; awaiting broker connection")
            return True
        except Exception as e:
            self._client = None
            self._connected = False
            logger.warning(f"MQTT broker not available — live telemetry disabled: {e}")
            return False

    def disconnect(self):
        """Gracefully disconnect, publishing offline status."""
        if self._client:
            try:
                status_topic = self._topic("status", self.rig_id, "online")
                self._client.publish(status_topic, payload="false", qos=1, retain=True)
                self._client.loop_stop()
                self._client.disconnect()
                logger.info("MQTT disconnected gracefully")
            except Exception as e:
                logger.warning(f"Error during MQTT disconnect: {e}")

    def publish_measurement(
        self,
        instrument_id: str,
        metric: str,
        value: float,
    ):
        """Publish a single measurement to the appropriate MQTT topic.

        Topic: {rig_id}/{instrument_id}/{metric}
        Payload: raw scalar value (e.g., "12.45")
        """
        with self._lock:
            if not self._client or not self._connected:
                logger.debug(f"MQTT not connected, skipping telemetry for {instrument_id}/{metric}")
                return

            topic = self._topic(self.rig_id, instrument_id, metric)
            payload = str(round(value, 4))

            try:
                self._client.publish(topic, payload=payload, qos=0, retain=True)
                logger.debug(f"Published telemetry: {topic} = {payload}")
            except Exception as e:
                logger.error(f"MQTT publish failed for {topic}: {e}")

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            self._connected = True
            logger.info("MQTT broker connected")
            # Publish online status on connect (retained)
            status_topic = self._topic("status", self.rig_id, "online")
            client.publish(status_topic, payload="true", qos=1, retain=True)
        else:
            self._connected = False
            logger.error(f"MQTT connect failed with code {rc}")

    def _on_disconnect(self, client, userdata, flags, rc, properties=None):
        self._connected = False
        if rc != 0:
            logger.warning(f"MQTT unexpected disconnect (rc={rc}). Will auto-reconnect.")
