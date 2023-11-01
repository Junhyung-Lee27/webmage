from rest_framework import status
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from rest_framework.response import Response
from django.http import HttpResponse, JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from ..models import MandaMain, MandaSub, MandaContent, UserProfile
from ..serializers.manda_serializer import *
import json
from django.db.models import Q

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_view(request):
    search_query = request.GET.get('query', '')

    #### MandaSimple 부분
    # 1. MandaMain의 main_title에 포함될 경우
    # 2. User의 username에 포함될 경우
    combined_mandamains = MandaMain.objects.filter(
        Q(main_title__icontains=search_query) |
        Q(user__username__icontains=search_query)
    ).distinct().prefetch_related('mandasub_set')

    # 응답 데이터 준비
    manda_simples = []
    for mandamain in combined_mandamains:
        # 유저 정보 조회
        user = mandamain.user

        # 유저 프로필 조회
        try:
            userprofile = UserProfile.objects.get(user_id=user.id)
            userposition = userprofile.user_position
        except UserProfile.DoesNotExist:
            userposition = None
        
        main_entry = {
            'id': mandamain.id,
            'main_title': mandamain.main_title,
            'user_id': mandamain.user.id,
            'username': user.username,
            'userposition': userposition,
            'subs': []
        }
        
        for sub in mandamain.mandasub_set.all():
            sub_entry = {
                'id': sub.id,
                'success': sub.success,
                'sub_title': sub.sub_title
            }
            main_entry['subs'].append(sub_entry)

        manda_simples.append(main_entry)

    #### Feed 부분
    

    # 응답 반환
    results = [manda_simples, ]
    return Response(results, status=status.HTTP_200_OK)