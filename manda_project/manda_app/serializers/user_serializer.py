from rest_framework import serializers
from django.contrib.auth.models import User
from ..models import UserProfile
from django.core.validators import MaxLengthValidator

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ('username', 'email', 'password', 'provider')
        extra_kwargs = {'password': {'write_only': True}}

class UserAuthenticationSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

def validate_max_length(value):
    max_length = 50
    if len(value) > max_length:
        raise serializers.ValidationError(f'{max_length} characters long.')
    return value

def validate_max_length2(value):
    max_length = 200
    if len(value) > max_length:
        raise serializers.ValidationError(f'{max_length} characters long.')
    return value

class UserProfileSerializer(serializers.ModelSerializer):
    user_image = serializers.CharField(required=False, allow_blank=True)
    user_position = serializers.CharField(validators=[validate_max_length])
    user_info = serializers.CharField(validators=[validate_max_length2])
    user_hash = serializers.CharField(validators=[validate_max_length])
    success_count = serializers.IntegerField()

    class Meta:
        model = UserProfile
        fields = ('user_image', 'user_position', 'user_info', 'user_hash', 'success_count')
