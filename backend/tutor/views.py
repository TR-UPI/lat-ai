from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from .serializers import TutorAskSerializer

class TutorAskView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = TutorAskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # AI/RAG integration is intentionally a stub at this stage.
        return Response({
            "detail": "Tutor API is connected. LLM/RAG service is not configured yet.",
            "mode": serializer.validated_data["mode"],
            "question": serializer.validated_data["question"],
            "answer": None,
        }, status=status.HTTP_501_NOT_IMPLEMENTED)
