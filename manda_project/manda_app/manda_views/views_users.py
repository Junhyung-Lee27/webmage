from rest_framework import status
from django.shortcuts import get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.http import HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token
from ..serializers.user_serializer import UserSerializer, UserAuthenticationSerializer, UserProfileSerializer
from .utils import generate_temp_password, send_temp_password_email
from ..models import UserProfile
from ..image_uploader import S3ImgUploader

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

@swagger_auto_schema(method='post', request_body=UserAuthenticationSerializer)
@api_view(['POST'])
def user_login(request):
    data = request.data
    try:
        username = data['username']
        password = data['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            token, created = Token.objects.get_or_create(user=user)
            return Response({'token': token.key}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)
    except KeyError:
        return Response({'error': 'Missing username or password'}, status=status.HTTP_400_BAD_REQUEST)
    
@api_view(['POST'])
def user_logout(requet):
    logout(requet)
    return HttpResponse(status=200)

@swagger_auto_schema(method='post', request_body=UserSerializer)
@api_view(['POST'])
def sign_up(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        password = make_password(serializer.validated_data['password'])
        serializer.validated_data['password'] = password
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
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
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({'error': 'User with this email address does not exist.'}, status=status.HTTP_404_NOT_FOUND)

    temp_password = generate_temp_password()
    user.set_password(temp_password)
    user.save()

    send_temp_password_email(user, temp_password)

    return Response({'message': 'Temporary password has been sent to your email address.'}, status=status.HTTP_200_OK)
    
@login_required
@api_view(['DELETE'])
def delete_user(request):
    user = request.user
    user.delete()
    return JsonResponse({'message': 'User deleted successfully.'})

@swagger_auto_schema(method='post', request_body=UserProfileSerializer)
@api_view(['POST'])
def write_profile(request):
    serializer = UserProfileSerializer(data=request.data)
    if serializer.is_valid():
        image_file = request.FILES['user_img']
        url = S3ImgUploader(image_file).upload()
        user_profile = UserProfile.objects.create(
            user=User.objects.get(pk=request.data['user']),
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
    user_profile = UserProfile.objects.get(user=user)
    object_key = user_profile.user_image
    url = f'https://d3u19o4soz3vn3.cloudfront.net/img/{object_key}'

    response_data = {
        'user_id': user_id,
        'username': user.username,
        'user_img': url,
        'user_position': user_profile.user_position,
        'user_info': user_profile.user_info,
        'user_hash': user_profile.user_hash,
        'success_count': user_profile.success_count
    }
    return Response(response_data, status=status.HTTP_200_OK)

@swagger_auto_schema(method='patch', request_body=UserProfileSerializer)
@api_view(['PATCH'])
def edit_profile(request):
    user_profile = get_object_or_404(UserProfile, user=request.data.get('user'))
    serializer = UserProfileSerializer(user_profile, data=request.data, partial=True)
    if serializer.is_valid():
        if 'user_img' in request.data:
            url = S3ImgUploader(request.FILES['user_img'])
            serializer.user_img = url.upload()
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
