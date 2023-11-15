from django.shortcuts import get_object_or_404
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
from ..models import UserProfile
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
            user_id = UserProfile.objects.get(username=username).pk
            login(request, user)
            token, created = Token.objects.get_or_create(user=user)
            return Response({'token': token.key, 'user_id': user_id}, status=status.HTTP_200_OK)
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

    # 유효성 검증 성공
    if serializer.is_valid():
        provider = serializer.validated_data.get('provider')
        
        # username이 변경된 사용자는 기존 계정으로 로그인
        if UserProfile.objects.filter(provider=provider).exists():
            user = UserProfile.objects.get(provider=provider)
            username = user.username
            # username을 변경한 사용자의 경우 변경된 username으로 로그인하도록 함
            if serializer.validated_data.get('username') != username:
                return JsonResponse({'username': username}, status=status.HTTP_200_OK)
        
        # 신규 사용자
        password = make_password(serializer.validated_data['password'])
        serializer.validated_data['password'] = password
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    # 유효성 검증 실패
    else:
        errors = serializer.errors

        # username 중복 케이스
        if 'username' in errors and 'username already exists' in errors['username'][0].lower():
            
            # 소셜 회원가입의 경우 -> 기존 사용자 로그인
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
        user = User.objects.get(email=email)
    except User.DoesNotExist:
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

@swagger_auto_schema(method='post', request_body=UserProfileSerializer)
@api_view(['POST'])
def write_profile(request):
    # 아이디 변경 확인
    new_username = request.data.get('username')
    user = User.objects.get(pk=request.data['user'])

    if new_username and new_username != user.username:
        # username 중복 확인
        if User.objects.filter(username=new_username).exists():
            return Response({'error': '이미 사용되고 있는 닉네임입니다😢'}, status=status.HTTP_400_BAD_REQUEST)
    
    # UserProfileSerializer 검증
    serializer = UserProfileSerializer(data=request.data)
    if serializer.is_valid():
        # 이미지 파일 처리
        image_file = request.FILES.get('user_img')
        if image_file:
            url = S3ImgUploader(image_file).upload() 
        else:
            url = None

        # 유저 username 변경
        if new_username and new_username != user.username:
            user.username = new_username
            user.save()

        user_profile = UserProfile.objects.create(
            user=user,
            user_image=url,
            user_position=serializer.validated_data.get('user_position'),
            user_info=serializer.validated_data.get('user_info'),
            user_hash=serializer.validated_data.get('user_hash'),
            success_count=serializer.validated_data.get('success_count')
        )
        response_serializer = UserProfileSerializer(user_profile)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def view_profile(request, user_id):
    user = User.objects.get(pk=user_id)

    # 기본 response_data 설정
    response_data = {
        'user_id': user_id,
        'username': user.username,
        'user_email': user.email
    }

    try:
        user_profile = UserProfile.objects.get(user=user)
        object_key = user_profile.user_image
        url = f'https://d3u19o4soz3vn3.cloudfront.net/img/{object_key}'

        # UserProfile이 있을 때의 추가 정보
        response_data.update({
            'user_img': url,
            'user_position': user_profile.user_position,
            'user_info': user_profile.user_info,
            'user_hash': user_profile.user_hash,
            'success_count': user_profile.success_count
        })

    except UserProfile.DoesNotExist:
        pass
    
    return Response(response_data, status=status.HTTP_200_OK)

@swagger_auto_schema(method='patch', request_body=UserProfileSerializer)
@api_view(['PATCH'])
def edit_profile(request):
    user_profile = get_object_or_404(UserProfile, user=request.data.get('user'))
    user = user_profile.user

    # request.data에서 'username'이 있는 경우 User 모델의 username 변경
    new_username = request.data.get('username')
    if new_username and new_username != user.username:
        # username 중복 확인
        if User.objects.filter(username=new_username).exists():
            return Response({'error': '이미 사용되고 있는 닉네임입니다😢'}, status=status.HTTP_400_BAD_REQUEST)
        user.username = new_username
        user.save()

    serializer = UserProfileSerializer(user_profile, data=request.data, partial=True)
    if serializer.is_valid():
        if 'user_img' in request.data:
            url = S3ImgUploader(request.FILES['user_img'])
            serializer.user_img = url.upload()
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
