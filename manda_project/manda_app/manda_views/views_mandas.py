from django.core.paginator import Paginator, EmptyPage
from django.contrib.auth.models import User
from django.db.models import Max, Q
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from ..models import MandaMain, MandaSub, MandaContent, UserProfile, BlockedUser, Follow
from ..serializers.manda_serializer import *
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json

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
    method='post',
    manual_parameters=[
        openapi.Parameter('manda_id', openapi.IN_PATH, description='Manda ID', type=openapi.TYPE_INTEGER),
    ]
)
@api_view(['POST'])
def manda_main_delete(request, manda_id):
    user = request.user
    manda_main = get_object_or_404(MandaMain, id=manda_id, user=user)

    manda_main.deleted_at = timezone.now()
    manda_main.save()

    return Response({'message': 'MandaMain soft deleted successfully.'}, status=status.HTTP_200_OK)

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

    # 1. MandaSub와 MandaContent의 success_count 최대값을 구함
    max_success_count_sub = MandaSub.objects.aggregate(Max('success_count'))['success_count__max'] or 0
    max_success_count_content = MandaContent.objects.aggregate(Max('success_count'))['success_count__max'] or 0
    max_success_count = max(max_success_count_sub, max_success_count_content)

    # 2. MandaSub 객체 각각의 success_count 백분율 계산
    manda_sub_objects = MandaSub.objects.filter(main_id=manda_main)
    for subs in manda_sub_objects:
        percentile = subs.success_count / max_success_count if max_success_count else 0
        subs.color_percentile = round(percentile * 100, 2)
    manda_sub_serializer = MandaSubSerializer(manda_sub_objects, many=True)

    # 3. MandaContent 객체 각각의 success_count 백분율 계산
    manda_content_objects = MandaContent.objects.filter(sub_id__in=manda_sub_objects)
    for obj in manda_content_objects:
        percentile = obj.success_count / max_success_count if max_success_count else 0
        obj.color_percentile = round(percentile * 100, 2)
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
    manda_main_objects = MandaMain.objects.filter(user=user, deleted_at__isnull=True)
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

@api_view(['GET'])
def search_sub_mandas(request):
    search_keyword = request.GET.get('keyword', '')
    current_user = request.user

    # 제외할 만다라트 목록
    blocked_users_list = BlockedUser.objects.filter(blocker=current_user).values_list('blocked_id', flat=True)
    inactive_users_list = UserProfile.objects.filter(is_active=False).values_list('id', flat=True)
    excluded_user_ids = set([current_user.id] + list(blocked_users_list) + list(inactive_users_list))
    
    # 최종 쿼리
    combined_mandamains = MandaMain.objects.exclude(user_id__in=excluded_user_ids).filter(
        main_title__icontains=search_keyword
    ).prefetch_related('mandasub_set')[:20]

    # 페이지네이션 적용
    default_page = 1
    page = int(request.GET.get('page', default_page))
    page_size = 4
    paginator = Paginator(combined_mandamains, page_size)

    try:
        searched_mandamains = paginator.page(page)
    except EmptyPage:
        return Response({'message': 'No more pages', 'data': []}, status=status.HTTP_200_OK)

    # 데이터 구조화
    manda_simples = []
    for mandamain in searched_mandamains:
        user = mandamain.user

        is_following = Follow.objects.filter(
            followed_user=user, following_user=current_user
        ).exists()

        main_entry = {
            'id': mandamain.id,
            'userId': user.id,
            'username': user.username,
            'userPosition': user.user_position,
            'userHash': user.user_hash,
            'userInfo': user.user_info,
            'is_following': is_following,
            'mainTitle': mandamain.main_title,
            'subs': [{'id': sub.id, 'successCount': sub.success_count, 'subTitle': sub.sub_title} for sub in mandamain.mandasub_set.all()]
        }
        manda_simples.append(main_entry)

    return Response(manda_simples, status=status.HTTP_200_OK)

# 유사한 핵심목표 찾는 함수
def find_similar_mandas(input_title, all_mandas, title_field_name, similarity_threshold=0.3):
    if input_title is None:
        return []
    
    # TF-IDF 벡터라이저 초기화 및 학습
    vectorizer = TfidfVectorizer()
    valid_titles = [title for title in [getattr(manda, title_field_name) for manda in all_mandas] if title and title.strip()]
    tfidf_matrix = vectorizer.fit_transform([input_title] + valid_titles)

    # 입력된 제목과 다른 제목들 간의 코사인 유사도 계산
    cosine_similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()

    # 유사도가 가장 높은 상위 10개 인덱스 추출
    similar_indices = cosine_similarities.argsort()[:-11:-1]

    # 유사도 임계값 이상인 객체 필터링
    filtered_indices = [idx for idx in similar_indices if cosine_similarities[idx] > similarity_threshold]
    converted_similar_indices = [int(idx) for idx in filtered_indices]

    # 유사한 객체 반환 (None이거나 공백인 제목을 가진 객체 제외)
    return [all_mandas[i] for i in converted_similar_indices if all_mandas[i] and getattr(all_mandas[i], title_field_name) and getattr(all_mandas[i], title_field_name).strip()]

@api_view(['POST'])
def recommend_mandas(request):
    try:
        input_data = json.loads(request.body)
        # 핵심 목표 또는 세부 목표 제목 확인
        input_title = input_data.get('main_title') or input_data.get('sub_title')
        title_type = 'main_title' if 'main_title' in input_data else 'sub_title'

        # 핵심 목표 추천
        if title_type == 'main_title':
            current_user = request.user
            recent_mandas = MandaMain.objects.exclude(user=current_user).order_by('-id')[:500]
            similar_mandas = find_similar_mandas(input_title, recent_mandas, title_type)

            results = []
            for manda in similar_mandas:
                subs = MandaSub.objects.filter(main_id=manda)
                subs_data = subs.values('id', 'sub_title')
                results.append({
                    'main_id': manda.id,
                    'main_title': manda.main_title,
                    'sub_mandas': list(subs_data)
                })

        # 세부 목표 추천
        elif title_type == 'sub_title':
            requested_sub_id = input_data.get('sub_id')
            recent_sub_mandas = MandaSub.objects.exclude(id=requested_sub_id).order_by('-id')[:500]
            similar_sub_mandas = find_similar_mandas(input_title, recent_sub_mandas, title_type)

            results = []
            for sub_manda in similar_sub_mandas:
                contents = MandaContent.objects.filter(sub_id=sub_manda)
                content_data = contents.values('id', 'content')
                results.append({
                    'sub_id': sub_manda.id,
                    'sub_title': sub_manda.sub_title,
                    'contents': list(content_data)
                })

        return Response(results, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

