
import logging

from django.db import transaction

from .models import DocumentChunk
from .services import extract_text, split_text
from .embedding_service import generate_embeddings


def process_document(document):
    """Извлекает текст, создаёт фрагменты и embeddings документа."""

    document.status = "processing"
    document.save(update_fields=["status"])

    try:
        text = extract_text(document.file.path)
        chunks = split_text(text)

        if not chunks:
            raise ValueError(
                "В документе не найден текст."
            )

        embeddings = generate_embeddings(chunks)

        with transaction.atomic():
            DocumentChunk.objects.filter(
                document=document
            ).delete()

            DocumentChunk.objects.bulk_create([
                DocumentChunk(
                    document=document,
                    content=chunk,
                    chunk_index=index,
                    embedding=embeddings[index],
                )
                for index, chunk in enumerate(chunks)
            ])

            document.extracted_text = text
            document.status = "ready"
            document.save(
                update_fields=["extracted_text", "status"]
            )

        return True

    except Exception:
        logging.exception(
            "Document processing failed: %s",
            document.title
        )

        document.status = "failed"
        document.save(update_fields=["status"])

        return False
