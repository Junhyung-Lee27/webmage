from django.core.paginator import Paginator, EmptyPage
from django.db.models import Max
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
from gensim.models.doc2vec import Doc2Vec, TaggedDocument
import json
from konlpy.tag import Mecab

@swagger_auto_schema(method='post', request_body=MandaMainSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def manda_main_create(request):
    user = request.user
    serializer = MandaMainSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save(user=user)

        manda_main = MandaMain.objects.get(id=serializer.data['id'])
        manda_main.main_title_morphs = analyze_morphs(manda_main.main_title)
        manda_main.save()
        
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
            manda_main.main_title_morphs = analyze_morphs(manda_main.main_title)
            manda_main.save()
            serializer = MandaMainSerializer(manda_main)
            
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        if 'privacy' in request.data:
            main_id = request.data['id']
            new_privacy = request.data['privacy']

            try:
                manda_main = MandaMain.objects.get(pk=main_id, user=user)
            except MandaMain.DoesNotExist:
                return Response(f"MandaMain with ID {main_id} does not exist for the current user.", status=status.HTTP_404_NOT_FOUND)
            
            manda_main.privacy = new_privacy
            manda_main.save()

            return Response(status=status.HTTP_204_NO_CONTENT)
        
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
            manda_sub.sub_title_morphs = analyze_morphs(manda_sub.sub_title)
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

# success_count의 stage 계산 함수
def calculate_stage(success_count, max_success_count):
    if max_success_count == 0 or success_count == 0:
        return 0  # Default 0 to avoid division by zero
    ratio = success_count / max_success_count
    if ratio <= 0.2:
        return 1
    elif ratio <= 0.5:
        return 2
    elif ratio <= 0.8:
        return 3
    else:
        return 4

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

    # 요청자(request.user)의 권한 확인
    if manda_main.user == request.user:
        pass
    elif manda_main.user != request.user:
        if manda_main.privacy == 'public':
            pass
        elif manda_main.privacy == 'followers':
            if not Follow.objects.filter(following_user=manda_main.user, followed_user=request.user).exists():
                return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
        elif manda_main.privacy == 'private':
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

    # 2. MandaSub 객체 각각의 success_count 백분율 계산
    manda_sub_objects = MandaSub.objects.filter(main_id=manda_main)
    for sub in manda_sub_objects:
        sub_stage = calculate_stage(sub.success_count, manda_main.success_count)
        sub.success_stage = sub_stage

    manda_sub_serializer = MandaSubSerializer(manda_sub_objects, many=True)

    # 3. MandaContent 객체 각각의 success_count 백분율 계산
    manda_content_objects = MandaContent.objects.filter(sub_id__in=manda_sub_objects)
    for obj in manda_content_objects:
        obj_stage = calculate_stage(obj.success_count, obj.sub_id.success_count)
        obj.success_stage = obj_stage

    manda_content_serializer = MandaContentSerializer(manda_content_objects, many=True)

    response_data = {
        'main': manda_main_serializer.data,
        'subs': manda_sub_serializer.data,
        'contents': manda_content_serializer.data,
        'privacy': manda_main.privacy
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

# 형태소 분석 함수
def analyze_morphs(text):
    mecab = Mecab(r'C:\\mecab\\mecab-ko-dic')
    # 명사만 추출
    nouns = mecab.nouns(text)
    return ' '.join(nouns)

# TF-IDF 및 Cosine 유사도 계산 함수
def compute_cosine_similarity(input_text, documents):
    tfidf_vectorizer = TfidfVectorizer()
    tfidf_matrix = tfidf_vectorizer.fit_transform(documents)

    input_vec = tfidf_vectorizer.transform([input_text])
    cosine_similarities = cosine_similarity(input_vec, tfidf_matrix)[0]

    valid_similarity = 0.2 # 유효 유사도 값 설정
    valid_indexes_scores = [(i-1, score) for i, score in enumerate(cosine_similarities) if score >= valid_similarity]
    valid_indexes_scores.sort(key=lambda x: x[1], reverse=True)  # 점수에 따라 내림차순 정렬
    
    return valid_indexes_scores[1:11]

@api_view(['POST'])
def recommend_mandas(request):
    try:
        # 핵심 목표 또는 세부 목표 제목 확인
        input_data = json.loads(request.body)
        input_title = input_data.get('main_title') or input_data.get('sub_title')
        title_type = 'main_title' if 'main_title' in input_data else 'sub_title'

        # 새로 입력된 제목의 형태소 분석
        analyzed_input = analyze_morphs(input_title)

        # 핵심 목표 추천
        if title_type == 'main_title':
            current_user = request.user
            recent_mandas = MandaMain.objects.exclude(user=current_user).exclude(main_title__isnull=True).exclude(main_title='').order_by('-id')[:500]
            
            # 형태소 분석된 제목 가져오기
            documents = [manda.main_title_morphs for manda in recent_mandas]
            documents.insert(0, analyzed_input)

            # 유사도 계산 및 상위 10개 선택
            similar_indexes_scores = compute_cosine_similarity(analyzed_input, documents)

            # 결과 생성
            results = []
            for idx, score in similar_indexes_scores:
                manda = recent_mandas[idx]
                subs = MandaSub.objects.filter(main_id=manda)
                subs_data = subs.values('id', 'sub_title')
                results.append({
                    'main_id': manda.id,
                    'main_title': manda.main_title,
                    'sub_mandas': list(subs_data)
                })

        # 세부 목표 추천
        elif title_type == 'sub_title':
            current_user = request.user
            
            # 불필요한 세부 목표 제외
            user_main_mandas = MandaMain.objects.filter(user=current_user)
            user_sub_ids = MandaSub.objects.filter(main_id__in=user_main_mandas).values_list('id', flat=True)
            recent_sub_mandas = MandaSub.objects.exclude(id__in=user_sub_ids).exclude(sub_title__isnull=True).exclude(sub_title='').order_by('-id')[:500]

            # 형태소 분석된 제목 가져오기
            documents = [manda.sub_title_morphs for manda in recent_sub_mandas]
            documents.insert(0, analyzed_input)

            # 유사도 계산 및 상위 10개 선택
            similar_indexes_scores = compute_cosine_similarity(analyzed_input, documents)

            # 결과 생성
            results = []
            for idx, score in similar_indexes_scores:
                sub_manda = recent_sub_mandas[idx]
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