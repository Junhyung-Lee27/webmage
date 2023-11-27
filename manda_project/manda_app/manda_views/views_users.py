from django.shortcuts import get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.contrib.auth.hashers import check_password
from django.http import HttpResponse, JsonResponse
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from ..serializers.user_serializer import UserSerializer, UserAuthenticationSerializer, UserProfileSerializer
from .utils import generate_temp_password, send_temp_password_email
from ..models import UserProfile, Follow
from ..image_uploader import S3ImgUploader

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
        serializer.validated_data['password'] = password
        serializer.validated_data['provider'] = provider
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

    # request에서 비밀번호를 가져옴
    password = request.data.get('password')

    # 비밀번호 확인
    if not password or not check_password(password, user.password):
        return Response({"error": "비밀번호가 일치하지 않습니다."}, status=status.HTTP_400_BAD_REQUEST)

    user.delete()
    return JsonResponse({'message': 'User deleted successfully.'})

@api_view(['GET'])
def view_profile(reqeust, user_id):
    user = UserProfile.objects.get(id=user_id)

    # 기본 response_data 설정
    response_data = {
        'user_id': user_id,
        'username': user.username,
        'user_email': user.email
    }

    try:
        object_key = user.user_image
        url = f'https://d3u19o4soz3vn3.cloudfront.net/img/{object_key}'

        # UserProfile이 있을 때의 추가 정보
        response_data.update({
            'user_image': url,
            'user_position': user.user_position,
            'user_info': user.user_info,
            'user_hash': user.user_hash,
            'success_count': user.success_count
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

    try:
        existing_follow = Follow.objects.get(followed_user_id=following_id, following_user_id=follower_id)
        return Response({'error': '이미 팔로우 관계가 존재합니다.'}, status=status.HTTP_400_BAD_REQUEST)
    except ObjectDoesNotExist:
        try:
            Follow.objects.create(followed_user_id=following_id, following_user_id=follower_id)
            return Response({'message': '팔로우 성공'}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

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
    

@api_view(['GET'])
def get_is_following(request, target_user_id):
    user_id = request.user.id

    try:
        is_following = Follow.objects.filter(followed_user_id=target_user_id, following_user_id=user_id).exists()
        return Response({'is_following': is_following}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)