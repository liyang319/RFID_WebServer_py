# rfid_app/device_manager.py
import threading
import time
import logging
from django.utils import timezone
from django.db import transaction
from .models import RFIDDevice

logger = logging.getLogger(__name__)


class DeviceManager:
    _instance = None

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return

        self.device_timeout = 300  # 5分钟超时
        self.heartbeat_interval = 60  # 每分钟检查一次
        self.status_checker = None
        self.is_running = False
        self.active_devices = {}  # 内存中活跃设备记录

        self._initialized = True
        logger.info("🔧 设备管理器初始化完成")

    def start(self):
        """启动设备管理器"""
        if self.is_running:
            logger.warning("⚠️ 设备管理器已在运行中")
            return

        if self.status_checker and self.status_checker.is_alive():
            return

        self.is_running = True
        self.status_checker = threading.Thread(target=self._status_check_loop, daemon=True)
        self.status_checker.start()
        logger.info("🔍 设备管理器已启动")

    def stop(self):
        """停止设备管理器"""
        self.is_running = False
        if self.status_checker:
            self.status_checker.join(timeout=5)
        logger.info("🛑 设备管理器已停止")

    def _status_check_loop(self):
        """设备状态检查循环"""
        logger.info("🔄 设备状态检查循环开始")

        while self.is_running:
            try:
                self._check_device_timeouts()
                self._cleanup_old_records()
                time.sleep(self.heartbeat_interval)
            except Exception as e:
                logger.error(f"❌ 设备状态检查错误: {e}")
                time.sleep(10)  # 出错后等待10秒

    def _check_device_timeouts(self):
        """检查设备超时"""
        try:
            with transaction.atomic():
                now = timezone.now()
                devices = RFIDDevice.objects.all()
                offline_count = 0
                online_count = 0

                for device in devices:
                    if device.last_seen:
                        time_diff = (now - device.last_seen).total_seconds()

                        if time_diff > self.device_timeout:
                            if device.status != 'offline':
                                device.status = 'offline'
                                device.save()
                                offline_count += 1
                                logger.info(f"🔌 设备 {device.device_id} 超时离线 ({time_diff:.0f}秒)")
                        else:
                            if device.status != 'online':
                                device.status = 'online'
                                device.save()
                                online_count += 1

                            # 更新内存记录
                            self.active_devices[device.device_id] = {
                                'last_seen': device.last_seen,
                                'status': device.status,
                                'device_name': device.device_name
                            }

                if offline_count > 0 or online_count > 0:
                    logger.info(f"📊 状态检查: {online_count}在线, {offline_count}离线")

        except Exception as e:
            logger.error(f"❌ 检查设备超时错误: {e}")

    def _cleanup_old_records(self):
        """清理旧的内存记录"""
        try:
            now = timezone.now()
            timeout_devices = []

            for device_id, info in self.active_devices.items():
                time_diff = (now - info['last_seen']).total_seconds()
                if time_diff > self.device_timeout * 2:  # 两倍超时时间
                    timeout_devices.append(device_id)

            for device_id in timeout_devices:
                del self.active_devices[device_id]

            if timeout_devices:
                logger.debug(f"🧹 清理了 {len(timeout_devices)} 个旧设备记录")

        except Exception as e:
            logger.error(f"❌ 清理设备记录错误: {e}")

    def update_device_status(self, device_id, status, data=None):
        """更新设备状态"""
        try:
            device, created = RFIDDevice.objects.get_or_create(
                device_id=device_id,
                defaults={
                    'device_name': data.get('device_name', f"设备-{device_id}") if data else f"设备-{device_id}",
                    'device_type': 'reader',
                    'status': status,
                    'last_seen': timezone.now()
                }
            )

            if not created:
                device.status = status
                device.last_seen = timezone.now()

                # 更新额外信息
                if data:
                    if 'device_name' in data:
                        device.device_name = data['device_name']
                    if 'ip_address' in data:
                        device.ip_address = data['ip_address']
                    if 'location' in data:
                        device.location = data['location']
                    if 'firmware_version' in data:
                        device.firmware_version = data['firmware_version']

                device.save()

            # 更新内存记录
            self.active_devices[device_id] = {
                'last_seen': device.last_seen,
                'status': device.status,
                'device_name': device.device_name
            }

            logger.debug(f"📊 设备状态更新: {device_id} - {status}")

        except Exception as e:
            logger.error(f"❌ 更新设备状态错误: {e}")

    def get_online_devices(self):
        """获取在线设备列表"""
        try:
            online_devices = []
            now = timezone.now()

            for device_id, info in self.active_devices.items():
                time_diff = (now - info['last_seen']).total_seconds()
                if time_diff <= self.device_timeout and info['status'] == 'online':
                    online_devices.append({
                        'device_id': device_id,
                        'device_name': info['device_name'],
                        'last_seen': info['last_seen'].isoformat(),
                        'time_diff': time_diff
                    })

            return online_devices

        except Exception as e:
            logger.error(f"❌ 获取在线设备错误: {e}")
            return []

    def get_device_stats(self):
        """获取设备统计信息"""
        try:
            total = RFIDDevice.objects.count()
            online = RFIDDevice.objects.filter(status='online').count()
            offline = RFIDDevice.objects.filter(status='offline').count()
            error = RFIDDevice.objects.filter(status='error').count()

            return {
                'total': total,
                'online': online,
                'offline': offline,
                'error': error,
                'last_update': timezone.now().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ 获取设备统计错误: {e}")
            return {'total': 0, 'online': 0, 'offline': 0, 'error': 0}

    def get_all_devices(self):
        """获取所有设备信息"""
        try:
            devices = list(RFIDDevice.objects.all().order_by('-last_seen').values(
                'device_id', 'device_name', 'device_type', 'status',
                'ip_address', 'last_seen', 'location', 'firmware_version'
            ))

            # 转换时间格式
            for device in devices:
                if device['last_seen']:
                    device['last_seen'] = device['last_seen'].isoformat()

            return devices

        except Exception as e:
            logger.error(f"❌ 获取所有设备错误: {e}")
            return []


# 全局实例
device_manager = DeviceManager()