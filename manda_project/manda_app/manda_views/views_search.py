from rest_framework import status
from django.shortcuts import get_list_or_404
from django.contrib.auth.models import User
from rest_framework.response import Response
from ..models import MandaMain, MandaSub, MandaContent, UserProfile, Feed, Comment
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

# 검색 요청 처리

# 만다 심플 검색
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_manda_simples(request):
    search_query = request.GET.get('query', '').strip()

    if not search_query:
        manda_simples = retrieve_manda_simples_for_explore()
    else:
        manda_simples = retrieve_manda_simples(search_query)

    return Response(manda_simples, status=status.HTTP_200_OK)

# 피드 게시물 검색
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_feeds(request):
    search_query = request.GET.get('query', '').strip()

    if not search_query:
        feeds = retrieve_feeds_for_explore()
    else:
        feeds = retrieve_feeds(search_query)

    return Response(feeds, status=status.HTTP_200_OK)

# 추천 유저 검색
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_users(request):
    search_query = request.GET.get('query', '').strip()

    if not search_query:
        users = retrieve_users_for_explore()
    else:
        users = retrieve_users(search_query)

    return Response(users, status=status.HTTP_200_OK)

# 만다심플, 피드, 유저 검색 결과 통합
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_view(request):
    search_query = request.GET.get('query', '').strip()  # 검색어 가져오기

    # 검색어가 없으면 기본 탐색 결과 반환, 있으면 해당 검색어에 따른 결과 반환
    if not search_query:
        manda_simples = retrieve_manda_simples_for_explore()
        feeds = retrieve_feeds_for_explore()
        users = retrieve_users_for_explore()
    else:
        manda_simples = retrieve_manda_simples(search_query)
        feeds = retrieve_feeds(search_query)
        users = retrieve_users(search_query)

    results = {
        'manda_simples': manda_simples,
        'feeds': feeds,
        'users': users
    }
    return Response(results, status=status.HTTP_200_OK)

# 기본 탐색을 위한 MandaMain 객체 반환 함수
def retrieve_manda_simples_for_explore():
    combined_mandamains = MandaMain.objects.all().order_by('-id')[:20]
    return build_manda_simple_data(combined_mandamains)

# 검색어에 따른 MandaMain 객체 반환 함수
def retrieve_manda_simples(query):
    combined_mandamains = MandaMain.objects.filter(
        Q(main_title__icontains=query) |
        Q(user__username__icontains=query)
    ).prefetch_related('mandasub_set', 'user__profile')[:20]
    return build_manda_simple_data(combined_mandamains)

# MandaMain 객체로부터 간단한 데이터 구조화
def build_manda_simple_data(mandamains):
    manda_simples = []
    for mandamain in mandamains:
        user = mandamain.user
        userprofile = user.profile if hasattr(user, 'profile') else None
        userposition = userprofile.user_position if userprofile else None

        main_entry = {
            'id': mandamain.id,
            'main_title': mandamain.main_title,
            'user_id': user.id,
            'username': user.username,
            'userposition': userposition,
            'subs': [{'id': sub.id, 'success': sub.success, 'sub_title': sub.sub_title} for sub in mandamain.mandasub_set.all()]
        }
        manda_simples.append(main_entry)
    return manda_simples

# 기본 탐색을 위한 Feed 객체 반환 함수
def retrieve_feeds_for_explore():
    combined_feeds = Feed.objects.all().order_by('-created_at')[:20]
    return build_feeds_data(combined_feeds)

# 검색어에 따른 Feed 객체 반환 함수
def retrieve_feeds(query):
    combined_feeds = Feed.objects.filter(
        Q(main_id__main_title__icontains=query) |
        Q(sub_id__sub_title__icontains=query) |
        Q(cont_id__content__icontains=query) |
        Q(feed_contents__icontains=query) |
        Q(user__username__icontains=query) |
        Q(user__profile__user_position__icontains=query)
    ).select_related('user', 'user__profile', 'main_id', 'sub_id', 'cont_id').prefetch_related('comment_set')[:20]
    return build_feeds_data(combined_feeds)

# Feed 객체로부터 데이터 구조화
def build_feeds_data(feeds):
    feed_entries = []
    for feed in feeds:
        user = feed.user
        userprofile = user.profile if hasattr(user, 'profile') else None

        main_title = feed.main_id.main_title
        sub_title = feed.sub_id.sub_title
        content = feed.cont_id.content

        comments_list = [
            {'username': comment.user.username, 'comment': comment.comment, 'upload_date': comment.created_at} for comment in feed.comment_set.all()
        ]

        feed_entry = {
            'userInfo': {
                'profile_img': userprofile.user_image if userprofile else None,
                'userPosition': userprofile.user_position if userprofile else None,
                'success': userprofile.success_count if userprofile else None,
                'userName': user.username,
            },
            'contentInfo': {
                'id': feed.id,
                'main_title': main_title,
                'sub_title': sub_title,
                'content': content,
                'post': feed.feed_contents,
                'content_img': str(feed.feed_image),
                'created_at': feed.created_at,
                'tags': feed.feed_hash,
                'emoji_count': feed.emoji_count,
                'comment_info': comments_list
            }
        }
        feed_entries.append(feed_entry)
    return feed_entries

# 기본 탐색을 위한 User 객체 반환 함수
def retrieve_users_for_explore():
    combined_users = User.objects.all().order_by('-date_joined')[:20]
    return build_users_data(combined_users)

# 검색어에 따른 User 객체 반환 함수
def retrieve_users(query):
    combined_users = User.objects.filter(
        Q(username__icontains=query) |
        Q(profile__user_position__icontains=query) |
        Q(profile__user_hash__icontains=query) |
        Q(profile__user_info__icontains=query)
    ).select_related('profile')[:20]
    return build_users_data(combined_users)

# User 객체로부터 데이터 구조화
def build_users_data(users):
    user_entries = []
    for user in users:
        userprofile = user.profile if hasattr(user, 'profile') else None

        user_entry = {
            'username': user.username,
            'user_image': userprofile.user_image if userprofile else None,
            'user_position': userprofile.user_position if userprofile else None,
            'user_hash': userprofile.user_hash if userprofile else None
        }
        user_entries.append(user_entry)
    return user_entries
