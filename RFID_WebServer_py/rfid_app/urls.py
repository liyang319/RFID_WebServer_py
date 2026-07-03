# rfid_webserver/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('rfid_app.urls')),  # 确保包含rfid_app的URL
]

# rfid_app/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # 页面路由
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('management/', views.management, name='management'),

    # 监控页面路由
    path('monitor/', views.monitor, name='monitor'),

    # API路由
    path('api/statistics/', views.get_statistics_api, name='api_statistics'),
    path('api/recent-data/', views.get_recent_data_api, name='api_recent_data'),
    path('api/recent-messages/', views.get_recent_messages_api, name='api_recent_messages'),
    path('api/devices/', views.get_devices_api, name='api_devices'),
    path('api/product-stats/', views.get_product_stats_api, name='api_product_stats'),
    path('api/send-command/', views.send_command_api, name='api_send_command'),
    path('api/connection-status/', views.get_connection_status_api, name='api_connection_status'),
    path('api/clear-database/', views.clear_database_api, name='api_clear_database'),

    # 监控API路由
    path('api/report-rfid/', views.report_rfid_api, name='api_report_rfid'),
    path('api/monitor-data/', views.get_monitor_data_api, name='api_monitor_data'),
]