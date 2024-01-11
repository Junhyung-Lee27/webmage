from rest_framework import serializers
from ..models import MandaMain, MandaSub, MandaContent

class MandaMainSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.id')
    class Meta:
        model = MandaMain
        fields = ('id', 'user', 'main_title', 'success', 'privacy')

    def validate_main_title(self, value):
        if len(value) > 50:
            raise serializers.ValidationError("핵심목표는 50글자 이하여야 합니다.")
        return value

class MandaContentSerializer(serializers.ModelSerializer):
    color_percentile = serializers.FloatField(read_only=True)

    class Meta:
        model = MandaContent
        fields = ('id', 'sub_id', 'success_count', 'content', 'color_percentile')

class MandaSubSerializer(serializers.ModelSerializer):
    content = MandaContentSerializer(many=True, read_only=True)
    color_percentile = serializers.FloatField(read_only=True)
    
    class Meta:
        model = MandaSub
        fields = ('id', 'main_id', 'success_count', 'sub_title', 'content', 'color_percentile')

class MandaMainViewSerializer(serializers.ModelSerializer):
    sub_instances = MandaSubSerializer(many=True, read_only=True)

    class Meta:
        model = MandaMain
        fields = ('id', 'user', 'success', 'main_title', 'sub_instances')

class MandaSubUpdateSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    sub_title = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    success_count = serializers.IntegerField(required=False)

    def validate_sub_title(self, value):
        if value is not None and len(value) > 50:
            raise serializers.ValidationError("세부 목표는 50글자 이하여야 합니다.")
        return value
    
class MandaContentUpdateSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    content = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    success_count = serializers.IntegerField(required=False)

    def validate_content(self, value):
        if value is not None and len(value) > 50:
          raise serializers.ValidationError("내용은 50글자 이하여야 합니다.")
        return value

manda_sub_update_schema = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "sub_title": {"type": "string"},
            "success_count": {"type": "integer"}
        },
        "required": ["id", "sub_title"]
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
        "required": ["id", "content"]
    }
}