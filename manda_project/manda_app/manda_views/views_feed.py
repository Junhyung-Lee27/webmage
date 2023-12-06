from rest_framework import status
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator, EmptyPage
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from ..models import UserProfile, Follow, Feed, Comment, Reaction, ReportedFeed, BlockedUser, ReportedComment
from ..serializers.comment_serializer import CommentSerializer  # You will need to create these serializers
from ..serializers.feed_serializer import FeedSerializer
from drf_yasg.utils import swagger_auto_schema
from django.db.models import Count, Q, ExpressionWrapper, F, DurationField, FloatField, Min, Max
from django.db.models.functions import Extract, Exp

from django.utils import timezone
from django.utils.dateformat import DateFormat
from datetime import timedelta
from collections import defaultdict, Counter

# Get feed of a specific user
@api_view(['GET'])
def return_feed(request, user_id):
    user_id = request.GET.get('query')
    feeds = Feed.objects.filter(user=user_id, deleted_at__isnull=True).order_by('-id')

    # 페이지네이션
    default_page = 1
    page = request.GET.get('page', default_page)
    page_size = 10
    paginator = Paginator(feeds, page_size)
    try:
        feeds_page = paginator.page(page)
    except EmptyPage:
        return Response({'message': 'No more pages', 'data': []}, status=status.HTTP_200_OK)

    # 유저가 신고한 댓글 / 차단한 유저 ID
    reported_comment_ids = ReportedComment.objects.filter(reporter=request.user).values_list('comment', flat=True)
    blocked_user_ids = BlockedUser.objects.filter(blocker=user_id).values_list('blocked', flat=True)

    # 데이터 구조화
    feed_entries = []
    for feed in feeds_page:
        userprofile = feed.user
        main_title = feed.main_id.main_title
        sub_title = feed.sub_id.sub_title
        content = feed.cont_id.content
        success_count = feed.cont_id.success_count
        is_following = Follow.objects.filter(followed_user=userprofile, following_user=request.user).exists()

        comments_list = [
            {
                'username': comment.user.username, 
                'comment': comment.comment, 
                'upload_date': comment.created_at
            } 
            for comment in feed.comment_set.all() 
            if comment.deleted_at is None
            and comment.id not in reported_comment_ids
            and comment.user.id not in blocked_user_ids
        ]

        feed_entry = {
            'userInfo': {
                'profile_img': userprofile.user_image if userprofile else None,
                'userPosition': userprofile.user_position if userprofile else None,
                'success': userprofile.success_count if userprofile else None,
                'userName': userprofile.username,
                'id' : userprofile.id,
                'is_following': is_following,
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

    # 차단된 유저 및 피드 게시물
    blocked_user_ids = BlockedUser.objects.filter(blocker=user).values_list('blocked', flat=True)
    reported_feed_ids = ReportedFeed.objects.filter(reporter=user).values_list('feed', flat=True)
    
    # 추천 로직
    # 1 내가 팔로우하는 유저, 나를 팔로우하는 유저
    following_user_ids = Follow.objects.filter(following_user=user).values_list('followed_user', flat=True)
    following_feeds_exclude_deleted = Feed.objects.filter(user__in=following_user_ids, deleted_at__isnull=True)
    following_feeds_exclude_blocked = following_feeds_exclude_deleted.exclude(user__in=blocked_user_ids).exclude(id__in=reported_feed_ids)
    following_feeds = following_feeds_exclude_blocked.select_related('user').prefetch_related('comment_set').order_by('-id')[:10]
    
    followed_user_ids = Follow.objects.filter(followed_user=user).values_list('following_user', flat=True)
    followed_feeds_exclude_deleted = Feed.objects.filter(user__in=followed_user_ids, deleted_at__isnull=True)
    followed_feeds_exclude_blocked = followed_feeds_exclude_deleted.exclude(user__in=blocked_user_ids).exclude(id__in=reported_feed_ids)
    followed_feeds = followed_feeds_exclude_blocked.select_related('user').prefetch_related('comment_set').order_by('-id')[:10]
    
    # 2 내가 댓글을 남긴 게시물의 유저, 내 피드 게시물에 댓글 남긴 유저
    commented_feed_ids = Comment.objects.filter(user=user).values_list('feed', flat=True)
    commented_user_ids = Feed.objects.filter(id__in=commented_feed_ids).values_list('user', flat=True)
    commented_user_feeds_exclude_deleted = Feed.objects.filter(user__in=commented_user_ids, deleted_at__isnull=True)
    commented_user_feeds_exclude_blocked = commented_user_feeds_exclude_deleted.exclude(user__in=blocked_user_ids).exclude(id__in=reported_feed_ids)
    commented_user_feeds = commented_user_feeds_exclude_blocked.select_related('user').prefetch_related('comment_set').exclude(user=user).order_by('-id')[:10]
    
    commenter_user_ids = Comment.objects.filter(feed__user=user).values_list('user', flat=True)
    commenter_feeds_exclude_deleted = Feed.objects.filter(user__in=commenter_user_ids, deleted_at__isnull=True)
    commenter_feeds_exclude_blocked = commenter_feeds_exclude_deleted.exclude(user__in=blocked_user_ids).exclude(id__in=reported_feed_ids)
    commenter_feeds = commenter_feeds_exclude_blocked.select_related('user').prefetch_related('comment_set').exclude(user=user).order_by('-id')[:10]
    
    # 3 내가 이모지 반응을 보이거나, 내 피드 게시물에 이모지를 남긴 유저
    reacted_feed_ids = Reaction.objects.filter(user=user).values_list('feed', flat=True)
    reacted_user_ids = Feed.objects.filter(id__in=reacted_feed_ids).values_list('user', flat=True)
    reacted_user_feeds_exclude_deleted = Feed.objects.filter(user__in=reacted_user_ids, deleted_at__isnull=True)
    reacted_user_feeds_exclude_blocked = reacted_user_feeds_exclude_deleted.exclude(user__in=blocked_user_ids).exclude(id__in=reported_feed_ids)
    reacted_user_feeds = reacted_user_feeds_exclude_blocked.select_related('user').prefetch_related('comment_set').exclude(user=user).order_by('-id')[:10]

    reactor_user_ids = Reaction.objects.filter(feed__user=user).values_list('user', flat=True)
    reactor_feeds_exclude_deleted = Feed.objects.filter(user__in=reactor_user_ids, deleted_at__isnull=True)
    reactor_feeds_exclude_blocked = reactor_feeds_exclude_deleted.exclude(user__in=blocked_user_ids).exclude(id__in=reported_feed_ids)
    reactor_feeds = reactor_feeds_exclude_blocked.select_related('user').prefetch_related('comment_set').exclude(user=user).order_by('-id')[:10]

    # 4. 유사한 성향의 사용자 기반 추천 피드
    # user_hash, user_info, user_position 텍스트 간의 유사도 계산 
    # (word2vec, BERT, TF-IDF 같은 기술을 사용해볼 수 있음)

    # 5. 최근 1개월 인기 추천 (댓글, 이모지가 많은 게시물 / 오래된 게시물의 시간 가중치가 지수적으로 감소)
    current_time = timezone.now()
    recent_time_limit = timezone.now() - timedelta(days=30)

    # 시간 가중치(분 단위) 계산 및 쿼리
    popular_feeds_exclude_deleted = Feed.objects.filter(created_at__gte=recent_time_limit, deleted_at__isnull=True)
    popular_feeds_exclude_blocked = popular_feeds_exclude_deleted.exclude(user__in=blocked_user_ids).exclude(id__in=reported_feed_ids)
    popular_feeds = popular_feeds_exclude_blocked\
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

    # 유저가 신고한 댓글 ID 목록
    reported_comment_ids = ReportedComment.objects.filter(reporter=request.user).values_list('comment', flat=True)

    # 데이터 구조화
    feed_entries = []
    for feed, weight in feeds_page:
        userprofile = feed.user
        main_title = feed.main_id.main_title
        sub_title = feed.sub_id.sub_title
        content = feed.cont_id.content
        success_count = feed.cont_id.success_count
        is_following = Follow.objects.filter(followed_user=userprofile, following_user=request.user).exists()

        comments_list = [
            {
                'username': comment.user.username, 
                'comment': comment.comment, 
                'upload_date': comment.created_at
            } 
            for comment in feed.comment_set.all() 
            if comment.deleted_at is None
            and comment.id not in reported_comment_ids
            and comment.user.id not in blocked_user_ids
        ]

        feed_entry = {
            'userInfo': {
                'profile_img': userprofile.user_image if userprofile else None,
                'userPosition': userprofile.user_position if userprofile else None,
                'success': userprofile.success_count if userprofile else None,
                'userName': userprofile.username,
                'id' : userprofile.id,
                'is_following': is_following,
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

# Delete(soft) a specific feed
@api_view(['POST'])
def delete_feed(request, feed_id):
    user = request.user
    feed = get_object_or_404(Feed, id=feed_id, user=user)
    feed.deleted_at = timezone.now()
    feed.save()

    return Response({'message': 'Feed soft deleted successfully.'}, status=status.HTTP_200_OK)

@api_view(['POST'])
def report_feed(request):
    reporter_id = request.user.id
    reported_feed = request.data.get('reported_id')
    reason = request.data.get('reason')

    report, created = ReportedFeed.objects.get_or_create(reporter_id = reporter_id, feed_id = reported_feed, reason = reason)

    if created:
        return Response({'message': '피드 신고 성공'}, status=status.HTTP_201_CREATED)
    else:
        return Response({'error' : '이미 신고 관계가 존재합니다.'}, status=status.HTTP_400_BAD_REQUEST)
    
@api_view(['DELETE'])
def unreport_feed(request):
    reporter_id = request.user.id
    reported_feed = request.data.get('reported_id')

    try:
        report = ReportedFeed.objects.get(reporter_id = reporter_id, feed_id = reported_feed)
        report.delete()
        return Response({'message': '신고 취소 성공'}, status=status.HTTP_204_NO_CONTENT)
    except ReportedFeed.DoesNotExist:
        return Response({'error': '신고 관계가 존재하지 않습니다.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
@api_view(['GET'])
def reported_feeds(request):
    reporter_id = request.user.id

    try:
        reported_feeds = ReportedFeed.objects.filter(reporter_id=reporter_id, feed__deleted_at__isnull=True)
        reported_feeds_data = []
        
        for reported_feed in reported_feeds:
            feed = reported_feed.feed
            userprofile = feed.user

            if userprofile.deleted_at is None:
              reported_at_formatted = DateFormat(reported_feed.reported_at).format('Y-m-d A h:i')

              reported_feed_entry = {
                  'id': feed.id,
                  'username': userprofile.username,
                  'feed_contents': feed.feed_contents,
                  'reason': reported_feed.reason,
                  'reported_at': reported_at_formatted
              }
              reported_feeds_data.append(reported_feed_entry)

        return Response(reported_feeds_data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

# 특정 피드에 대한 자신 및 전체 이모지 카운트 조회 함수
@api_view(['GET'])
def get_emoji_count(request, feed_id):
    reactions = Reaction.objects.filter(feed_id=feed_id).values_list('emoji_name', flat=True)
    emoji_count = Counter(reactions)
    
    user_reactions = Reaction.objects.filter(user=request.user, feed_id=feed_id).values_list('emoji_name', flat=True)

    return Response({'emoji_count': dict(emoji_count), 'user_reactions': list(user_reactions)}, status=status.HTTP_200_OK)

# 이모지 입력
@api_view(['POST'])
def add_emoji(request):
    user_id = request.user.id
    feed_id = request.data.get('feed_id')
    emoji_name = request.data.get('emoji_name')

    Reaction.objects.create(user_id=user_id, feed_id=feed_id, emoji_name=emoji_name)

    return Response({'message': '이모지 입력 성공'}, status=status.HTTP_201_CREATED)

# 이모지 취소
@api_view(['DELETE'])
def remove_emoji(request):
    user_id = request.user.id
    feed_id = request.data.get('feed_id')
    emoji_name = request.data.get('emoji_name')

    try:
        reaction = Reaction.objects.get(user_id=user_id, feed_id=feed_id, emoji_name=emoji_name)
        reaction.delete()
        return Response({'message': '이모지 삭제 성공'}, status=status.HTTP_204_NO_CONTENT)
    except Reaction.DoesNotExist:
        return Response({'error': '이모지 리액션이 존재하지 않습니다.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

# 댓글 조회
@api_view(['GET'])
def get_comments(request, feed_id):
    user = request.user
    reported_comment_ids = ReportedComment.objects.filter(reporter=user).values_list('comment', flat=True)
    blocked_user_ids = BlockedUser.objects.filter(blocker=user).values_list('blocked', flat=True)
    
    comments = Comment.objects.filter(feed_id=feed_id, deleted_at__isnull=True)\
      .exclude(id__in=reported_comment_ids).exclude(user__in=blocked_user_ids).order_by('-created_at')
    page = request.query_params.get('page', 1)
    page_size = 5

    paginator = Paginator(comments, page_size)
    try:
        comments_page = paginator.page(page)
    except EmptyPage:
        return Response({'message': 'No more pages', 'data': []}, status=status.HTTP_200_OK)

    serializer = CommentSerializer(comments_page, many=True)
    return Response({'comment_info': serializer.data, 'count': paginator.count}, status=status.HTTP_200_OK)

# 댓글 생성
@api_view(['POST'])
def add_comment(request, feed_id):
    feed = get_object_or_404(Feed, id=feed_id)
    serializer = CommentSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(feed=feed, user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 댓글 수정
@api_view(['PATCH'])
def edit_comment(request, feed_id, comment_id):
    comment = get_object_or_404(Comment, id=comment_id, feed_id=feed_id)
    serializer = CommentSerializer(comment, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 댓글 삭제
@api_view(['DELETE'])
def delete_comment(request, feed_id, comment_id):
    comment = get_object_or_404(Comment, id=comment_id, feed_id=feed_id)
    comment.deleted_at = timezone.now()
    comment.save()
    return Response({'message': '댓글 삭제 성공'}, status=status.HTTP_204_NO_CONTENT)

# 댓글 신고
@api_view(['POST'])
def report_comment(request, comment_id):
    reporter_id = request.user.id
    reason = request.data.get('reason')

    comment, created = ReportedComment.objects.get_or_create(reporter_id=reporter_id, comment_id=comment_id, reason=reason)

    if created:
        return Response({'message': '댓글 신고 성공'}, status=status.HTTP_201_CREATED)
    else:
        return Response({'error' : '이미 신고 관계가 존재합니다.'}, status=status.HTTP_400_BAD_REQUEST)
    
# 댓글 신고 취소
@api_view(['DELETE'])
def unreport_comment(request, comment_id):
    reporter_id = request.user.id
    
    try:
        report = ReportedComment.objects.get(reporter_id=reporter_id, comment_id=comment_id)
        report.delete()
        return Response({'message' : '신고 취소 성공'}, status=status.HTTP_204_NO_CONTENT)
    except ReportedComment.DoesNotExist:
        return Response({'error': '신고 관계가 존재하지 않습니다.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def reported_comments(request):
    reporter_id = request.user.id

    try:
        reported_comments = ReportedComment.objects.filter(reporter_id=reporter_id, comment__deleted_at__isnull=True)
        reported_comments_data = []
        
        for reported_comment in reported_comments:
            comment = reported_comment.comment
            userprofile = comment.user

            if userprofile.deleted_at is None:
              reported_at_formatted = DateFormat(reported_comment.reported_at).format('Y-m-d A h:i')

              reported_comment_entry = {
                  'id': comment.id,
                  'username': userprofile.username,
                  'comment': comment.comment,
                  'reason': reported_comment.reason,
                  'reported_at': reported_at_formatted
              }
              reported_comments_data.append(reported_comment_entry)

        return Response(reported_comments_data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)