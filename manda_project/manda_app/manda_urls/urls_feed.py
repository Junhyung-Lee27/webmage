from django.urls import path
from ..manda_views import views_feed

urlpatterns = [
    # Feed related URLs
    path('<int:user_id>/', views_feed.return_feed, name='user_feed'),
    path('recommend/', views_feed.recommend_feeds, name='recommend_feed'),
    path('<int:user_id>/log/', views_feed.return_feed_log, name='user_feed_log'),
    path('write/', views_feed.write_feed, name='write_feed'),
    path('edit/<int:feed_id>/', views_feed.edit_feed, name='edit_feed'),
    path('delete/<int:feed_id>/', views_feed.delete_feed, name='delete_feed'),
    
    # 댓글
    path('<int:feed_id>/comment/', views_feed.get_comments, name="get_comments"),
    path('<int:feed_id>/comment/add/', views_feed.add_comment, name='add_comment'),
    path('<int:feed_id>/comment/<int:comment_id>/edit/', views_feed.edit_comment, name='edit_comment'),
    path('<int:feed_id>/comment/<int:comment_id>/remove/', views_feed.delete_comment, name='remove_comment'),

    # 피드 신고
    path('report/', views_feed.report_feed, name='report_feed'),
    path('unreport/', views_feed.unreport_feed, name='unreport_feed'),
    path('reported_feeds/', views_feed.reported_feeds, name="reported_feeds"),

    # 이모지
    path('emoji/<int:feed_id>/', views_feed.get_emoji_count, name="get_emoji_count"),
    path('emoji/add/', views_feed.add_emoji, name="add_emoji"),
    path('emoji/remove/', views_feed.remove_emoji, name="remove_emoji"),
]