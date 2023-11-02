# urls.py 파일에 아래와 같이 추가합니다
from django.urls import path
from ..manda_views import views_todo

urlpatterns = [
    # 다른 URL 매핑들...
    path('view/', views_todo.todo_list_view, name='todo_list'),
    path('wirte/', views_todo.create_todo_view, name='create_todo'),
    path('detail/<int:id>/', views_todo.get_todo_detail_view, name='todo_detail'),
    path('updqte/<int:id>/', views_todo.update_todo_view, name='update_todo'),
    path('delete/<int:id>/', views_todo.delete_todo_view, name='delete_todo'),
]
