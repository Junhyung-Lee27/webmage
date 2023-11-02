from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from ..models import TodoList
from ..serializers.todo_serializer import TodoListSerializer
from ..serializers.todo_serializer import TodoListCreateSerializer
from rest_framework import status

from rest_framework.decorators import api_view
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


# 목록 보기 - 할일 리스트
@swagger_auto_schema(method='get', responses={200: TodoListSerializer(many=True)})
@api_view(['GET'])
def todo_list_view(request):
    todo_list = TodoList.objects.all()
    serializer = TodoListSerializer(todo_list, many=True)
    return Response(serializer.data)

# 할 일 추가
@swagger_auto_schema(method='post', request_body=TodoListCreateSerializer, responses={201: TodoListCreateSerializer})
@api_view(['POST'])
def create_todo_view(request):
    serializer = TodoListCreateSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 할 일 상세 정보 보기
@swagger_auto_schema(method='get', responses={200: TodoListSerializer})
@api_view(['GET'])
def get_todo_detail_view(request, id):
    try:
        todo = TodoList.objects.get(id=id)
    except TodoList.DoesNotExist:
        return Response({"error": "TodoList does not exist"}, status=status.HTTP_404_NOT_FOUND)

    serializer = TodoListSerializer(todo)
    return Response(serializer.data, status=status.HTTP_200_OK)

# 할 일 갱신
@swagger_auto_schema(method='put', request_body=TodoListSerializer, responses={200: TodoListSerializer})
@swagger_auto_schema(method='patch', request_body=TodoListSerializer, responses={200: TodoListSerializer})
@api_view(['PUT', 'PATCH'])
def update_todo_view(request, id):
    try:
        todo = TodoList.objects.get(id=id)
    except TodoList.DoesNotExist:
        return Response({"error": "TodoList does not exist"}, status=status.HTTP_404_NOT_FOUND)

    serializer = TodoListSerializer(todo, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 삭제
@swagger_auto_schema(method='delete')
@api_view(['DELETE'])
def delete_todo_view(request, id):
    try:
        todo = TodoList.objects.get(id=id)
    except TodoList.DoesNotExist:
        return Response({"error": "TodoList does not exist"}, status=status.HTTP_404_NOT_FOUND)

    todo.delete()
    return Response({"message": "TodoList deleted successfully"}, status=status.HTTP_204_NO_CONTENT)