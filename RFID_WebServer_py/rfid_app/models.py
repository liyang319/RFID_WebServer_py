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
    location = models.CharField(max_length=200, blank=True, null=True, verbose_name="安装位置")
    description = models.TextField(blank=True, null=True, verbose_name="设备描述")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")

    class Meta:
        verbose_name = 'RFID设备'
        verbose_name_plural = 'RFID设备'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.device_name} ({self.device_id})"

    def save(self, *args, **kwargs):
        if self.status == 'online':
            self.last_seen = timezone.now()
        super().save(*args, **kwargs)

    @property
    def is_online(self):
        if self.last_seen:
            time_diff = timezone.now() - self.last_seen
            return time_diff.total_seconds() < 300
        return False


class RFIDTagData(models.Model):
    tag_id = models.CharField(max_length=100, verbose_name="标签ID")
    epc = models.CharField(max_length=200, blank=True, verbose_name="EPC码")
    device = models.ForeignKey(RFIDDevice, on_delete=models.CASCADE, verbose_name="读取设备")
    rssi = models.FloatField(null=True, blank=True, verbose_name="信号强度")
    antenna = models.IntegerField(default=1, verbose_name="天线编号")
    timestamp = models.DateTimeField(default=timezone.now, verbose_name="读取时间")
    product_name = models.CharField(max_length=100, blank=True, verbose_name="产品名称")
    data_type = models.CharField(max_length=20, default='single', verbose_name="数据类型")
    raw_data = models.JSONField(null=True, blank=True, verbose_name="原始数据")

    class Meta:
        verbose_name = 'RFID标签数据'
        verbose_name_plural = 'RFID标签数据'
        ordering = ['-timestamp']

    def __str__(self):
        return f"标签 {self.tag_id} - 产品: {self.product_name}"