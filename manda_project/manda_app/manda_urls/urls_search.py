from django.urls import path
from ..manda_views import views_search

urlpatterns = [
    path('', views_search.search_view, name='search'),
]