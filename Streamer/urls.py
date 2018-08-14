from django.urls import path

from . import views
app_name = 'Streamer'
urlpatterns = [
    path('', views.index, name = 'index'),
    path('get_camera',views.get_camera, name = 'get_camera'),
    path('<int:camera_id>/', views.camera_stream, name = 'camera_stream'),
    path('<int:camera_id>/live/', views.live_feed, name = 'live'),
    path('<int:camera_id>/start_stream',views.start_stream, name = 'start_stream'),
    path('<int:camera_id>/stop_stream', views.stop_stream, name = 'stop_stream'),
    path('<int:camera_id>/upload_stream', views.upload_stream, name = 'upload_stream')
]
