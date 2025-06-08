"""
Examples of using the concurrent file upload functionality
"""

from .services.aws import AWSService


def example_id_card_upload(user_id, front_image, back_image, selfie, selfie_video=None):
    """
    Example: Upload ID card verification files
    """
    aws_service = AWSService()

    # Using the legacy method (backward compatible)
    urls = aws_service.upload_to_s3(
        user_id=user_id,
        image_front=front_image,
        image_back=back_image,
        selfie=selfie,
        selfie_video=selfie_video,
    )

    return urls


def example_document_upload(user_id, documents_dict):
    """
    Example: Upload arbitrary documents concurrently

    Args:
        user_id: User identifier
        documents_dict: Dict like {
            'passport': passport_file,
            'utility_bill': bill_file,
            'bank_statement': statement_file,
            'contract': contract_file
        }
    """
    aws_service = AWSService()

    # Using the new concurrent method
    urls = aws_service.upload_files_concurrently(
        user_id=user_id,
        files=documents_dict,
        file_category="documents",
        max_workers=6,  # Upload up to 6 files concurrently
    )

    return urls


def example_profile_documents(user_id, profile_files):
    """
    Example: Upload user profile documents

    Args:
        user_id: User identifier
        profile_files: Dict like {
            'profile_picture': profile_pic,
            'resume': resume_file,
            'cover_letter': cover_letter,
            'portfolio': portfolio_file
        }
    """
    aws_service = AWSService()

    urls = aws_service.upload_files_concurrently(
        user_id=user_id, files=profile_files, file_category="profile", max_workers=4
    )

    return urls


def example_bulk_upload(user_id, file_list):
    """
    Example: Upload a large number of files

    Args:
        user_id: User identifier
        file_list: List of tuples like [('file_type', file_object), ...]
    """
    aws_service = AWSService()

    # Convert list to dict
    files_dict = {file_type: file_obj for file_type, file_obj in file_list}

    # Use higher concurrency for bulk uploads
    urls = aws_service.upload_files_concurrently(
        user_id=user_id,
        files=files_dict,
        file_category="bulk_upload",
        max_workers=10,  # Higher concurrency for bulk operations
    )

    return urls


def example_mixed_file_types(user_id, mixed_files):
    """
    Example: Upload mixed file types (images, videos, PDFs)

    Args:
        user_id: User identifier
        mixed_files: Dict like {
            'id_front': image_file,
            'id_back': image_file,
            'selfie_video': video_file,
            'signed_contract': pdf_file,
            'proof_document': pdf_file
        }
    """
    aws_service = AWSService()

    urls = aws_service.upload_files_concurrently(
        user_id=user_id, files=mixed_files, file_category="verification", max_workers=5
    )

    return urls


# Example usage in a Django view
"""
from django.views import View
from django.http import JsonResponse
from .examples import example_document_upload

class DocumentUploadView(View):
    def post(self, request):
        files = {
            'passport': request.FILES.get('passport'),
            'utility_bill': request.FILES.get('utility_bill'),
            'bank_statement': request.FILES.get('bank_statement'),
        }
        
        # Remove None values
        files = {k: v for k, v in files.items() if v is not None}
        
        if not files:
            return JsonResponse({'error': 'No files provided'}, status=400)
        
        try:
            urls = example_document_upload(request.user.pk, files)
            return JsonResponse({
                'status': 'success',
                'uploaded_files': urls
            })
        except Exception as e:
            return JsonResponse({
                'error': f'Upload failed: {str(e)}'
            }, status=500)
"""
