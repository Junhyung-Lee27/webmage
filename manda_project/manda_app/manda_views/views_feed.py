from rest_framework import status
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator, EmptyPage
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from ..models import UserProfile, Follow, Feed, Comment, Reaction
from ..serializers.comment_serializer import CommentSerializer  # You will need to create these serializers
from ..serializers.feed_serializer import FeedSerializer
from drf_yasg.utils import swagger_auto_schema
from django.db.models import Count, Q, ExpressionWrapper, F, DurationField, FloatField, Min, Max
from django.db.models.functions import Extract, Exp

from django.utils import timezone
from datetime import timedelta
from collections import defaultdict

# Get feed of a specific user
@api_view(['GET'])
def return_feed(request, user_id):
    user_id = request.GET.get('query')
    feeds = Feed.objects.filter(user=user_id).order_by('-id')

    # 페이지네이션
    default_page = 1
    page = request.GET.get('page', default_page)
    page_size = 10
    paginator = Paginator(feeds, page_size)
    try:
        feeds_page = paginator.page(page)
    except EmptyPage:
        return Response({'message': 'No more pages', 'data': []}, status=status.HTTP_200_OK)

    # 데이터 구조화
    feed_entries = []
    for feed in feeds_page:
        userprofile = feed.user
        main_title = feed.main_id.main_title
        sub_title = feed.sub_id.sub_title
        content = feed.cont_id.content
        success_count = feed.cont_id.success_count

        comments_list = [
            {'username': comment.user.username, 'comment': comment.comment, 'upload_date': comment.created_at} for comment in feed.comment_set.all()
        ]

        feed_entry = {
            'userInfo': {
                'profile_img': userprofile.user_image if userprofile else None,
                'userPosition': userprofile.user_position if userprofile else None,
                'success': userprofile.success_count if userprofile else None,
                'userName': userprofile.username,
            },
            'feedInfo': {
                'id': feed.id,
                'main_title': main_title,
                'sub_title': sub_title,
                'content': content,
                'success_count': success_count,
                'post': feed.feed_contents,
                'content_img': str(feed.feed_image),
                'created_at': feed.created_at,
                'tags': feed.feed_hash,
                'emoji_count': feed.emoji_count,
                'comment_info': comments_list
            }
        }
        feed_entries.append(feed_entry)
        
    return Response(feed_entries)

# 피드 추천 알고리즘 (팔로우, 댓글, 이모지 상호작용 + 최근 인기 게시물)
@api_view(['GET'])
def recommend_feeds(request):
    user = request.user

    # 추천 로직
    # 1 내가 팔로우하는 유저, 나를 팔로우하는 유저
    following_user_ids = Follow.objects.filter(following_user=user).values_list('followed_user', flat=True)
    following_feeds = Feed.objects.filter(user__in=following_user_ids).select_related('user').prefetch_related('comment_set').order_by('-created_at')[:10]
    followed_user_ids = Follow.objects.filter(followed_user=user).values_list('following_user', flat=True)
    followed_feeds = Feed.objects.filter(user__in=followed_user_ids).select_related('user').prefetch_related('comment_set').order_by('-created_at')[:10]
    
    # 2 내가 댓글을 남긴 게시물의 유저, 내 피드 게시물에 댓글 남긴 유저
    commented_feed_ids = Comment.objects.filter(user=user).values_list('feed', flat=True)
    commented_user_ids = Feed.objects.filter(id__in=commented_feed_ids).values_list('user', flat=True)
    commented_user_feeds = Feed.objects.filter(user__in=commented_user_ids).select_related('user').prefetch_related('comment_set').exclude(user=user).order_by('-created_at')[:10]
    commenter_user_ids = Comment.objects.filter(feed__user=user).values_list('user', flat=True)
    commenter_feeds = Feed.objects.filter(user__in=commenter_user_ids).select_related('user').prefetch_related('comment_set').exclude(user=user).order_by('-created_at')[:10]
    
    # 3 내가 이모지 반응을 보이거나, 내 피드 게시물에 이모지를 남긴 유저
    reacted_feed_ids = Reaction.objects.filter(user=user).values_list('feed', flat=True)
    reacted_user_ids = Feed.objects.filter(id__in=reacted_feed_ids).values_list('user', flat=True)
    reacted_user_feeds = Feed.objects.filter(user__in=reacted_user_ids).select_related('user').prefetch_related('comment_set').exclude(user=user).order_by('-created_at')[:10]
    reactor_user_ids = Reaction.objects.filter(feed__user=user).values_list('user', flat=True)
    reactor_feeds = Feed.objects.filter(user__in=reactor_user_ids).select_related('user').prefetch_related('comment_set').exclude(user=user).order_by('-created_at')[:10]

    # 4. 유사한 성향의 사용자 기반 추천 피드
    # user_hash, user_info, user_position 텍스트 간의 유사도 계산 
    # (word2vec, BERT, TF-IDF 같은 기술을 사용해볼 수 있음)

    # 5. 최근 1개월 인기 추천 (댓글, 이모지가 많은 게시물 / 오래된 게시물의 시간 가중치가 지수적으로 감소)
    current_time = timezone.now()
    recent_time_limit = timezone.now() - timedelta(days=30)

    # 시간 가중치(분 단위) 계산 및 쿼리
    popular_feeds = Feed.objects.filter(created_at__gte=recent_time_limit)\
        .annotate(num_comments=Count('comment'), num_reactions=Count('reaction'))\
        .annotate(time_diff=ExpressionWrapper(current_time - F('created_at'), output_field=DurationField()))\
        .annotate(minutes=Extract('time_diff', 'epoch') / 60)\

    time_weight = 0.00004 # 숫자가 클수록 시간 가중치의 영향력 커짐
    time_weighted_popular_feeds = popular_feeds\
        .annotate(time_weight=ExpressionWrapper(Exp(-time_weight * F('minutes')), output_field=FloatField()))

    # 시간 가중치를 0 ~ 1사이로 정규화
    min_time_weight = time_weighted_popular_feeds.aggregate(Min('time_weight'))['time_weight__min']
    max_time_weight = time_weighted_popular_feeds.aggregate(Max('time_weight'))['time_weight__max']
    normalized_popular_feeds = time_weighted_popular_feeds.annotate(
        normalized_time_weight=(F('time_weight') - min_time_weight) / (max_time_weight - min_time_weight)
    )
    
    # 일반 가중치 적용
    weighted_following_feeds = [(feed, 1) for feed in following_feeds] # 내가 팔로우하는 유저의 피드
    weighted_followed_feeds = [(feed, 0.05) for feed in followed_feeds] # 나를 팔로우하는 유저의 피드
    weighted_commented_feeds = [(feed, 0.7) for feed in commented_user_feeds] # 내가 댓글 남긴 유저의 피드
    weighted_commenter_feeds = [(feed, 0.05) for feed in commenter_feeds] # 나에게 댓글 남긴 유저의 피드
    weighted_reacted_feeds = [(feed, 0.5) for feed in reacted_user_feeds] # 내가 이모지 남긴 유저의 피드
    weighted_reactor_feeds = [(feed, 0.05) for feed in reactor_feeds] # 나에게 이모지 남긴 유저의 피드
    weighted_popular_feeds = [(feed, 0.5 * feed.time_weight) for feed in normalized_popular_feeds]

    all_feeds = weighted_following_feeds + weighted_followed_feeds + \
        weighted_commented_feeds + weighted_commenter_feeds + \
        weighted_reacted_feeds + weighted_reactor_feeds + \
        weighted_popular_feeds
    
    # 중복 피드 가중치 계산
    feed_weights = defaultdict(float)
    unique_feeds = set()

    for feed, weight in all_feeds:
        if feed not in unique_feeds:
            unique_feeds.add(feed)
            feed_weights[feed] += weight

    # 가중치 정렬
    recommended_feeds = sorted(feed_weights.items(), key=lambda x: x[1], reverse=True)
  
    # 페이지네이션
    default_page = 1
    page = request.GET.get('page', default_page)
    page_size = 10
    paginator = Paginator(recommended_feeds, page_size)
    try:
        feeds_page = paginator.page(page)
    except EmptyPage:
        return Response({'message': 'No more pages', 'data': []}, status=status.HTTP_200_OK)

    # 데이터 구조화
    feed_entries = []
    for feed, weight in feeds_page:
        userprofile = feed.user
        main_title = feed.main_id.main_title
        sub_title = feed.sub_id.sub_title
        content = feed.cont_id.content
        success_count = feed.cont_id.success_count

        comments_list = [
            {'username': comment.user.username, 'comment': comment.comment, 'upload_date': comment.created_at} for comment in feed.comment_set.all()
        ]

        feed_entry = {
            'userInfo': {
                'profile_img': userprofile.user_image if userprofile else None,
                'userPosition': userprofile.user_position if userprofile else None,
                'success': userprofile.success_count if userprofile else None,
                'userName': userprofile.username,
            },
            'feedInfo': {
                'id': feed.id,
                'main_title': main_title,
                'sub_title': sub_title,
                'content': content,
                'success_count': success_count,
                'post': feed.feed_contents,
                'content_img': str(feed.feed_image),
                'created_at': feed.created_at,
                'tags': feed.feed_hash,
                'emoji_count': feed.emoji_count,
                'comment_info': comments_list,
            }
        }
        feed_entries.append(feed_entry)

    return Response(feed_entries)

# Get feed logs for a specific user
@api_view(['GET'])
def return_feed_log(request, user_id):
    logs = Feed.objects.filter(user=user_id).values('created_at').annotate(feed_count=Count('id'))
    return Response(logs, status=status.HTTP_200_OK)

# Get the timeline for a specific user
@api_view(['GET'])
def return_timeline(request, user_id):
    # This might include the user's feed as well as feeds from their followers.
    # Placeholder logic is provided here. Adjust based on actual requirements.
    timeline_objects = Feed.objects.filter(Q(user_id=user_id) | Q(user__followers__id=user_id))
    serializer = FeedSerializer(timeline_objects, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

# Write a new feed
@swagger_auto_schema(method='post', request_body=FeedSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def write_feed(request):
    serializer = FeedSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Edit a specific feed
@swagger_auto_schema(method='patch', request_body=FeedSerializer)
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def edit_feed(request, feed_id):
    feed = get_object_or_404(Feed, id=feed_id)
    serializer = FeedSerializer(feed, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Set emoji on a feed
@api_view(['PATCH'])
def set_feed_emoji(request, feed_id):
    feed = get_object_or_404(Feed, id=feed_id)
    emoji_count = request.data.get('emoji_count', {})
    feed.emoji_count = emoji_count  # Assuming this is a JSONField
    feed.save()
    return Response({'message': 'Emoji updated successfully.'}, status=status.HTTP_200_OK)

# Comment on a feed
@api_view(['POST'])
def comment_on_feed(request, feed_id):
    feed = get_object_or_404(Feed, id=feed_id)
    serializer = CommentSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(feed=feed)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Edit a comment
@api_view(['PATCH'])
def edit_comment(request, feed_id, comment_id):
    comment = get_object_or_404(Comment, id=comment_id, feed_id=feed_id)
    serializer = CommentSerializer(comment, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

