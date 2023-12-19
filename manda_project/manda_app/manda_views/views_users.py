from django.shortcuts import get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from django.core import serializers
from django.core.paginator import Paginator, EmptyPage
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError
from django.http import HttpResponse, JsonResponse
from django.utils.dateformat import DateFormat
from django.utils import timezone
from django.db.models import Sum, Q, F, Count, FloatField, ExpressionWrapper
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from ..serializers.user_serializer import UserSerializer, UserAuthenticationSerializer, UserProfileSerializer
from .utils import generate_temp_password, send_temp_password_email
from ..models import UserProfile, Follow, BlockedUser, MandaContent, MandaSub, Comment, Reaction
from ..image_uploader import S3ImgUploader
from datetime import timedelta
import re

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

@swagger_auto_schema(method='post', request_body=UserAuthenticationSerializer)
@api_view(['POST'])
@permission_classes([AllowAny])
def user_login(request):
    data = request.data
    try:
        username = data.get('username')
        provider = data.get('provider')

        # EMAIL 회원 로그인
        if provider == 'EMAIL':
            # username 또는 이메일로 로그인 가능
            if '@' in username:
                user = UserProfile.objects.filter(email=username).first()
            else:
                user = UserProfile.objects.filter(username=username).first()

            # 비밀번호 확인
            password = data.get('password')
            if not check_password(password, user.password):
                return Response({'error': 'username과 password를 다시 확인해주세요'}, status=status.HTTP_400_BAD_REQUEST)

        # KAKAO 회원 로그인 로직
        elif provider == 'KAKAO':
            user = UserProfile.objects.filter(username=username).first()

        # 유저 존재 여부 및 is_active 확인
        if not user or not user.is_active:
            return Response({'error': '존재하지 않는 회원입니다'}, status=status.HTTP_400_BAD_REQUEST)

        # 로그인 및 토큰 발급
        login(request, user)
        token, created = Token.objects.get_or_create(user=user)
        return Response({'token': token.key, 'user_id': user.id}, status=status.HTTP_200_OK)

    except KeyError:
        return Response({'error': 'Missing username or provider'}, status=status.HTTP_400_BAD_REQUEST)
    
@api_view(['POST'])
@permission_classes([AllowAny])
def user_logout(requet):
    logout(requet)
    return HttpResponse(status=200)

def custom_password_validator(password):
    # 최소 8자 이상
    if len(password) < 8:
        return False, "비밀번호는 최소 8자 이상이어야 합니다."

    # 문자(영문, 한글), 숫자, 기호 중 2종류 이상 조합
    if not re.match(r'((?=.*[A-Za-z\uAC00-\uD7A3])(?=.*\d)|(?=.*[A-Za-z\uAC00-\uD7A3])(?=.*[!@#$%^&*])|(?=.*\d)(?=.*[!@#$%^&*]))', password):
        return False, "비밀번호는 문자, 숫자, 기호 중 2개 이상을 조합하여야 합니다."

    # 문자, 숫자, 기호 모두 포함하는 경우
    if re.match(r'(?=.*[A-Za-z\uAC00-\uD7A3])(?=.*\d)(?=.*[!@#$%^&*])', password):
        return True, ""

    return True, ""

@swagger_auto_schema(method='post', request_body=UserSerializer)
@api_view(['POST'])
@permission_classes([AllowAny])
def sign_up(request):
    provider = request.data['provider']
    email = request.data['email']
    username = request.data['username']

    # KAKAO 로그인 예외 처리
    if provider == 'KAKAO':
        existing_user = UserProfile.objects.filter(email=email, is_active=True)
        if existing_user.exists():
            return Response({'username': existing_user.first().username}, status=status.HTTP_200_OK)
        
    serializer = UserSerializer(data=request.data)
    
    if serializer.is_valid():
        existing_user_by_username = UserProfile.objects.filter(username=username).first()
        existing_user_by_email = UserProfile.objects.filter(email=email).first()
        
        # 유저명 유효성 검사
        if not 6 <= len(username) <= 12 or not re.match("^[A-Za-z0-9가-힣-_]+$", username):
            return Response({"error": "유효하지 않은 사용자 이름입니다."}, status=status.HTTP_400_BAD_REQUEST)

        # 유저명 중복 검사
        if existing_user_by_username:
            return Response({"error": "이미 사용 중인 사용자 이름입니다."}, status=status.HTTP_400_BAD_REQUEST)
        
        # 이메일 중복 검사
        if existing_user_by_email:
            return Response({"error": "이미 사용 중인 이메일입니다."}, status=status.HTTP_400_BAD_REQUEST)


        # 비밀번호 유효성 검사
        password = serializer.validated_data.get('password')
        is_valid, message = custom_password_validator(password)
        if not is_valid:
          return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)

        # 비밀번호 암호화
        encrypted_password = make_password(password)
        
        # 사용자 저장
        user = serializer.save(password=encrypted_password)
        user.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(method='patch', request_body=UserSerializer)
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def user_edit(request):
    user = request.user
    serializer = UserSerializer(user, data=request.data, partial=True)
    if serializer.is_valid():
        if 'password' in request.data:
            password = make_password(serializer.validated_data['password'])
            serializer.validated_data['password'] = password
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'email': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL),
        },
        required=['username', 'email']
    )
)
@api_view(['POST'])
def reset_password(request):
    email = request.data['email']
    try:
        user = UserProfile.objects.get(email=email)
    except UserProfile.DoesNotExist:
        return Response({'error': 'User with this email address does not exist.'}, status=status.HTTP_404_NOT_FOUND)

    temp_password = generate_temp_password()
    user.set_password(temp_password)
    user.save()

    send_temp_password_email(user, temp_password)

    return Response({'message': 'Temporary password has been sent to your email address.'}, status=status.HTTP_200_OK)
    
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_user(request):
    user = request.user
    data = request.data
    provider = user.provider

    # 현재 시간 기록
    current_time = timezone.now()

    # 소셜 로그인 회원 탈퇴 처리
    if 'KAKAO' in provider:
        user.username = f"{user.username}_del_{current_time.strftime('%Y%m%d%H%M%S')}"
        user.email = f"{user.email}_del_{current_time.strftime('%Y%m%d%H%M%S')}"
        
        user.is_active = False
        user.deleted_at = current_time
        user.save()
        return JsonResponse({'message': 'User successfully deactivated.'})

    # 이메일 회원 탈퇴 처리
    else:
        password = data.get('password')
        if not password:
            return JsonResponse({'error': '비밀번호를 입력해야 합니다.'}, status=status.HTTP_400_BAD_REQUEST)

        if not user.check_password(password):
            return JsonResponse({'error': '비밀번호가 일치하지 않습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        user.username = f"{user.username}_del_{current_time.strftime('%Y%m%d%H%M%S')}"
        user.email = f"{user.email}_del_{current_time.strftime('%Y%m%d%H%M%S')}"

        user.is_active = False
        user.deleted_at = current_time
        user.save()
        return JsonResponse({'message': 'User successfully deactivated.'})


@api_view(['GET'])
def view_profile(reqeust, user_id):
    current_user = reqeust.user
    user = UserProfile.objects.get(id=user_id)

    follower_count = Follow.objects.filter(followed_user=user).count()
    is_following = Follow.objects.filter(followed_user=user, following_user=current_user).exists()
    success_count_total = MandaContent.objects.filter(
        sub_id__in=MandaSub.objects.filter(main_id__user=user)
    ).aggregate(Sum('success_count'))['success_count__sum'] or 0
    provider_str = re.sub(r'\d+|[a-z]|-', '', user.provider)
    
    response_data = {
        'userId': user_id,
        'username': user.username,
        'followerCount': follower_count,
        'successCount': success_count_total,
        'userPosition': user.user_position,
        'userInfo': user.user_info,
        'userHash': user.user_hash,
        'userEmail': user.email,
        'userProvider': provider_str,
        'is_following': is_following
    }

    # User Image가 있을 때의 추가 정보
    try:
        object_key = user.user_image
        url = f'https://d3u19o4soz3vn3.cloudfront.net/img/{object_key}'
        response_data.update({
            'userImg': url,
        })

    except UserProfile.DoesNotExist:
        pass
    
    return Response(response_data, status=status.HTTP_200_OK)

@swagger_auto_schema(method='patch', request_body=UserProfileSerializer)
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def edit_profile(request):
    user = request.user
    data = request.data

    # 유저명 유효성 검사
    if 'username' in data:
        if not 6 <= len(data['username']) <= 12 or not re.match("^[A-Za-z0-9가-힣-_]+$", data['username']):
            return Response({"error": "유효하지 않은 사용자 이름입니다."}, status=status.HTTP_400_BAD_REQUEST)
        if data['username'] != user.username and UserProfile.objects.filter(username=data['username']).exists():
            return Response({'error': '이미 사용되고 있는 닉네임입니다😢'}, status=status.HTTP_400_BAD_REQUEST)

    # 이메일 중복 체크
    if 'email' in data and data['email'] != user.email and UserProfile.objects.filter(email=data['email']).exists():
        return Response({'error': '이미 사용되고 있는 이메일입니다😢'}, status=status.HTTP_400_BAD_REQUEST)

    # 비밀번호 변경 시 유효성 검사 및 암호화
    if 'password' in data:
        is_valid, message = custom_password_validator(data['password'])
        if not is_valid:
            return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)
        data['password'] = make_password(data['password'])

    serializer = UserProfileSerializer(user, data=data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

def construct_user_entries(user_profiles, current_user):
    user_profile_entries = []

    for user_profile in user_profiles:
        is_following = Follow.objects.filter(
            followed_user=user_profile, following_user=current_user
        ).exists()

        user_entry = {
            'id': user_profile.id,
            'username': user_profile.username,
            'userImg': user_profile.user_image,
            'userPosition': user_profile.user_position,
            'userHash': user_profile.user_hash,
            'userInfo': user_profile.user_info,
            'is_following': is_following
        }
        user_profile_entries.append(user_entry)

    return user_profile_entries

@api_view(['GET'])
def search_users(request):
    search_keyword = request.GET.get('keyword', '')
    current_user = request.user

    # 차단 유저 제외
    blocked_user_ids = BlockedUser.objects.filter(blocker=current_user).values_list('blocked', flat=True)
    
    # 검색어에 따른 User 객체 검색
    combined_users = UserProfile.objects.filter(
        Q(is_active=True) &
        (
            Q(username__icontains=search_keyword) |
            Q(user_position__icontains=search_keyword) |
            Q(user_hash__icontains=search_keyword) |
            Q(user_info__icontains=search_keyword)
        )
    ).distinct('id').exclude(id__in=blocked_user_ids)

    # 페이지네이션
    default_page = 1
    page = int(request.GET.get('page', default_page))
    page_size = 6
    paginator = Paginator(combined_users, page_size)

    try:
        searched_user_page = paginator.page(page)
    except EmptyPage:
        return Response({'message': 'No more pages', 'data': []}, status=status.HTTP_200_OK)

    # 데이터 구조화
    searched_users_entries = construct_user_entries(searched_user_page, current_user)

    return Response(searched_users_entries, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_trending_users(request):
    user = request.user
    current_time = timezone.now()
    one_month_ago = current_time - timedelta(days=30)

    # 차단 유저 제외
    blocked_user_ids = BlockedUser.objects.filter(blocker=user).values_list('blocked', flat=True)

    # 가중치 설정
    weight_new_followers = 7  # 최근 1개월간 팔로워 증가 (팔로우 = 한 번만 가능)
    weight_feed_comments = 2  # 최근 1개월간 받은 댓글 (댓글 = 각각의 피드에 무제한으로 가능)
    weight_feed_reactions = 1  # 최근 1개월간 받은 이모티콘 리액션 (리액션 = 각각의 피드에 5회씩 가능)

    trending_users = UserProfile.objects.annotate(
        new_followers=Count('follower', filter=Q(follower__created_at__gte=one_month_ago)),
        feed_comments=Count('feed__comment', filter=Q(feed__comment__created_at__gte=one_month_ago)),
        feed_reactions=Count('feed__reaction', filter=Q(feed__reaction__created_at__gte=one_month_ago))
    ).annotate(
        total_score=ExpressionWrapper(
            weight_new_followers * F('new_followers') +
            weight_feed_comments * F('feed_comments') +
            weight_feed_reactions * F('feed_reactions'),
            output_field=FloatField()
        )
    ).exclude(id__in=blocked_user_ids).order_by('-total_score')[:6]

    # 페이지네이션
    default_page = 1
    page = request.GET.get('page', default_page)
    page_size = 6
    paginator = Paginator(trending_users, page_size)
    try:
        trending_users_page = paginator.page(page)
    except EmptyPage:
        return Response({'message': 'No more pages', 'data': []}, status=status.HTTP_200_OK)

    # 데이터 구조화
    trending_users_entries = construct_user_entries(trending_users_page, user)
    
    return Response(trending_users_entries)

@api_view(['GET'])
def get_familiar_users(request):
    user = request.user

    # 차단 유저 제외
    blocked_user_ids = BlockedUser.objects.filter(blocker=user).values_list('blocked', flat=True)

    # 1. 내가 팔로우하는 유저가 팔로우하는 유저, 나를 팔로우하는 유저가 팔로우하는 유저
    my_followings = Follow.objects.filter(following_user=user).values_list('followed_user', flat=True)
    followings_of_my_followings = Follow.objects.filter(following_user__in=my_followings).values_list('followed_user', flat=True)
    my_followers = Follow.objects.filter(followed_user=user).values_list('following_user', flat=True)
    followings_of_my_followers = Follow.objects.filter(following_user__in=my_followers).values_list('followed_user', flat=True)

    # 2. 내가 댓글을 남긴 피드의 작성자, 내 피드에 댓글을 남긴 유저
    commented_feed_authors = Comment.objects.filter(user=user).values_list('feed__user', flat=True)
    users_commented_on_my_feeds = Comment.objects.filter(feed__user=user).values_list('user', flat=True)

    # 3. 내가 이모지 반응을 남긴 피드의 작성자, 내 피드에 이모지 반응을 남긴 유저
    reacted_feed_authors = Reaction.objects.filter(user=user).values_list('feed__user', flat=True)
    users_reacted_on_my_feeds = Reaction.objects.filter(feed__user=user).values_list('user', flat=True)

    # 유저 ID 집합 생성
    familiar_user_ids = set(followings_of_my_followings | followings_of_my_followers | 
                            commented_feed_authors | users_commented_on_my_feeds | 
                            reacted_feed_authors | users_reacted_on_my_feeds)

    familiar_users = UserProfile.objects.filter(id__in=familiar_user_ids).exclude(id__in=blocked_user_ids)

    # 페이지네이션
    default_page = 1
    page = request.GET.get('page', default_page)
    page_size = 6
    paginator = Paginator(familiar_users, page_size)

    try:
        users_page = paginator.page(page)
    except EmptyPage:
        return Response({'message': 'No more pages', 'data': []}, status=status.HTTP_200_OK)

    # 데이터 구조화
    familiar_users_entries = construct_user_entries(users_page, user)
    
    return Response(familiar_users_entries)

@api_view(['GET'])
def get_active_users(request):
    user = request.user
    current_time = timezone.now()
    one_month_ago = current_time - timedelta(days=30)

    # 차단 유저 제외
    blocked_user_ids = BlockedUser.objects.filter(blocker=user).values_list('blocked', flat=True)

    # 가중치 설정
    weight_feed = 20  # 최근 1개월간 게시물 수
    weight_comment = 5  # 최근 1개월간 입력한 댓글
    weight_reaction = 1  # 최근 1개월간 입력한 이모티콘 리액션

    # 활동 기준에 따른 유저 추출
    active_users = UserProfile.objects.annotate(
        feed_count=Count('feed', filter=Q(feed__created_at__gte=one_month_ago)),
        comment_count=Count('feed__comment', filter=Q(feed__comment__created_at__gte=one_month_ago)),
        reaction_count=Count('feed__reaction', filter=Q(feed__reaction__created_at__gte=one_month_ago))
    ).annotate(
        total_score=ExpressionWrapper(
            weight_feed * F('feed_count') +
            weight_comment * F('comment_count') +
            weight_reaction * F('reaction_count'),
            output_field=FloatField()
        )
    ).exclude(id__in=blocked_user_ids).order_by('-total_score')

    # 페이지네이션
    default_page = 1
    page = request.GET.get('page', default_page)
    page_size = 6
    paginator = Paginator(active_users, page_size)

    try:
        users_page = paginator.page(page)
    except EmptyPage:
        return Response({'message': 'No more pages', 'data': []}, status=status.HTTP_200_OK)

    # 데이터 구조화
    active_users_entries = construct_user_entries(users_page, user)
    
    return Response(active_users_entries)

@api_view(['POST'])
def follow_user(request):
    follower_id = request.user.id
    following_id = request.data.get('following_id')

    follow, created = Follow.objects.get_or_create(followed_user_id=following_id, following_user_id=follower_id)

    if created:
        return Response({'message': '팔로우 성공'}, status=status.HTTP_201_CREATED)
    else:
        return Response({'error': '이미 팔로우 관계가 존재합니다.'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
def unfollow_user(request):
    follower_id = request.user.id
    following_id = request.data.get('following_id')

    try:
        follow = Follow.objects.get(followed_user_id=following_id, following_user_id=follower_id)
        follow.delete()
        return Response({'message': '언팔로우 성공'}, status=status.HTTP_204_NO_CONTENT)
    except Follow.DoesNotExist:
        return Response({'error': '팔로우 관계가 존재하지 않습니다.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
@api_view(['POST'])
def block_user(request):
    blocker_id = request.user.id
    blocked_id = request.data.get('blocked_id')

    block, created = BlockedUser.objects.get_or_create(blocker_id = blocker_id, blocked_id = blocked_id)

    if created:
        return Response({'message': '유저 차단 성공'}, status=status.HTTP_201_CREATED)
    else:
        return Response({'error' : '이미 차단 관계가 존재합니다.'}, status=status.HTTP_400_BAD_REQUEST)
  
@api_view(['DELETE'])
def unblock_user(request):
    blocker_id = request.user.id
    blocked_id = request.data.get('blocked_id')

    try:
        block = BlockedUser.objects.get(blocker_id = blocker_id, blocked_id = blocked_id)
        block.delete()
        return Response({'message': '차단 해제 성공'}, status=status.HTTP_204_NO_CONTENT)
    except BlockedUser.DoesNotExist:
        return Response({'error': '차단 관계가 존재하지 않습니다.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
@api_view(['GET'])
def blocked_users(request):
    blocker_id = request.user.id

    try:
        blocked_users = BlockedUser.objects.filter(blocker_id=blocker_id)
        blocked_users_data = []
        
        for blocked_user in blocked_users:
            userprofile = blocked_user.blocked
            
            if userprofile.deleted_at is None:
                blocked_at_formatted = DateFormat(blocked_user.blocked_at).format('Y-m-d A h:i')

                blocked_user_entry = {
                    'id': userprofile.id,
                    'username': userprofile.username,
                    'blocked_at': blocked_at_formatted
                }
                blocked_users_data.append(blocked_user_entry)

        return Response(blocked_users_data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)