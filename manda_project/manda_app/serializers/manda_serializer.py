from rest_framework import serializers
from ..models import MandaMain, MandaSub, MandaContent

class MandaMainSerializer(serializers.ModelSerializer):
    class Meta:
        model = MandaMain
        fields = ('id', 'user', 'main_title', 'success')

    def validate_main_title(self, value):
        if len(value) > 50:
            raise serializers.ValidationError("핵심목표는 50글자 이하여야 합니다.")
        return value

class MandaContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MandaContent
        fields = ('id', 'sub_id', 'success_count', 'content')

class MandaSubSerializer(serializers.ModelSerializer):
    content = MandaContentSerializer(many=True, read_only=True)
    
    class Meta:
        model = MandaSub
        fields = ('id', 'main_id', 'success', 'sub_title', 'content')

class MandaMainViewSerializer(serializers.ModelSerializer):
    sub_instances = MandaSubSerializer(many=True, read_only=True)

    class Meta:
        model = MandaMain
        fields = ('id', 'user', 'success', 'main_title', 'sub_instances')

class MandaSubUpdateSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    sub_title = serializers.CharField(allow_blank=True)

    def validate_sub_title(self, value):
        if len(value) > 50:
            raise serializers.ValidationError("세부 목표는 50글자 이하여야 합니다.")
        return value
    
class MandaContentUpdateSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    content = serializers.CharField(allow_blank=True)
    success_count = serializers.IntegerField()

    def validate_content(self, value):
        if len(value) > 50:
            raise serializers.ValidationError("내용은 50글자 이하여야 합니다.")
        return value

manda_sub_update_schema = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "sub_title": {"type": "string"},
            "success": {"type": "boolean"}
        },
        "required": ["id", "sub_title", "success"]
    }
}

manda_content_update_schema = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "content": {"type": "string"},
            "success_count": {"type": "integer"}
        },
        "required": ["id", "content", "success_count"]
    }
}