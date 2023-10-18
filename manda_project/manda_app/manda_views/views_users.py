from rest_framework import status
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from ..serializers.user_serializer import UserSerializer
from .utils import generate_temp_password, send_temp_password_email

@csrf_exempt
def user_login(request):
    if request.method == 'POST':
        data = JSONParser().parse(request)
        try:
            username = data['username']
            password = data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return HttpResponse(status=200)
            else:
                return HttpResponse(status=400)
        except KeyError:
            return HttpResponse(status=400)
    else:
        return HttpResponse(status=405)
    
@api_view(['POST'])
def user_logout(requet):
    logout(requet)
    return HttpResponse(status=200)

@api_view(['POST'])
def sign_up(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def user_edit(request):
    user = request.user
    serializer = UserSerializer(user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def reset_password(request):
    if request.method == 'POST':
        email = request.data.get('email')
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
def delete_user(request):
    user = request.user
    user.delete()
    return JsonResponse({'message': 'User deleted successfully.'})
