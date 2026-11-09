
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response

from pgvector.django import CosineDistance

from .models import Document, DocumentChunk
from .serializers import DocumentSerializer
from .embedding_service import generate_query_embedding
from .processing import process_document


class DocumentListCreateView(generics.ListCreateAPIView):
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Document.objects.filter(
            owner=self.request.user
        ).order_by("-created_at")

    def perform_create(self, serializer):
        uploaded = self.request.FILES["file"]

        document = serializer.save(
            owner=self.request.user,
            title=uploaded.name,
            mime_type=getattr(uploaded, "content_type", ""),
            status="processing",
        )

        process_document(document)


class DocumentDeleteView(generics.DestroyAPIView):
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Document.objects.filter(
            owner=self.request.user
        )


class DocumentSearchView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        query = request.data.get("query", "").strip()

        if not query:
            return Response(
                {"error": "Введите поисковый запрос"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(query) > 1000:
            return Response(
                {"error": "Запрос слишком длинный"},
                status=status.HTTP_400_BAD_REQUEST
            )

        vector = generate_query_embedding(query)

        chunks = (
            DocumentChunk.objects
            .filter(
                document__owner=request.user,
                document__status="ready",
                embedding__isnull=False
            )
            .annotate(
                distance=CosineDistance("embedding", vector)
            )
            .order_by("distance")[:5]
        )

        results = [
            {
                "document_id": chunk.document_id,
                "document_title": chunk.document.title,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "distance": round(chunk.distance, 4)
            }
            for chunk in chunks
        ]

        return Response({
            "query": query,
            "results": results
        })
