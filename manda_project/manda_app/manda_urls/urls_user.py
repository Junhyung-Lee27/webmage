from django.urls import path
from django.contrib.auth import views as auth_views
from ..manda_views import views_users

urlpatterns = [
    path('login/', views_users.user_login, name='login'), 
    path('logout/', views_users.user_logout, name='logout'), 
    path('signup/', views_users.sign_up, name='signup'), 
    path('edit/', views_users.user_edit, name='edit'),
    path('reset-password/', views_users.reset_password, name='reset_password'),
    path('delete-user/', views_users.delete_user, name='delete_user'),

    path('profile/write', views_users.write_profile, name='write_profile'),
    path('profile/edit', views_users.edit_profile, name='edit_profile'),
    path('profile/<int:user_id>', views_users.view_profile, name='view_profile'),
]