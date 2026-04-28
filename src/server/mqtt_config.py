"""MQTT broker connection configuration."""

import os
import logging
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class MqttConfig:
    """MQTT connection settings."""
    broker_host: str
    broker_port: int
    ws_port: int
    username: str
    password: str
    client_id_prefix: str
    base_topic: str

    @classmethod
    def from_env(cls, client_id_prefix: str = "rack") -> "MqttConfig":
        """Load MQTT config from environment variables."""
        return cls(
            broker_host=os.getenv("MQTT_BROKER_HOST", "localhost"),
            broker_port=int(os.getenv("MQTT_BROKER_PORT", "1883")),
            ws_port=int(os.getenv("MQTT_WS_PORT", "9001")),
            username=os.getenv("MQTT_USERNAME", "rack"),
            password=os.getenv("MQTT_PASSWORD", ""),
            client_id_prefix=client_id_prefix,
            base_topic=os.getenv("MQTT_BASE_TOPIC", ""),
        )
