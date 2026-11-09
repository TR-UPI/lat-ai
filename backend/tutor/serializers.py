from rest_framework import serializers

class TutorAskSerializer(serializers.Serializer):
    question = serializers.CharField(min_length=1, max_length=2000)
    mode = serializers.ChoiceField(choices=("internal", "personal"), default="internal")
    document_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
