# rfid_app/views.py
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Count, Max, Avg
from django.db import models
import json
from .models import RFIDTagData, RFIDDevice
from .mqtt_client import mqtt_client


def management(request):
    """管理页面视图"""
    context = {
        'page_title': '火工品工厂管控服务平台',
        # 可以添加其他上下文数据
    }
    return render(request, 'rfid_app/management.html', context)


def dashboard(request):
    """主仪表板页面"""
    try:
        # 获取最近数据用于初始显示
        recent_data = RFIDTagData.objects.all().order_by('-timestamp')[:20]
        total_tags = RFIDTagData.objects.count()
        online_devices = RFIDDevice.objects.filter(status='online').count()
        total_devices = RFIDDevice.objects.count()

        # 获取产品统计
        product_stats = RFIDTagData.objects.values('product_name').annotate(
            count=Count('id')
        ).order_by('-count')[:10]

        context = {
            'page_title': 'RFID实时监控仪表板',
            'recent_data': recent_data,
            'total_tags': total_tags,
            'online_devices': online_devices,
            'total_devices': total_devices,
            'product_stats': product_stats,
            'mqtt_connected': mqtt_client.is_connected,
            'message_count': mqtt_client.message_count,
        }
        return render(request, 'rfid_app/dashboard.html', context)

    except Exception as e:
        return render(request, 'rfid_app/error.html', {
            'error_message': f'页面加载失败: {str(e)}'
        })


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

        # 获取产品统计
        product_stats = RFIDTagData.objects.values('product_name').annotate(
            count=Count('id')
        ).count()

        mqtt_stats = mqtt_client.get_statistics()

        return JsonResponse({
            'success': True,
            'data': {
                'total_tags': total_tags,
                'recent_24h': recent_count,
                'online_devices': online_devices,
                'total_devices': total_devices,
                'total_products': product_stats,
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
        product_name = request.GET.get('product_name')
        data_type = request.GET.get('data_type')

        query = RFIDTagData.objects.all().order_by('-timestamp')
        if device_id:
            query = query.filter(device__device_id=device_id)
        if product_name:
            query = query.filter(product_name=product_name)
        if data_type:
            query = query.filter(data_type=data_type)

        recent_data = list(query[:limit].values(
            'tag_id', 'epc', 'rssi', 'antenna', 'product_name', 'data_type',
            'device__device_id', 'timestamp'
        ))

        # 转换时间格式
        for item in recent_data:
            if item['timestamp']:
                item['timestamp'] = item['timestamp'].isoformat()
            item['device_id'] = item['device__device_id']
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


@require_http_methods(["GET"])
def get_product_stats_api(request):
    """获取产品统计API"""
    try:
        # 获取产品统计详情
        product_stats = list(RFIDTagData.objects.values('product_name').annotate(
            count=Count('id'),
            last_seen=Max('timestamp'),
            avg_rssi=Avg('rssi'),
            total_devices=Count('device__device_id', distinct=True)
        ).order_by('-count'))

        # 转换时间格式
        for stat in product_stats:
            if stat['last_seen']:
                stat['last_seen'] = stat['last_seen'].isoformat()
            if not stat['product_name']:
                stat['product_name'] = '未知产品'

        return JsonResponse({
            'success': True,
            'product_stats': product_stats,
            'total_products': len(product_stats)
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_http_methods(["GET"])
def get_product_detail_api(request):
    """获取产品详情API"""
    try:
        product_name = request.GET.get('product_name')
        if not product_name:
            return JsonResponse({
                'success': False,
                'error': '产品名称不能为空'
            })

        # 获取产品相关的标签数据
        tags = list(RFIDTagData.objects.filter(product_name=product_name)
                    .order_by('-timestamp')[:100]
                    .values(
            'tag_id', 'epc', 'rssi', 'antenna', 'data_type',
            'device__device_id', 'timestamp'
        ))

        # 获取产品统计
        stats = RFIDTagData.objects.filter(product_name=product_name).aggregate(
            total_tags=Count('id'),
            unique_tags=Count('tag_id', distinct=True),
            avg_rssi=Avg('rssi'),
            last_seen=Max('timestamp'),
            total_devices=Count('device__device_id', distinct=True)
        )

        # 转换时间格式
        for tag in tags:
            if tag['timestamp']:
                tag['timestamp'] = tag['timestamp'].isoformat()
            tag['device_id'] = tag['device__device_id']
            del tag['device__device_id']

        if stats['last_seen']:
            stats['last_seen'] = stats['last_seen'].isoformat()

        return JsonResponse({
            'success': True,
            'product_name': product_name,
            'stats': stats,
            'recent_tags': tags,
            'count': len(tags)
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@require_http_methods(["GET"])
def get_device_detail_api(request):
    """获取设备详情API"""
    try:
        device_id = request.GET.get('device_id')
        if not device_id:
            return JsonResponse({
                'success': False,
                'error': '设备ID不能为空'
            })

        # 获取设备信息
        try:
            device = RFIDDevice.objects.get(device_id=device_id)
            device_data = {
                'device_id': device.device_id,
                'device_name': device.device_name,
                'device_type': device.device_type,
                'status': device.status,
                'ip_address': device.ip_address,
                'last_seen': device.last_seen.isoformat() if device.last_seen else None,
                'location': device.location,
                'description': device.description
            }
        except RFIDDevice.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'设备不存在: {device_id}'
            })

        # 获取设备相关的标签统计
        tag_stats = RFIDTagData.objects.filter(device=device).aggregate(
            total_tags=Count('id'),
            recent_24h=Count('id', filter=models.Q(
                timestamp__gte=timezone.now() - timezone.timedelta(hours=24)
            )),
            avg_rssi=Avg('rssi'),
            last_read=Max('timestamp')
        )

        # 获取设备最近读取的标签
        recent_tags = list(RFIDTagData.objects.filter(device=device)
                           .order_by('-timestamp')[:20]
                           .values('tag_id', 'epc', 'rssi', 'antenna', 'product_name', 'timestamp'))

        # 转换时间格式
        for tag in recent_tags:
            if tag['timestamp']:
                tag['timestamp'] = tag['timestamp'].isoformat()

        if tag_stats['last_read']:
            tag_stats['last_read'] = tag_stats['last_read'].isoformat()

        return JsonResponse({
            'success': True,
            'device': device_data,
            'stats': tag_stats,
            'recent_tags': recent_tags
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


@require_http_methods(["GET"])
def export_data_api(request):
    """导出数据API"""
    try:
        import csv
        from django.http import HttpResponse

        format_type = request.GET.get('format', 'csv')
        data_type = request.GET.get('data_type', 'tags')

        if format_type == 'csv':
            response = HttpResponse(content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = 'attachment; filename="rfid_data.csv"'

            writer = csv.writer(response)

            if data_type == 'tags':
                # 导出标签数据
                writer.writerow(['标签ID', 'EPC码', '产品名称', '信号强度', '天线', '设备ID', '读取时间'])

                tags = RFIDTagData.objects.all().order_by('-timestamp')[:1000]
                for tag in tags:
                    writer.writerow([
                        tag.tag_id,
                        tag.epc,
                        tag.product_name or '未知',
                        tag.rssi or 0,
                        tag.antenna,
                        tag.device.device_id,
                        tag.timestamp.strftime('%Y-%m-%d %H:%M:%S') if tag.timestamp else ''
                    ])
            else:
                # 导出设备数据
                writer.writerow(['设备ID', '设备名称', '状态', 'IP地址', '最后在线', '位置'])

                devices = RFIDDevice.objects.all()
                for device in devices:
                    writer.writerow([
                        device.device_id,
                        device.device_name,
                        device.status,
                        device.ip_address or '',
                        device.last_seen.strftime('%Y-%m-%d %H:%M:%S') if device.last_seen else '',
                        device.location or ''
                    ])

            return response

        else:
            return JsonResponse({
                'success': False,
                'error': '不支持的导出格式'
            })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


# rfid_app/views.py
@csrf_exempt
@require_http_methods(["POST"])
def clear_database_api(request):
    """清空数据库API"""
    try:
        data_type = request.GET.get('type', 'tags')  # tags, all
        print(f'data_type={data_type}')
        if data_type == 'all':
            # 清空所有数据
            tag_count = RFIDTagData.objects.count()
            device_count = RFIDDevice.objects.count()
            RFIDTagData.objects.all().delete()
            RFIDDevice.objects.all().delete()
            message = f'已清空所有数据：{tag_count}条标签，{device_count}台设备'
        elif data_type == 'tags':
            # 只清空标签数据
            count = RFIDTagData.objects.count()
            RFIDTagData.objects.all().delete()
            message = f'已清空 {count} 条标签数据'
        else:
            return JsonResponse({
                'success': False,
                'error': '无效的数据类型'
            })

        return JsonResponse({
            'success': True,
            'message': message,
            'cleared_count': count if data_type == 'tags' else tag_count,
            'data_type': data_type,
            'timestamp': timezone.now().isoformat()
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })