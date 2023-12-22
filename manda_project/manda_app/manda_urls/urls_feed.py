from django.urls import path
from ..manda_views import views_feed

urlpatterns = [
    # Feed related URLs
    path('<int:user_id>/', views_feed.return_feed, name='user_feed'),
    path('recommend/', views_feed.recommend_feeds, name='recommend_feed'),
    path('selected_feed/<int:feed_id>', views_feed.selected_feed, name='selected_feed'),
    path('<int:user_id>/log/', views_feed.return_feed_log, name='user_feed_log'),
    path('write/', views_feed.write_feed, name='write_feed'),
    path('edit/<int:feed_id>/', views_feed.edit_feed, name='edit_feed'),
    path('delete/<int:feed_id>/', views_feed.delete_feed, name='delete_feed'),
    # path('search/', views_feed.search_feeds, name='search_feeds'),

    # 피드 신고
    path('report/', views_feed.report_feed, name='report_feed'),
    path('unreport/', views_feed.unreport_feed, name='unreport_feed'),
    path('reported_feeds/', views_feed.reported_feeds, name="reported_feeds"),
    
    # 댓글
    path('<int:feed_id>/comment/', views_feed.get_comments, name="get_comments"),
    path('<int:feed_id>/comment/add/', views_feed.add_comment, name='add_comment'),
    path('<int:feed_id>/comment/<int:comment_id>/edit/', views_feed.edit_comment, name='edit_comment'),
    path('<int:feed_id>/comment/<int:comment_id>/delete/', views_feed.delete_comment, name='delete_comment'),

    # 댓글 신고
    path('comment/<int:comment_id>/report/', views_feed.report_comment, name="report_comment"),
    path('comment/<int:comment_id>/unreport/', views_feed.unreport_comment, name="unreport_comment"),
    path('reported_comments/', views_feed.reported_comments, name="reported_comments"),

    # 이모지
    path('emoji/<int:feed_id>/', views_feed.get_emoji_count, name="get_emoji_count"),
    path('emoji/add/', views_feed.add_emoji, name="add_emoji"),
    path('emoji/remove/', views_feed.remove_emoji, name="remove_emoji"),
]