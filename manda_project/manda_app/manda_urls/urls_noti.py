from django.urls import path
from ..manda_views import views_noti

urlpatterns = [
    path('get/<int:user_id>', views_noti.get_notifications, name='get_notifications'),
    path('read/<int:noti_id>', views_noti.read_notification, name='read_notification'),
]