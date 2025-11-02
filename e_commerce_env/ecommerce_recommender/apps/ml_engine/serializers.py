from rest_framework import serializers
from .models import MLModel

class MLModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = MLModel
        fields = '__all__'
        read_only_fields = ['created_at']

class TrainingRequestSerializer(serializers.Serializer):
    model_type = serializers.ChoiceField(choices=['collaborative', 'content', 'hybrid'])
    parameters = serializers.JSONField(default=dict)