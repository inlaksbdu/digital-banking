from weasyprint import HTML
from PyPDF2 import PdfReader, PdfWriter
import io
import tempfile
from cbs.models import BankAccount, ExpenseLimit
from datatable.models import TransactionPurpose
from django.utils import timezone
from loguru import logger


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


def check_expense_limit(account_id, transaction_purpose, amount):
    print("=== checking expense limit ===")
    try:
        today = timezone.now().date()
        account = BankAccount.objects.get(id=account_id)
        purpose = TransactionPurpose.objects.get(name=transaction_purpose.strip())

        print("=== toda: ", today)
        print(account)
        print(purpose)

        # check account limit
        if account.expense_limits:
            expense_limit = account.expense_limits.filter(
                limit_type=ExpenseLimit.ExpenseLimitType.ACCOUNT_BUDGET,
                status=ExpenseLimit.Status.ACTIVE,
                start_date__lte=today,
                end_date__gte=today,
            )
            if expense_limit.exists():
                expense_limit = expense_limit.first()
                if expense_limit.amount_spent + amount > expense_limit.limit_amount:
                    return False

        # check limit for transaction puprose
        if account.expense_limits:
            expense_limit = account.expense_limits.filter(
                limit_type=ExpenseLimit.ExpenseLimitType.CATEGORICAL_BUDGET,
                category=purpose,
                status=ExpenseLimit.Status.ACTIVE,
                start_date__lte=today,
                end_date__gte=today,
            )
            if expense_limit.exists():
                expense_limit = expense_limit.first()
                if expense_limit.amount_spent + amount > expense_limit.limit_amount:
                    return False
    except Exception as e:
        print("=== error checking expense limit ===")
        logger.error(f"An error ocurred checking expense limit {str(e)}")
        return True
    print("== rerturning TRUEEEEE")
    return True


def get_absolute_profile_picture_url(request, relative_url):
    absolute_url = request.build_absolute_uri(relative_url)
    return absolute_url
