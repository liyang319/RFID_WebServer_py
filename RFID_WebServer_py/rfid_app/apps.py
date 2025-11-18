# rfid_app/apps.py
from django.apps import AppConfig
import logging
import os

logger = logging.getLogger(__name__)


class RfidAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rfid_app'

    def ready(self):
        """Django启动时自动执行"""
        if os.environ.get('RUN_MAIN'):
            self.start_mqtt_client()

    def start_mqtt_client(self):
        """启动MQTT客户端"""
        from .mqtt_client import mqtt_client

        try:
            if mqtt_client.connect():
                logger.info("✅ RFID MQTT客户端启动成功")
            else:
                logger.error("❌ RFID MQTT客户端启动失败")

        except Exception as e:
            logger.error(f"❌ 启动MQTT客户端时发生错误: {e}")