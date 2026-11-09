
from rest_framework import serializers
from .models import Course, Lesson, Exercise


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = (
            "id",
            "course",
            "title",
            "content",
            "order",
        )


class CourseSerializer(serializers.ModelSerializer):
    lessons_count = serializers.IntegerField(
        source="lessons.count",
        read_only=True
    )

    class Meta:
        model = Course
        fields = (
            "id",
            "title",
            "description",
            "subject",
            "is_published",
            "lessons_count",
        )


class ExerciseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exercise
        fields = (
            "id",
            "lesson",
            "title",
            "description",
            "task_type",
            "order",
            "max_score",
        )
