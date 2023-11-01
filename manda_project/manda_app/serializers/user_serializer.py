from rest_framework import serializers
from django.contrib.auth.models import User
from ..models import UserProfile
from django.core.validators import MaxLengthValidator

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'email', 'password')
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
    user_img = serializers.ImageField(max_length=None, use_url=True, write_only=True)
    user_position = serializers.CharField(validators=[validate_max_length])
    user_info = serializers.CharField(validators=[validate_max_length2])
    user_hash = serializers.CharField(validators=[validate_max_length])
    success_count = serializers.IntegerField()

    class Meta:
        model = UserProfile
        fields = ('user', 'user_img', 'user_position', 'user_info', 'user_hash', 'success_count')
