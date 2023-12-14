from django.shortcuts import get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from django.core import serializers
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.contrib.auth.hashers import check_password
from django.http import HttpResponse, JsonResponse
from django.utils.dateformat import DateFormat
from django.utils import timezone
from django.db.models import Sum
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from ..serializers.user_serializer import UserSerializer, UserAuthenticationSerializer, UserProfileSerializer
from .utils import generate_temp_password, send_temp_password_email
from ..models import UserProfile, Follow, BlockedUser, MandaContent, MandaSub
from ..image_uploader import S3ImgUploader
import re

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

@swagger_auto_schema(method='post', request_body=UserAuthenticationSerializer)
@api_view(['POST'])
@permission_classes([AllowAny])
def user_login(request):
    data = request.data
    try:
        username = data['username']
        password = data['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.deleted_at:
                return Response({'error': 'Account is deactivated'}, status=status.HTTP_400_BAD_REQUEST)
            login(request, user)
            token, created = Token.objects.get_or_create(user=user)
            return Response({'token': token.key, 'user_id': user.id}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)
    except KeyError:
        return Response({'error': 'Missing username or password'}, status=status.HTTP_400_BAD_REQUEST)
    
@api_view(['POST'])
@permission_classes([AllowAny])
def user_logout(requet):
    logout(requet)
    return HttpResponse(status=200)

@swagger_auto_schema(method='post', request_body=UserSerializer)
@api_view(['POST'])
@permission_classes([AllowAny])
def sign_up(request):
    serializer = UserSerializer(data=request.data)

    # 가입 요청 데이터의 유효성 검증 성공
    if serializer.is_valid():
        provider = serializer.validated_data.get('provider')
        
        # 이메일 사용자일 경우 provider에 숫자 1 더함 (<- EMAIL 사용자 간에 구분하기 위함)
        if provider == "EMAIL":
          provider_count = UserProfile.objects.filter(provider__startswith=provider).count()
          provider = f"{provider}{provider_count + 1}"
        
        # username을 변경한 사용자의 경우 변경된 username으로 로그인하도록 함
        if UserProfile.objects.filter(provider=provider).exists():
            user = UserProfile.objects.get(provider=provider)
            username = user.username
            
            if serializer.validated_data.get('username') != username:
                return JsonResponse({'username': username}, status=status.HTTP_200_OK)
        
        # 신규 회원가입
        password = make_password(serializer.validated_data['password'])
        username_count = UserProfile.objects.filter(username__startswith=serializer.validated_data['username']).count()
        if not "EMAIL" in provider:
            serializer.validated_data['username'] = serializer.validated_data['username'] + str(username_count + 1)    
        serializer.validated_data['password'] = password
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    # 가입 요청 데이터의 유효성 검증 실패
    else:
        provider = serializer.data.get('provider')
        errors = serializer.errors

        # username 중복 케이스
        if 'username' in errors and 'username already exists' in errors['username'][0].lower():
            
            # 이미 소셜 회원가입한 사용자의 경우 -> 기존 사용자 로그인
            if 'EMAIL' not in provider:
                username = serializer.data['username']
                password = serializer.data['password']
                
                if UserProfile.objects.filter(username=username).exists():    
                    return Response({'message': 'User already registered. Please log in.'}, status=status.HTTP_200_OK)

            # EMAIL 회원가입의 경우 -> 다른 이름 사용 권고
            if 'EMAIL' in provider:
                return Response({"error": "이미 사용 중인 사용자 이름입니다."}, status=status.HTTP_400_BAD_REQUEST)
        
        # 다른 실패 케이스
        else:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

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
    
    # 이후 재사용할 수 있도록 username, provider 값 변경
    current_time = timezone.now().strftime("%Y%m%d%H%M%S")
    user.username = f"{user.username}_del_{current_time}"
    user.provider = f"{user.provider}_del_{current_time}"

    # 소셜 회원 탈퇴
    if 'EMAIL' not in user.provider:
        user.deleted_at = timezone.now()
        user.save()
        return JsonResponse({'message': 'User soft deleted successfully.'})
    
    # 이메일 회원 탈퇴
    password = request.data.get('password')
    if not password or not check_password(password, user.password):
        return Response({"error": "비밀번호가 일치하지 않습니다."}, status=status.HTTP_400_BAD_REQUEST)

    user.deleted_at = timezone.now()
    user.save()
    return JsonResponse({'message': 'User soft deleted successfully.'})

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
def edit_profile(request):
    user = request.user

    # request.data에서 'username'이 있는 경우 User 모델의 username 변경
    new_username = request.data.get('username')
    if new_username and new_username != user.username:
        if UserProfile.objects.filter(username=new_username).exists():
            return Response({'error': '이미 사용되고 있는 닉네임입니다😢'}, status=status.HTTP_400_BAD_REQUEST)
        user.username = new_username
        user.save()

    serializer = UserProfileSerializer(user, data=request.data, partial=True)
    if serializer.is_valid():
        # if 'user_img' in request.data:
        #     url = S3ImgUploader(request.FILES['user_img'])
        #     serializer.user_img = url.upload()
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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