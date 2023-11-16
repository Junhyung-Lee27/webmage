from rest_framework import status
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from rest_framework.response import Response
from django.http import HttpResponse, JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from ..models import MandaMain, MandaSub, MandaContent, UserProfile
from ..serializers.manda_serializer import *
import json

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

@swagger_auto_schema(method='post', request_body=MandaMainSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def manda_main_create(request):
    user = request.user
    serializer = MandaMainSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save(user=user)
        
        manda_sub_objects = MandaSub.objects.filter(main_id=serializer.data['id'])
        manda_sub_serializer = MandaSubSerializer(manda_sub_objects, many=True)

        manda_content_objects = MandaContent.objects.filter(sub_id__in=manda_sub_objects)
        manda_content_serializer = MandaContentSerializer(manda_content_objects, many=True)

        response_data = {
            'main': serializer.data,
            'subs': manda_sub_serializer.data,
            'contents': manda_content_serializer.data
        }
        
        return Response(response_data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='patch',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "user": {"type": "integer"},
            "id": {"type": "integer"},
            "main_title": {"type": "string"},
            "success": {"type": "boolean"}
        }
    )
)
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_manda_main(request):
    user = request.user
    serializer = MandaMainSerializer(data=request.data, partial=True)

    if 'id' not in request.data:
        return Response(status=status.HTTP_400_BAD_REQUEST)

    if serializer.is_valid():
        if 'main_title' in request.data:
            main_id = request.data['id']
            main_title = serializer.validated_data['main_title']

            try:
                manda_main = MandaMain.objects.get(pk=main_id, user=user)
            except MandaMain.DoesNotExist:
                return Response(f"MandaMain with ID {main_id} does not exist for the current user.", status=status.HTTP_404_NOT_FOUND)

            if 'success' in request.data:
                new_success = request.data.get('success')
                manda_main.success = new_success

            manda_main.main_title = main_title
            manda_main.save()
            
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

"""
{
  "subs": [
    {"id": 1, "value": "new_value1"},
    {"id": 2, "value": "new_value2"},
    ...
    {"id": 8, "value": "new_value8"}
  ]
}
"""
@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "subs": manda_sub_update_schema
        },
        required=["subs"]
    )
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_manda_subs(request):
    user = request.user
    data = request.data

    serializer = MandaSubUpdateSerializer(data=data.get('subs', []), many=True)

    if serializer.is_valid():
        for sub_data in serializer.validated_data:
            sub_id = sub_data.get('id')
            new_value = sub_data.get('sub_title')

            try:
                manda_sub = MandaSub.objects.get(id=sub_id, main_id_id__user=user.id)
            except MandaSub.DoesNotExist:
                return Response(f"MandaSub with ID {sub_id} does not exist for the current user.", status=status.HTTP_404_NOT_FOUND)
            
            if 'success' in sub_data:
                new_success = sub_data.get('success')
                manda_sub.success = new_success

            manda_sub.sub_title = new_value
            manda_sub.save()

        return Response(serializer.data, status=status.HTTP_200_OK)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "contents": manda_content_update_schema
        },
        required=["contents"]
    )
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_manda_contents(request):
    user = request.user
    data = request.data

    serializer = MandaContentUpdateSerializer(data=data.get('contents', []), many=True)

    if serializer.is_valid():
        for content_data in serializer.validated_data:
            content_id = content_data.get('id')
            new_value = content_data.get('content')

            try:
                manda_content = MandaContent.objects.get(id=content_id, sub_id__main_id__user=user)
            except MandaContent.DoesNotExist:
                return Response(f"MandaContent with ID {content_id} does not exist for the current user.", status=status.HTTP_404_NOT_FOUND)

            if 'success_count' in content_data:
                new_success_count = content_data.get('success_count')
                manda_content.success_count = new_success_count

            manda_content.content = new_value
            manda_content.save()

        return Response(serializer.data, status=status.HTTP_200_OK)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    method='delete',
    manual_parameters=[
        openapi.Parameter('manda_id', openapi.IN_PATH, description='Manda ID', type=openapi.TYPE_INTEGER),
    ]
)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def manda_main_delete(request, manda_id):
    user = request.user
    manda_main = get_object_or_404(MandaMain, id=manda_id, user=user)
    manda_main.delete()
    return Response({'message': 'MandaMain deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)

@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter('manda_id', openapi.IN_PATH, description='Manda ID', type=openapi.TYPE_INTEGER),
    ]
)
@api_view(['GET'])
def select_mandalart(request, manda_id):
    manda_main = MandaMain.objects.get(id=manda_id)
    manda_main_serializer = MandaMainViewSerializer(manda_main)
    
    manda_sub_objects = MandaSub.objects.filter(main_id=manda_main)
    manda_sub_serializer = MandaSubSerializer(manda_sub_objects, many=True)

    manda_content_objects = MandaContent.objects.filter(sub_id__in=manda_sub_objects)
    manda_content_serializer = MandaContentSerializer(manda_content_objects, many=True)

    response_data = {
        'main': manda_main_serializer.data,
        'subs': manda_sub_serializer.data,
        'contents': manda_content_serializer.data
    }

    return Response(response_data, status=status.HTTP_200_OK)

@api_view(['GET'])
def manda_main_list(request, user_id):
    try:
        user = UserProfile.objects.get(pk=user_id)
    except user.DoesNotExist:
        return Response(f"해당 유저가 존재하지 않습니다.", status=status.HTTP_404_NOT_FOUND)
    manda_main_objects = MandaMain.objects.filter(user=user)
    serializer = MandaMainSerializer(manda_main_objects, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def others_manda_main_list(request):
    user = request.user

    manda_main = MandaMain.objects.exclude(user=user)
    manda_data = {}
    
    for main in manda_main:
        main_entry = {
            'id': main.id,
            'success': main.success,
            'main_title': main.main_title,
            'subs': []
        }
        
        manda_subs = MandaSub.objects.filter(main_id=main)
        for sub in manda_subs:
            sub_entry = {
                'id': sub.id,
                'success': sub.success,
                'sub_title': sub.sub_title
            }
            main_entry['subs'].append(sub_entry)

        user_id = main.user.id
        if user_id in manda_data:
            manda_data[user_id].append(main_entry)
        else:
            manda_data[user_id] = [main_entry]

    return Response(manda_data, status=status.HTTP_200_OK)

@api_view(['GET'])
def manda_main_sub(request, manda_id):
    manda_main = MandaMain.objects.get(pk=manda_id)
    
    main_entry = {
        'id': manda_main.id,
        'success': manda_main.success,
        'main_title': manda_main.main_title,
        'user_id': manda_main.user.id,
        'subs': []
    }
    
    manda_subs = MandaSub.objects.filter(main_id=manda_main)
    for sub in manda_subs:
        sub_entry = {
            'id': sub.id,
            'success': sub.success,
            'sub_title': sub.sub_title
        }
        main_entry['subs'].append(sub_entry)

    return Response(main_entry, status=status.HTTP_200_OK)