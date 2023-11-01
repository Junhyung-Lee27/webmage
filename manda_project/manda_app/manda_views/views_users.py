from rest_framework import status
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
from ..serializers.user_serializer import UserSerializer, UserAuthenticationSerializer
from .utils import generate_temp_password, send_temp_password_email

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
@permission_classes([IsAuthenticated])
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
    user.delete()
    return JsonResponse({'message': 'User deleted successfully.'})