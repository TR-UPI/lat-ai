


from rest_framework import serializers

from courses.models import Exercise
from .models import LessonProgress, ExerciseAttempt


class LessonProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonProgress
        fields = (
            "id",
            "lesson",
            "completed",
            "score",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "lesson",
            "completed",
            "score",
            "updated_at",
        )


class ExerciseAttemptSerializer(serializers.ModelSerializer):
    exercise = serializers.PrimaryKeyRelatedField(
        queryset=Exercise.objects.filter(
            is_published=True,
            lesson__course__is_published=True,
        )
    )

    class Meta:
        model = ExerciseAttempt
        fields = (
            "id",
            "exercise",
            "answer",
            "score",
            "feedback",
            "status",
            "submitted_at",
        )
        read_only_fields = (
            "id",
            "score",
            "feedback",
            "status",
            "submitted_at",
        )


class ExerciseAttemptReviewSerializer(serializers.ModelSerializer):
    score = serializers.FloatField(
        min_value=0,
        required=True
    )

    feedback = serializers.CharField(
        required=False,
        allow_blank=True
    )

    class Meta:
        model = ExerciseAttempt
        fields = ("score", "feedback")

    def validate_score(self, value):
        if value > self.instance.exercise.max_score:
            raise serializers.ValidationError(
                "Оценка не может превышать максимальный балл."
            )
        return value
