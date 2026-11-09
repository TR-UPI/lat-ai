from rest_framework import serializers
from .models import Document

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".txt"}
class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = (
        "id",
        "title",
        "file",
        "mime_type",
        "status",
        "created_at",
    )
        read_only_fields = (
        "id",
        "title",
        "mime_type",
        "status",
        "created_at",
    )
    def validate_file(self, value):
        import os
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise serializers.ValidationError("Поддерживаются только PDF, DOCX, PPTX и TXT.")
        if value.size > 20 * 1024 * 1024:
            raise serializers.ValidationError("Максимальный размер файла — 20 МБ.")
        return value
