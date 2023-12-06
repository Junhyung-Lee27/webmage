from rest_framework import serializers
from ..models import Comment, UserProfile

class CommentSerializer(serializers.ModelSerializer):
    user_image = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'user', 'username', 'user_image', 'comment', 'created_at', 'updated_at', 'deleted_at']
        read_only_fields = ['id', 'user', 'username', 'user_image', 'created_at', 'updated_at', 'deleted_at']

    def get_user_image(self, obj):
        return obj.user.user_image

    def get_username(self, obj):
        return obj.user.username