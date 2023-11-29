from django.urls import path, include
from django.contrib.auth import views as auth_views
from ..manda_views import views_users

urlpatterns = [
    path('login/', views_users.user_login, name='login'),
    path('logout/', views_users.user_logout, name='logout'), 
    path('signup/', views_users.sign_up, name='signup'), 
    path('edit/', views_users.user_edit, name='edit'),
    path('reset-password/', views_users.reset_password, name='reset_password'),
    path('delete-user/', views_users.delete_user, name='delete_user'),
    path('profile/edit', views_users.edit_profile, name='edit_profile'),
    path('profile/<int:user_id>', views_users.view_profile, name='view_profile'),
    
    path('follow/', views_users.follow_user, name='follow'),
    path('unfollow/', views_users.unfollow_user, name='unfollow'),

    path('block/', views_users.block_user, name='block'),
    path('unblock/', views_users.unblock_user, name='unblock'),
    path('blocked_users/', views_users.blocked_users, name="blocked_users")
]