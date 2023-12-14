from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from ..models import Notification, UserProfile

@api_view(['GET'])
def get_notifications(request, user_id):
    notifications = Notification.objects.filter(recipient_id=user_id).order_by('-created_at')[:30]

    # 데이터 구조화
    response_data = []

    for notif in notifications:

        # 공통 데이터
        notif_data = {
            'user_image': notif.sender.user_image,
            'user_id': notif.sender.id,
            'username': notif.sender.username,
            'created_at': notif.created_at,
            'is_read' : notif.is_read,
            'type' : notif.notification_type,
            'noti_id' : notif.id,
            'feed_id' : notif.feed.id if notif.feed else None
        }

        # 알림 유형에 따른 추가 데이터
        if notif.notification_type == 'comment':
            notif_data['comment'] = notif.comment
        elif notif.notification_type == 'reaction':
            notif_data['total_count'] = notif.total_count

        response_data.append(notif_data)

    return Response(response_data, status=status.HTTP_200_OK)

@api_view(['PATCH'])
def read_notification(request, noti_id):
    try:
        notification = Notification.objects.get(id=noti_id, recipient=request.user)
        notification.is_read = True
        notification.save()

        return Response({'message': 'Notification is read successfully'}, status=status.HTTP_200_OK)

    except Notification.DoesNotExist:
        return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)