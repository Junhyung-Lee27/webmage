from django.urls import path
from ..manda_views import views_mandas

urlpatterns = [
    path('create/', views_mandas.manda_main_create, name='create'), 
    path('edit/main/', views_mandas.update_manda_main, name='edit_main'),
    path('edit/sub/', views_mandas.update_manda_subs, name='edit_sub'),
    path('edit/content/', views_mandas.update_manda_contents, name='edit_content'),
    path('delete/<int:manda_id>', views_mandas.manda_main_delete, name='delete_manda'),
    path('mandamain/<int:manda_id>', views_mandas.select_mandalart, name='mandamain'),
    path('<int:user_id>/', views_mandas.manda_main_list, name='usermanda'),
    path('others/', views_mandas.others_manda_main_list, name='others'),
    path('search/mandasimple/', views_mandas.search_sub_mandas, name='search_mandasimple'),
    path('recommend/mandasimple/', views_mandas.recommend_mandas, name='recommend_mandasimple')
]