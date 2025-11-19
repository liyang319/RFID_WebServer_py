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

    # API路由
    path('api/statistics/', views.get_statistics_api, name='api_statistics'),
    path('api/recent-data/', views.get_recent_data_api, name='api_recent_data'),
    path('api/recent-messages/', views.get_recent_messages_api, name='api_recent_messages'),
    path('api/devices/', views.get_devices_api, name='api_devices'),
    path('api/product-stats/', views.get_product_stats_api, name='api_product_stats'),
    path('api/send-command/', views.send_command_api, name='api_send_command'),
    path('api/connection-status/', views.get_connection_status_api, name='api_connection_status'),
]