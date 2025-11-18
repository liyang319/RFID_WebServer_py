# rfid_app/views.py
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json
from .models import RFIDTagData, RFIDDevice
from .mqtt_client import mqtt_client


def dashboard(request):
    """主仪表板页面"""
    # 获取最近数据用于初始显示
    recent_data = RFIDTagData.objects.all().order_by('-timestamp')[:20]
    total_tags = RFIDTagData.objects.count()
    online_devices = RFIDDevice.objects.filter(status='online').count()
    total_devices = RFIDDevice.objects.count()

    context = {
        'page_title': 'RFID实时监控仪表板',
        'recent_data': recent_data,
        'total_tags': total_tags,
        'online_devices': online_devices,
        'total_devices': total_devices,
        'mqtt_connected': mqtt_client.is_connected,
        'message_count': mqtt_client.message_count,
    }
    return render(request, 'rfid_app/dashboard.html', context)


@require_http_methods(["GET"])
def get_statistics_api(request):
    """获取统计信息API"""
    try:
        total_tags = RFIDTagData.objects.count()
        recent_count = RFIDTagData.objects.filter(
            timestamp__gte=timezone.now() - timezone.timedelta(hours=24)
        ).count()
        online_devices = RFIDDevice.objects.filter(status='online').count()
        total_devices = RFIDDevice.objects.count()

        mqtt_stats = mqtt_client.get_statistics()

        return JsonResponse({
            'success': True,
            'data': {
                'total_tags': total_tags,
                'recent_24h': recent_count,
                'online_devices': online_devices,
                'total_devices': total_devices,
                'mqtt_connected': mqtt_stats['connected'],
                'total_messages': mqtt_stats['total_messages'],
                'last_update': timezone.now().isoformat()
            }
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_http_methods(["GET"])
def get_recent_data_api(request):
    """获取最近标签数据API"""
    try:
        limit = int(request.GET.get('limit', 50))
        device_id = request.GET.get('device_id')

        query = RFIDTagData.objects.all().order_by('-timestamp')
        if device_id:
            query = query.filter(device__device_id=device_id)

        recent_data = list(query[:limit].values(
            'tag_id', 'epc', 'rssi', 'antenna', 'device__device_id', 'timestamp'
        ))

        # 转换时间格式
        for item in recent_data:
            if item['timestamp']:
                item['timestamp'] = item['timestamp'].isoformat()
            item['reader_id'] = item['device__device_id']
            del item['device__device_id']

        return JsonResponse({
            'success': True,
            'data': recent_data,
            'count': len(recent_data)
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_http_methods(["GET"])
def get_recent_messages_api(request):
    """获取最近MQTT消息API"""
    try:
        limit = int(request.GET.get('limit', 50))
        message_type = request.GET.get('type')

        messages = mqtt_client.get_recent_messages(limit, message_type)

        return JsonResponse({
            'success': True,
            'messages': messages,
            'count': len(messages),
            'timestamp': timezone.now().isoformat()
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_http_methods(["GET"])
def get_devices_api(request):
    """获取设备列表API"""
    try:
        devices = list(RFIDDevice.objects.all().order_by('-last_seen').values(
            'device_id', 'device_name', 'device_type', 'status',
            'ip_address', 'last_seen', 'location', 'description'
        ))

        # 转换时间格式
        for device in devices:
            if device['last_seen']:
                device['last_seen'] = device['last_seen'].isoformat()

        return JsonResponse({
            'success': True,
            'devices': devices,
            'count': len(devices)
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@csrf_exempt
@require_http_methods(["POST"])
def send_command_api(request):
    """发送命令API"""
    try:
        data = json.loads(request.body)
        device_id = data.get('device_id')
        command = data.get('command')
        parameters = data.get('parameters', {})

        if not device_id or not command:
            return JsonResponse({
                'success': False,
                'error': '设备ID和命令不能为空'
            })

        # 发送命令
        success = mqtt_client.send_command(device_id, command, parameters)

        return JsonResponse({
            'success': success,
            'message': f'命令发送成功: {command} -> {device_id}' if success else '命令发送失败',
            'command_id': f"cmd_{int(timezone.now().timestamp() * 1000)}",
            'timestamp': timezone.now().isoformat()
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_http_methods(["GET"])
def get_connection_status_api(request):
    """获取连接状态API"""
    try:
        return JsonResponse({
            'success': True,
            'connected': mqtt_client.is_connected,
            'message_count': mqtt_client.message_count,
            'timestamp': timezone.now().isoformat()
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })