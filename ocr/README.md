# OCR App - Django/DRF Implementation

This OCR app has been completely refactored to use Django and Django REST Framework patterns, removing all FastAPI/SQLAlchemy dependencies.

## Key Improvements Made

### 1. **Django/DRF Compatibility**
- ✅ Converted all FastAPI services to Django services
- ✅ Updated file handling to use Django's `InMemoryUploadedFile`
- ✅ Replaced SQLAlchemy patterns with Django ORM
- ✅ Added proper DRF serializers with comprehensive validation
- ✅ Implemented Django-style views with proper permissions

### 2. **Enhanced Validation**
- ✅ **Image validation**: File size, type, and dimension checks
- ✅ **Video validation**: Support for selfie videos with size/type validation
- ✅ **Age validation**: Ensures users are 18+ years old
- ✅ **Document validation**: Checks for expired documents
- ✅ **Cross-field validation**: Ensures required back images for certain document types
- ✅ **Data integrity**: Proper field length and format validation

### 3. **Better Django Patterns**
- ✅ **Proper caching**: Using Django's cache framework
- ✅ **Database optimization**: Select_related and prefetch_related queries
- ✅ **Transaction management**: Atomic transactions for data consistency
- ✅ **Signal handlers**: Automatic S3 cleanup on model deletion
- ✅ **Admin interface**: Comprehensive admin with actions and filters

### 4. **Enhanced Security & Performance**
- ✅ **Permission classes**: Proper authentication and authorization
- ✅ **File upload security**: Validated file types and sizes
- ✅ **Query optimization**: Efficient database queries
- ✅ **Error handling**: Comprehensive error handling and logging
- ✅ **Cache management**: Strategic caching for performance

### 5. **API Improvements**
- ✅ **Filtering & Search**: Advanced filtering with django-filter
- ✅ **Pagination**: Built-in DRF pagination support
- ✅ **Ordering**: Multiple field ordering options
- ✅ **Response formatting**: Consistent API response structure
- ✅ **Documentation**: Help text and field descriptions

## Models

### `IdCard`
- Stores OCR-extracted document information
- JSON fields for OCR data with confidence scores
- Computed properties for confidence scoring and validation
- Automatic text field extraction for searching

### `OnboardingStage`
- Tracks user progress through verification process
- Cached for performance
- Automatic stage progression

## API Endpoints

### User Endpoints
- `GET /onboarding/stage/` - Get current onboarding stage
- `POST /documents/upload/` - Upload and process documents
- `PUT /id-cards/{id}/confirm/` - Confirm extracted data
- `GET /id-cards/detail/` - Get user's ID card details

### Admin Endpoints
- `GET /admin/id-cards/` - List all ID cards with filtering
- `GET /admin/id-cards/low-confidence/` - Get low confidence cards

## Services

### `OnboardingService`
- Document type validation
- Expiry date checking
- ID card creation from verification results
- File validation utilities

### `VerificationService`
- ID Analyzer API integration
- Document verification processing
- Error handling and fallback responses

### `AWSService`
- **Concurrent S3 uploads**: Upload multiple files simultaneously using gevent
- **Flexible file handling**: Support for arbitrary file types and numbers
- **Legacy compatibility**: Backward compatible with existing ID card upload method
- Presigned URL generation
- File existence checking
- Automatic cleanup

## Validation Features

### Image Validation
- **Size limits**: 10MB for images, 50MB for videos
- **Format support**: JPEG, PNG, GIF, WebP for images; MP4, WebM, MOV, AVI for videos
- **Dimension checks**: Minimum 800x600 for document images
- **Quality assurance**: PIL-based image validation

### Data Validation
- **Age verification**: 18-120 years age range
- **Date validation**: Logical date constraints
- **Document requirements**: Back image required for certain document types
- **Field length validation**: Appropriate minimum lengths for IDs

### Business Logic Validation
- **Document expiry**: Automatic expiry date checking
- **Duplicate prevention**: Prevents multiple ID cards per user
- **Confidence scoring**: Automatic confidence calculation
- **Low confidence detection**: Identifies fields needing review

## Admin Features

### Enhanced Admin Interface
- **Visual indicators**: Color-coded confidence scores and status
- **Bulk actions**: Verify, approve, or reject multiple cards
- **Advanced filtering**: Filter by confidence, type, status, dates
- **Detailed views**: Comprehensive field display with computed values
- **Search functionality**: Search across user and document fields

### Admin Actions
- Mark cards as verified/unverified
- Approve or reject decisions
- View low confidence fields
- Access computed properties

## Dependencies

See `requirements.txt` for full dependency list. Key dependencies:
- Django 4.2+
- Django REST Framework 3.14+
- django-filter for advanced filtering
- Pillow for image processing
- boto3 for AWS S3 integration
- **gevent for concurrent file uploads**
- loguru for enhanced logging
- idanalyzer2 for document verification

## Configuration Required

### Django Settings
```python
# Add to INSTALLED_APPS
INSTALLED_APPS = [
    # ... other apps
    'rest_framework',
    'django_filters',
    'ocr',
]

# DRF Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# AWS Configuration
AWS_ACCESS_KEY_ID = 'your-access-key'
AWS_SECRET_ACCESS_KEY = 'your-secret-key'
AWS_S3_REGION_NAME = 'your-region'
AWS_S3_BUCKET_NAME = 'your-bucket-name'

# ID Analyzer Configuration
ID_ANALYZER_API_KEY = 'your-api-key'
```

### URL Configuration
```python
# In your main urls.py
urlpatterns = [
    # ... other patterns
    path('api/ocr/', include('ocr.urls')),
]
```

## Migration Notes

### Breaking Changes
- All FastAPI/SQLAlchemy code removed
- File handling now uses Django's file upload system
- API endpoints follow DRF conventions
- Response formats updated to DRF standards

### Data Migration
- Existing data should be compatible
- JSON field structure maintained
- New validation may require data cleanup

## Future Enhancements

### Recommended Improvements
1. **Database optimization**: Add computed confidence score field
2. **Background processing**: Use Celery for OCR processing
3. **Webhook support**: Add webhook notifications for verification results
4. **API versioning**: Implement API versioning for future changes
5. **Rate limiting**: Add rate limiting for API endpoints
6. **Audit logging**: Enhanced audit trail for admin actions

### Performance Optimizations
1. **Caching strategy**: Implement Redis for better caching
2. **Database indexing**: Add composite indexes for common queries
3. **File optimization**: Implement image compression
4. **CDN integration**: Use CloudFront for image delivery

## Concurrent File Upload

The AWS service now supports concurrent file uploads using gevent for improved performance:

### New Method: `upload_files_concurrently()`

```python
from ocr.services.aws import AWSService

aws_service = AWSService()

# Upload multiple arbitrary files concurrently
files = {
    'passport': passport_file,
    'utility_bill': bill_file,
    'contract': contract_file,
    'bank_statement': statement_file
}

urls = aws_service.upload_files_concurrently(
    user_id=user.pk,
    files=files,
    file_category="documents",  # Organizes files in S3
    max_workers=6  # Number of concurrent uploads
)

# Returns: {'passport': 's3://bucket/...', 'utility_bill': 's3://bucket/...', ...}
```

### Benefits

- **Concurrent uploads**: Multiple files uploaded simultaneously
- **Flexible**: Accept any number and type of files
- **Organized storage**: Files categorized in S3 by type and user
- **Error resilience**: Partial failures don't stop other uploads
- **Backward compatible**: Existing `upload_to_s3()` method still works

### Usage Examples

See `ocr/examples.py` for comprehensive usage examples including:
- ID card verification files
- Document uploads
- Profile documents
- Bulk file uploads
- Mixed file types (images, videos, PDFs)

### Performance Comparison

- **Sequential**: 4 files × 2 seconds each = 8 seconds total
- **Concurrent**: 4 files uploaded simultaneously ≈ 2-3 seconds total

The concurrent approach can reduce upload time by 60-75% for multiple files.

This refactored OCR app now follows Django best practices and provides a robust, scalable foundation for document verification workflows with high-performance file uploads. 