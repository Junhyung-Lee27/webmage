from rest_framework import status
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from ..models import Feed, Comment  # You will need to create these models based on the API spec provided
from ..serializers.comment_serializer import CommentSerializer  # You will need to create these serializers
from ..serializers.feed_serializer import FeedSerializer
from drf_yasg.utils import swagger_auto_schema
from django.db.models import Count, Q

# Get feed of a specific user
@api_view(['GET'])
def return_feed(request, user_id):
    feed_objects = Feed.objects.filter(user=user_id)
    serializer = FeedSerializer(feed_objects, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

# Get feed logs for a specific user
@api_view(['GET'])
def return_feed_log(request, user_id):
    logs = Feed.objects.filter(user=user_id).values('created_at').annotate(feed_count=Count('id'))
    return Response(logs, status=status.HTTP_200_OK)

# Get the timeline for a specific user
@api_view(['GET'])
def return_timeline(request, user_id):
    # This might include the user's feed as well as feeds from their followers.
    # Placeholder logic is provided here. Adjust based on actual requirements.
    timeline_objects = Feed.objects.filter(Q(user_id=user_id) | Q(user__followers__id=user_id))
    serializer = FeedSerializer(timeline_objects, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

# Write a new feed
@swagger_auto_schema(method='post', request_body=FeedSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def write_feed(request):
    serializer = FeedSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Edit a specific feed
@swagger_auto_schema(method='patch', request_body=FeedSerializer)
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def edit_feed(request, feed_id):
    feed = get_object_or_404(Feed, id=feed_id)
    serializer = FeedSerializer(feed, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Set emoji on a feed
@api_view(['PATCH'])
def set_feed_emoji(request, feed_id):
    feed = get_object_or_404(Feed, id=feed_id)
    emoji_count = request.data.get('emoji_count', {})
    feed.emoji_count = emoji_count  # Assuming this is a JSONField
    feed.save()
    return Response({'message': 'Emoji updated successfully.'}, status=status.HTTP_200_OK)

# Comment on a feed
@api_view(['POST'])
def comment_on_feed(request, feed_id):
    feed = get_object_or_404(Feed, id=feed_id)
    serializer = CommentSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(feed=feed)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Edit a comment
@api_view(['PATCH'])
def edit_comment(request, feed_id, comment_id):
    comment = get_object_or_404(Comment, id=comment_id, feed_id=feed_id)
    serializer = CommentSerializer(comment, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

