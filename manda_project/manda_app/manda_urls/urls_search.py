from django.urls import path
from ..manda_views import views_search

urlpatterns = [
    path('', views_search.search_view, name='search'),
    path('mandasimple/', views_search.search_manda_simples, name='search_manda_simples'),
    path('feeds/', views_search.search_feeds, name='search_feeds'),
    path('users/', views_search.search_users, name='search_users'),
]