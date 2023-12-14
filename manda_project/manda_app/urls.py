from django.urls import path, include
from . import views
from django.contrib import admin
from django.conf.urls.static import static
from django.urls import path
from manda_app.views import TestView

from .manda_urls.urls_user import urlpatterns as manda_user_urls
from .manda_urls.urls_write import urlpatterns as manda_write_urls
from .manda_urls.urls_manda import urlpatterns as manda_manda_urls
from .manda_urls.urls_feed import urlpatterns as manda_feed_urls
from .manda_urls.urls_chat import urlpatterns as manda_chat_urls
from .manda_urls.urls_search import urlpatterns as manda_search_urls
from .manda_urls.urls_noti import urlpatterns as manda_noti_urls

urlpatterns = [
    path('v1/test/', TestView.as_view(), name='test'),
    path('', views.main, name='main'),
    path('user/', include(manda_user_urls)), #회원가입, 로그인, 로그아웃
    path('write/', include(manda_write_urls)), #글 작성, 글 선택
    path('manda/', include(manda_manda_urls)), #만다라트
	  path('feed/', include(manda_feed_urls)), #피드
    path('chat/', include(manda_chat_urls)), #채팅
    path('search/', include(manda_search_urls)), #검색(탐색)
    path('noti/', include(manda_noti_urls)), # 알림
    path('get_token/', views.get_csrf_token, name='get_token'), #토큰
]
