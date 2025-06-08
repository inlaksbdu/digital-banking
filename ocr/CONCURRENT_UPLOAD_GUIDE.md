# Concurrent File Upload Guide

This guide explains how to use the enhanced AWS service with concurrent file upload capabilities.

## Overview

The `AWSService` now supports uploading multiple files concurrently using gevent, significantly improving performance for bulk file operations.

## Key Features

- **Concurrent uploads**: Multiple files uploaded simultaneously
- **Flexible file handling**: Support for any file type and number
- **Error resilience**: Partial failures don't stop other uploads
- **Backward compatibility**: Existing code continues to work
- **Organized storage**: Files are categorized in S3 by type and user

## API Reference

### `upload_files_concurrently()`

```python
def upload_files_concurrently(
    self,
    user_id: Any,
    files: Dict[str, Optional[InMemoryUploadedFile]],
    file_category: str = "general",
    bucket_name: Optional[str] = None,
    max_workers: int = 5,
) -> Dict[str, str]:
```

**Parameters:**
- `user_id`: User identifier for organizing files in S3
- `files`: Dictionary mapping file types to file objects
- `file_category`: Category for S3 organization (e.g., "documents", "id_cards")
- `bucket_name`: S3 bucket name (optional, uses default if not provided)
- `max_workers`: Maximum number of concurrent uploads (default: 5)

**Returns:**
- Dictionary mapping file types to S3 URLs for successfully uploaded files

## Usage Examples

### Basic Document Upload

```python
from ocr.services.aws import AWSService

aws_service = AWSService()

# Prepare files
files = {
    'passport': request.FILES.get('passport'),
    'utility_bill': request.FILES.get('utility_bill'),
    'bank_statement': request.FILES.get('bank_statement'),
    'contract': request.FILES.get('contract')
}

# Remove None values
files = {k: v for k, v in files.items() if v is not None}

# Upload concurrently
urls = aws_service.upload_files_concurrently(
    user_id=request.user.pk,
    files=files,
    file_category="kyc_documents",
    max_workers=4
)

# Result: {'passport': 's3://bucket/...', 'utility_bill': 's3://bucket/...', ...}
```

### ID Card Verification (Backward Compatible)

```python
# Legacy method still works
urls = aws_service.upload_to_s3(
    user_id=user.pk,
    image_front=front_image,
    image_back=back_image,
    selfie=selfie_image,
    selfie_video=selfie_video  # Optional
)

# Internally uses concurrent upload with 4 workers
```

### Profile Documents

```python
profile_files = {
    'profile_picture': profile_pic,
    'resume': resume_file,
    'cover_letter': cover_letter_file,
    'portfolio': portfolio_file
}

urls = aws_service.upload_files_concurrently(
    user_id=user.pk,
    files=profile_files,
    file_category="profile",
    max_workers=3
)
```

### Bulk Upload

```python
# For many files, use higher concurrency
bulk_files = {
    f'document_{i}': file_obj 
    for i, file_obj in enumerate(document_list)
}

urls = aws_service.upload_files_concurrently(
    user_id=user.pk,
    files=bulk_files,
    file_category="bulk_documents",
    max_workers=10  # Higher concurrency for bulk operations
)
```

## Performance Considerations

### Concurrency Levels

- **1-3 files**: Use 2-3 workers
- **4-10 files**: Use 4-6 workers  
- **10+ files**: Use 6-10 workers
- **Very large batches**: Consider splitting into smaller groups

### File Size Impact

- **Small files (< 1MB)**: Higher concurrency is beneficial
- **Large files (> 10MB)**: Lower concurrency to avoid overwhelming bandwidth
- **Mixed sizes**: Use moderate concurrency (4-6 workers)

### Example Performance

Sequential vs Concurrent upload times:

| Files | Sequential | Concurrent (4 workers) | Improvement |
|-------|------------|-------------------------|-------------|
| 2 files | 4 seconds | 2 seconds | 50% |
| 4 files | 8 seconds | 2.5 seconds | 69% |
| 8 files | 16 seconds | 4 seconds | 75% |
| 16 files | 32 seconds | 8 seconds | 75% |

## Error Handling

The concurrent upload handles errors gracefully:

```python
try:
    urls = aws_service.upload_files_concurrently(
        user_id=user.pk,
        files=files,
        file_category="documents"
    )
    
    if len(urls) < len(files):
        # Some uploads failed - check logs
        failed_files = set(files.keys()) - set(urls.keys())
        print(f"Failed uploads: {failed_files}")
    
except Exception as e:
    # Critical error occurred
    print(f"Upload failed: {e}")
```

## S3 Organization

Files are organized in S3 as follows:

```
bucket/
├── id_cards/
│   └── user_123/
│       ├── front/
│       │   └── abc123hash.jpg
│       ├── back/
│       │   └── def456hash.jpg
│       └── selfie/
│           └── ghi789hash.jpg
├── documents/
│   └── user_123/
│       ├── passport/
│       │   └── jkl012hash.pdf
│       └── utility_bill/
│           └── mno345hash.jpg
└── profile/
    └── user_123/
        ├── profile_picture/
        │   └── pqr678hash.png
        └── resume/
            └── stu901hash.pdf
```

## Django Integration

### In Views

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from ocr.services.aws import AWSService

class DocumentUploadView(APIView):
    def post(self, request):
        aws_service = AWSService()
        
        # Extract files from request
        files = {
            'passport': request.FILES.get('passport'),
            'utility_bill': request.FILES.get('utility_bill'),
            'bank_statement': request.FILES.get('bank_statement'),
        }
        
        # Filter out None values
        files = {k: v for k, v in files.items() if v is not None}
        
        if not files:
            return Response({'error': 'No files provided'}, status=400)
        
        try:
            urls = aws_service.upload_files_concurrently(
                user_id=request.user.pk,
                files=files,
                file_category="verification_documents",
                max_workers=len(files)  # One worker per file
            )
            
            return Response({
                'status': 'success',
                'uploaded_files': urls,
                'uploaded_count': len(urls),
                'total_files': len(files)
            })
            
        except Exception as e:
            return Response({
                'error': f'Upload failed: {str(e)}'
            }, status=500)
```

### In Serializers

```python
from rest_framework import serializers
from ocr.services.aws import AWSService

class DocumentUploadSerializer(serializers.Serializer):
    passport = serializers.FileField(required=False)
    utility_bill = serializers.FileField(required=False)
    bank_statement = serializers.FileField(required=False)
    
    def save(self, user):
        aws_service = AWSService()
        
        files = {
            k: v for k, v in self.validated_data.items() 
            if v is not None
        }
        
        return aws_service.upload_files_concurrently(
            user_id=user.pk,
            files=files,
            file_category="user_documents"
        )
```

## Testing

```python
from unittest.mock import patch, Mock
from django.test import TestCase
from ocr.services.aws import AWSService

class TestConcurrentUpload(TestCase):
    @patch('ocr.services.aws.gevent')
    @patch.object(AWSService, 's3')
    def test_concurrent_upload(self, mock_s3, mock_gevent):
        # Setup mocks
        mock_pool = Mock()
        mock_gevent.pool.Pool.return_value = mock_pool
        
        # Test your upload functionality
        aws_service = AWSService()
        result = aws_service.upload_files_concurrently(
            user_id=123,
            files={'test': mock_file},
            file_category="test"
        )
        
        # Verify gevent was used
        mock_gevent.pool.Pool.assert_called_once()
```

## Migration from Sequential Upload

If you have existing sequential upload code:

```python
# Old way (sequential)
for file_type, file_obj in files.items():
    url = aws_service.upload_single_file(file_obj)
    urls[file_type] = url

# New way (concurrent)
urls = aws_service.upload_files_concurrently(
    user_id=user.pk,
    files=files,
    file_category="documents"
)
```

## Best Practices

1. **Choose appropriate concurrency**: Don't use more workers than files
2. **Handle partial failures**: Check if all files uploaded successfully
3. **Use meaningful categories**: Organize files logically in S3
4. **Filter None values**: Remove empty files before upload
5. **Log upload results**: Monitor success/failure rates
6. **Consider file sizes**: Adjust concurrency based on total data volume
7. **Test with realistic data**: Verify performance with actual file sizes

## Troubleshooting

### Common Issues

1. **High memory usage**: Reduce concurrency for large files
2. **Timeout errors**: Increase timeout settings or reduce concurrency
3. **Rate limiting**: AWS may throttle requests - implement retry logic
4. **Partial uploads**: Check logs for specific file failures

### Monitoring

```python
import time

start_time = time.time()
urls = aws_service.upload_files_concurrently(
    user_id=user.pk,
    files=files,
    file_category="documents"
)
end_time = time.time()

print(f"Uploaded {len(urls)} files in {end_time - start_time:.2f} seconds")
print(f"Success rate: {len(urls) / len(files) * 100:.1f}%")
```

This concurrent upload feature provides significant performance improvements while maintaining backward compatibility and error resilience. 