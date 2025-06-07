from weasyprint import HTML
from PyPDF2 import PdfReader, PdfWriter
import io
import tempfile


def generate_pdf_from_html(html_content):
    # Use WeasyPrint to convert HTML to PDF
    html = HTML(string=html_content)
    pdf = html.write_pdf()
    return pdf


def encrypt_pdf(pdf_data, password):
    # Use a BytesIO buffer to treat the PDF as a file-like object
    pdf_buffer = io.BytesIO(pdf_data)

    # Create a PdfReader object from the BytesIO buffer
    reader = PdfReader(pdf_buffer)
    writer = PdfWriter()

    # Add all pages to the writer
    for page in reader.pages:
        writer.add_page(page)

    # Encrypt the PDF with the password
    output_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    writer.encrypt(password)

    # Write the encrypted PDF to the file
    with open(output_pdf.name, "wb") as output_file:
        writer.write(output_file)

    return output_pdf.name
