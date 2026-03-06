from rest_framework import serializers
from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()
    uploaded_by_name = serializers.SerializerMethodField()
    shared_with_ids = serializers.SerializerMethodField()
    property_name = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            'id', 'title', 'description', 'document_type',
            'file_url', 'file_name', 'uploaded_by_name',
            'shared_with_ids', 'property_name', 'created_at',
        ]

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url if obj.file else None

    def get_file_name(self, obj):
        if obj.file:
            return obj.file.name.rsplit('/', 1)[-1]
        return None

    def get_uploaded_by_name(self, obj):
        u = obj.uploaded_by
        full = u.get_full_name()
        return full if full else u.username

    def get_shared_with_ids(self, obj):
        return list(obj.shared_with.values_list('id', flat=True))

    def get_property_name(self, obj):
        return obj.property.name if obj.property else None
