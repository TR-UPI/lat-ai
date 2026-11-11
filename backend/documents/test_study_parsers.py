from importlib.util import find_spec
from io import BytesIO
from unittest import skipUnless
from unittest.mock import patch
from zipfile import ZipFile

from django.test import TestCase

from .test_study import BASE, StudyApiFixture


class ParserTests(StudyApiFixture, TestCase):
    def test_zip_guards_run_before_optional_parser(self):
        output = BytesIO()
        with ZipFile(output, 'w') as archive:
            archive.writestr('large.xml', 'A' * 1001)
        with patch('documents.study_extraction.MAX_ARCHIVE_BYTES', 1000), patch(
            'documents.study_extraction.docx_text'
        ) as parser:
            response = self.upload(output.getvalue(), 'large.docx')
        parser.assert_not_called()
        self.assertEqual(response.data['error'], 'unsafe_archive')

    @skipUnless(find_spec('pypdf'), 'optional PDF parser not installed')
    def test_pdf_text_scanned_and_encrypted(self):
        from pypdf import PdfWriter
        from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

        writer = PdfWriter()
        page = writer.add_blank_page(width=72, height=72)
        output = BytesIO()
        writer.write(output)
        scanned = self.upload(output.getvalue(), 'scanned.pdf')
        self.assertEqual(scanned.data['error'], 'empty_document')

        resources = DictionaryObject({
            NameObject('/Font'): DictionaryObject({
                NameObject('/F1'): DictionaryObject({
                    NameObject('/Type'): NameObject('/Font'),
                    NameObject('/Subtype'): NameObject('/Type1'),
                    NameObject('/BaseFont'): NameObject('/Helvetica'),
                }),
            }),
        })
        page[NameObject('/Resources')] = resources
        stream = DecodedStreamObject()
        stream.set_data(b'BT /F1 12 Tf 10 30 Td (A locally extracted PDF sentence.) Tj ET')
        page[NameObject('/Contents')] = stream
        output = BytesIO()
        writer.write(output)
        pdf = self.upload(output.getvalue(), 'ready.pdf')
        detail = self.client.get(BASE + f"{pdf.data['id']}/")
        self.assertIn('A locally extracted PDF sentence.', detail.data['extracted_text'])

        writer.encrypt('private-passphrase')
        output = BytesIO()
        writer.write(output)
        encrypted = self.upload(output.getvalue(), 'encrypted.pdf')
        self.assertEqual(encrypted.data['error'], 'encrypted_document')

    @skipUnless(find_spec('docx'), 'optional DOCX parser not installed')
    def test_docx_text_and_table(self):
        from docx import Document

        document = Document()
        document.add_paragraph('A paragraph.')
        document.add_table(rows=1, cols=1).cell(0, 0).text = 'A cell.'
        output = BytesIO()
        document.save(output)
        upload = self.upload(output.getvalue(), 'source.docx')
        self.assertEqual(upload.data['status'], 'ready')
        self.assertEqual(upload.data['text_length'], len('A paragraph.\nA cell.'))

    @skipUnless(find_spec('pptx'), 'optional PPTX parser not installed')
    def test_pptx_text(self):
        from pptx import Presentation

        document = Presentation()
        slide = document.slides.add_slide(document.slide_layouts[0])
        slide.shapes.title.text = 'A slide.'
        output = BytesIO()
        document.save(output)
        upload = self.upload(output.getvalue(), 'source.pptx')
        self.assertEqual(upload.data['status'], 'ready')
        self.assertEqual(upload.data['text_length'], len('A slide.'))
