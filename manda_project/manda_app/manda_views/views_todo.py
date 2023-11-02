from rest_framework.response import Response
from rest_framework.decorators import api_view
from ..models import TodoList
from ..serializers.todo_serializer import TodoListSerializer
from ..serializers.todo_serializer import TodoListCreateSerializer
from rest_framework import status

#목록 보기 - 할일 리스트
@api_view(['GET'])
def todo_list_view(request):
    todo_list = TodoList.objects.all()
    serializer = TodoListSerializer(todo_list, many=True)
    return Response(serializer.data)

#할 일 추가
@api_view(['POST'])
def create_todo_view(request):
    serializer = TodoListCreateSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#할 일 상세 정보 보기
@api_view(['GET'])
def get_todo_detail_view(request, id):
    try:
        todo = TodoList.objects.get(id=id)
    except TodoList.DoesNotExist:
        return Response({"error": "TodoList does not exist"}, status=status.HTTP_404_NOT_FOUND)

    serializer = TodoListSerializer(todo)
    return Response(serializer.data, status=status.HTTP_200_OK)

#할 일 갱신
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

#삭제
@api_view(['DELETE'])
def delete_todo_view(request, id):
    try:
        todo = TodoList.objects.get(id=id)
    except TodoList.DoesNotExist:
        return Response({"error": "TodoList does not exist"}, status=status.HTTP_404_NOT_FOUND)

    todo.delete()
    return Response({"message": "TodoList deleted successfully"}, status=status.HTTP_204_NO_CONTENT)