# ── ADD TO BOTTOM of ScriptNova/serilaizer.py ────────────────────────────────
# Keep all your existing serializers above, just append these two classes

from rest_framework import serializers
from ScriptNova.models import Blog


class BlogSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = Blog
        fields = [
            'id', 'user', 'title', 'content', 'keywords',
            'tone', 'length_preference', 'status',
            'word_count', 'slug', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'user', 'slug', 'created_at', 'updated_at']

    def get_user(self, obj):
        return obj.user.username if obj.user else None


class BlogListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list view — omits full content for speed."""
    class Meta:
        model = Blog
        fields = [
            'id', 'title', 'keywords', 'tone',
            'status', 'word_count', 'slug',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']