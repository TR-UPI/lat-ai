"""Bounded local text extraction for the document pilot."""
from pathlib import PurePath
from zipfile import ZipFile

MAX_UPLOAD = 20 * 1024 * 1024
MAX_TEXT = 200_000
MAX_ARCHIVE_MEMBERS = 2_048
MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MIME_TYPES = {
    '.txt': 'text/plain',
    '.pdf': 'application/pdf',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
}


class ExtractionError(ValueError):
    pass


def check_archive(upload):
    with ZipFile(upload) as archive:
        entries = archive.infolist()
        if len(entries) > MAX_ARCHIVE_MEMBERS or sum(entry.file_size for entry in entries) > MAX_ARCHIVE_BYTES:
            raise ExtractionError('unsafe_archive')
        if any(entry.flag_bits & 1 for entry in entries):
            raise ExtractionError('encrypted_document')
    upload.seek(0)


def pdf_text(upload):
    from pypdf import PdfReader, apply_configuration
    from pypdf.errors import LimitReachedError

    stream_limit = 8 * 1024 * 1024
    try:
        with apply_configuration(
            page_tree_maximum_entries=2_000,
            page_tree_maximum_depth=40,
            maximum_declared_stream_length=stream_limit,
            array_based_stream_maximum_output_length=stream_limit,
            zlib_maximum_output_length=stream_limit,
            lzw_maximum_output_length=stream_limit,
            run_length_maximum_output_length=stream_limit,
            brotli_maximum_output_length=stream_limit,
            stream_decoding_work_maximum_length=4 * stream_limit,
            stream_parsing_work_maximum_count=200_000,
        ):
            reader = PdfReader(upload, root_object_recovery_limit=1_000)
            if reader.is_encrypted:
                raise ExtractionError('encrypted_document')
            if len(reader.pages) > 1_000:
                raise ExtractionError('unsafe_pdf')
            for page in reader.pages:
                yield page.extract_text()
    except LimitReachedError:
        raise ExtractionError('unsafe_pdf') from None


def docx_text(upload):
    from docx import Document

    document = Document(upload)
    for paragraph in document.paragraphs:
        yield paragraph.text
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                yield cell.text


def slide_shape_text(shapes):
    for shape in shapes:
        if shape.has_text_frame:
            yield shape.text
        elif shape.has_table:
            for cell in shape.table.iter_cells():
                yield cell.text
        elif hasattr(shape, 'shapes'):
            yield from slide_shape_text(shape.shapes)


def pptx_text(upload):
    from pptx import Presentation

    for slide in Presentation(upload).slides:
        yield from slide_shape_text(slide.shapes)


def bounded_join(parts):
    kept = []
    length = 0
    for part in parts:
        if not part:
            continue
        length += len(part) + bool(kept)
        if length > MAX_TEXT:
            raise ExtractionError('text_too_large')
        kept.append(part)
    text = '\n'.join(kept)
    if not text.strip():
        raise ExtractionError('empty_document')
    if '\x00' in text:
        raise ExtractionError('invalid_document')
    return text


def extract_upload(upload):
    extension = PurePath(upload.name).suffix.lower()
    try:
        if extension == '.txt':
            # Four UTF-8 bytes per code point and a possible BOM.
            limit = 4 * MAX_TEXT + 3
            raw = upload.read(limit + 1)
            if len(raw) > limit:
                raise ExtractionError('text_too_large')
            return bounded_join([raw.decode('utf-8-sig')])
        if extension in ('.docx', '.pptx'):
            check_archive(upload)
        parser = {'.pdf': pdf_text, '.docx': docx_text, '.pptx': pptx_text}[extension]
        return bounded_join(parser(upload))
    except UnicodeDecodeError:
        raise ExtractionError('invalid_utf8') from None
    except ImportError:
        raise ExtractionError('parser_unavailable') from None
    except ExtractionError:
        raise
    except Exception:
        # Third-party parser messages can include text and filesystem paths.
        raise ExtractionError('invalid_document') from None
    finally:
        upload.seek(0)
