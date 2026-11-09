
from pathlib import Path
import fitz
from docx import Document as DocxDocument
from pptx import Presentation


def extract_text(file_path: str) -> str:
    path = Path(file_path)
    extension = path.suffix.lower()

    if extension == ".pdf":
        with fitz.open(path) as pdf:
            return "\n".join(
                page.get_text() for page in pdf
            )

    elif extension == ".docx":
        document = DocxDocument(path)
        return "\n".join(
            paragraph.text
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        )

    elif extension == ".pptx":
        presentation = Presentation(path)
        slides_text = []

        for slide in presentation.slides:
            for shape in slide.shapes:
                if shape.has_text_frame:
                    slides_text.append(shape.text)

        return "\n".join(slides_text)

    elif extension == ".txt":
        return path.read_text(encoding="utf-8-sig")

    raise ValueError("Неподдерживаемый формат файла")

def split_text(text, chunk_size=1000, overlap=150):
    text = text.strip()

    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        # Стараемся не разрывать предложения
        if end < len(text):
            boundary = text.rfind(". ", start, end)

            if boundary > start + chunk_size // 2:
                end = boundary + 1

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = max(end - overlap, start + 1)

    return chunks