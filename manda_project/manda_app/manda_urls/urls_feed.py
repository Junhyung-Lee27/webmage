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
    path('<int:feed_id>/set_emoji/', views_feed.set_feed_emoji, name='set_feed_emoji'),
    path('<int:feed_id>/comment/', views_feed.comment_on_feed, name='add_comment'),
    path('<int:feed_id>/comment/<int:comment_id>/', views_feed.edit_comment, name='edit_comment'),

    path('report/', views_feed.report_feed, name='report_feed'),
    path('unreport/', views_feed.unreport_feed, name='unreport_feed'),
    path('reported_feeds/', views_feed.reported_feeds, name="reported_feeds")
]