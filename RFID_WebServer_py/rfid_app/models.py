# rfid_app/models.py
from django.db import models
from django.utils import timezone


class RFIDDevice(models.Model):
    DEVICE_TYPES = [
        ('reader', 'RFID阅读器'),
        ('sensor', '传感器'),
        ('gate', '门禁'),
    ]

    DEVICE_STATUS = [
        ('online', '在线'),
        ('offline', '离线'),
        ('error', '错误'),
    ]

    device_id = models.CharField(max_length=50, unique=True, verbose_name="设备ID")
    device_name = models.CharField(max_length=100, verbose_name="设备名称")
    device_type = models.CharField(max_length=10, choices=DEVICE_TYPES, default='reader', verbose_name="设备类型")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP地址")
    status = models.CharField(max_length=10, choices=DEVICE_STATUS, default='offline', verbose_name="状态")
    last_seen = models.DateTimeField(null=True, blank=True, verbose_name="最后在线时间")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")

    class Meta:
        verbose_name = 'RFID设备'
        verbose_name_plural = 'RFID设备'

    def __str__(self):
        return f"{self.device_name} ({self.device_id})"


class RFIDTagData(models.Model):
    tag_id = models.CharField(max_length=100, verbose_name="标签ID")
    epc = models.CharField(max_length=200, blank=True, verbose_name="EPC码")
    device = models.ForeignKey(RFIDDevice, on_delete=models.CASCADE, verbose_name="读取设备")
    rssi = models.FloatField(null=True, blank=True, verbose_name="信号强度")
    antenna = models.IntegerField(default=1, verbose_name="天线编号")
    timestamp = models.DateTimeField(default=timezone.now, verbose_name="读取时间")
    raw_data = models.JSONField(null=True, blank=True, verbose_name="原始数据")

    class Meta:
        verbose_name = 'RFID标签数据'
        verbose_name_plural = 'RFID标签数据'
        ordering = ['-timestamp']

    def __str__(self):
        return f"标签 {self.tag_id} - 设备 {self.device.device_id}"
