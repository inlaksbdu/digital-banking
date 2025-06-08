import io
from unittest.mock import Mock, patch
from django.test import TestCase
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.contrib.auth import get_user_model

from ..services.aws import AWSService

User = get_user_model()


class ConcurrentUploadTestCase(TestCase):
    def setUp(self):
        self.aws_service = AWSService()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def create_mock_file(
        self, name: str, content: str = "test content", content_type: str = "image/jpeg"
    ):
        file_content = content.encode("utf-8")
        return InMemoryUploadedFile(
            file=io.BytesIO(file_content),
            field_name=name,
            name=f"{name}.jpg",
            content_type=content_type,
            size=len(file_content),
            charset=None,
        )

    @patch("ocr.services.aws.gevent")
    @patch.object(AWSService, "s3")
    @patch.object(AWSService, "get_image_url_if_exists")
    def test_concurrent_upload_success(self, mock_get_url, mock_s3, mock_gevent):
        """Test successful concurrent upload of multiple files"""

        # Setup mocks
        mock_get_url.return_value = None  # Files don't exist
        mock_s3.upload_fileobj = Mock()

        # Mock gevent pool and greenlets
        mock_pool = Mock()
        mock_gevent.pool.Pool.return_value = mock_pool

        # Create mock greenlets that return successful results
        mock_greenlet1 = Mock()
        mock_greenlet1.value = ("front", "s3://bucket/front.jpg", None)
        mock_greenlet2 = Mock()
        mock_greenlet2.value = ("back", "s3://bucket/back.jpg", None)
        mock_greenlet3 = Mock()
        mock_greenlet3.value = ("selfie", "s3://bucket/selfie.jpg", None)

        mock_pool.spawn.side_effect = [mock_greenlet1, mock_greenlet2, mock_greenlet3]
        mock_gevent.joinall = Mock()

        # Create test files
        files = {
            "front": self.create_mock_file("front"),
            "back": self.create_mock_file("back"),
            "selfie": self.create_mock_file("selfie"),
        }

        # Test upload
        result = self.aws_service.upload_files_concurrently(
            user_id=self.user.pk,
            files=files,
            file_category="test_category",
            max_workers=3,
        )

        # Assertions
        self.assertEqual(len(result), 3)
        self.assertIn("front", result)
        self.assertIn("back", result)
        self.assertIn("selfie", result)

        # Verify gevent was used correctly
        mock_gevent.pool.Pool.assert_called_once_with(3)
        self.assertEqual(mock_pool.spawn.call_count, 3)
        mock_gevent.joinall.assert_called_once()
        mock_pool.kill.assert_called_once()

    @patch("ocr.services.aws.gevent")
    @patch.object(AWSService, "s3")
    @patch.object(AWSService, "get_image_url_if_exists")
    def test_concurrent_upload_with_existing_files(
        self, mock_get_url, mock_s3, mock_gevent
    ):
        """Test upload when some files already exist"""

        # Setup mocks - one file exists, others don't
        def mock_url_exists(key, bucket):
            if "front" in key:
                return "s3://bucket/existing_front.jpg"
            return None

        mock_get_url.side_effect = mock_url_exists
        mock_s3.upload_fileobj = Mock()

        # Mock gevent
        mock_pool = Mock()
        mock_gevent.pool.Pool.return_value = mock_pool

        mock_greenlet1 = Mock()
        mock_greenlet1.value = ("front", "s3://bucket/existing_front.jpg", None)
        mock_greenlet2 = Mock()
        mock_greenlet2.value = ("back", "s3://bucket/back.jpg", None)

        mock_pool.spawn.side_effect = [mock_greenlet1, mock_greenlet2]
        mock_gevent.joinall = Mock()

        files = {
            "front": self.create_mock_file("front"),
            "back": self.create_mock_file("back"),
        }

        result = self.aws_service.upload_files_concurrently(
            user_id=self.user.pk, files=files, file_category="test_category"
        )

        self.assertEqual(len(result), 2)
        self.assertEqual(result["front"], "s3://bucket/existing_front.jpg")
        self.assertEqual(result["back"], "s3://bucket/back.jpg")

    @patch("ocr.services.aws.gevent")
    @patch.object(AWSService, "s3")
    @patch.object(AWSService, "get_image_url_if_exists")
    def test_concurrent_upload_with_errors(self, mock_get_url, mock_s3, mock_gevent):
        """Test upload with some files failing"""

        mock_get_url.return_value = None
        mock_s3.upload_fileobj = Mock()

        # Mock gevent
        mock_pool = Mock()
        mock_gevent.pool.Pool.return_value = mock_pool

        # One successful, one failed
        mock_greenlet1 = Mock()
        mock_greenlet1.value = ("front", "s3://bucket/front.jpg", None)
        mock_greenlet2 = Mock()
        mock_greenlet2.value = ("back", None, "Upload failed")

        mock_pool.spawn.side_effect = [mock_greenlet1, mock_greenlet2]
        mock_gevent.joinall = Mock()

        files = {
            "front": self.create_mock_file("front"),
            "back": self.create_mock_file("back"),
        }

        # Should not raise exception, just log warnings
        result = self.aws_service.upload_files_concurrently(
            user_id=self.user.pk, files=files, file_category="test_category"
        )

        # Only successful upload should be in result
        self.assertEqual(len(result), 1)
        self.assertIn("front", result)
        self.assertNotIn("back", result)

    def test_empty_files_dict(self):
        """Test upload with empty files dictionary"""
        result = self.aws_service.upload_files_concurrently(
            user_id=self.user.pk, files={}, file_category="test_category"
        )

        self.assertEqual(result, {})

    def test_files_with_none_values(self):
        """Test upload with None values in files dict"""
        files = {
            "front": self.create_mock_file("front"),
            "back": None,
            "selfie": self.create_mock_file("selfie"),
        }

        # Should filter out None values
        with patch.object(self.aws_service, "_upload_single_file_group") as mock_upload:
            mock_upload.return_value = {
                "front": "s3://bucket/front.jpg",
                "selfie": "s3://bucket/selfie.jpg",
            }

            result = self.aws_service.upload_files_concurrently(
                user_id=self.user.pk, files=files, file_category="test_category"
            )

    def test_get_file_extension(self):
        """Test file extension detection"""

        # Test with content type
        jpeg_file = self.create_mock_file("test", content_type="image/jpeg")
        self.assertEqual(self.aws_service._get_file_extension(jpeg_file), "jpg")

        png_file = self.create_mock_file("test", content_type="image/png")
        self.assertEqual(self.aws_service._get_file_extension(png_file), "png")

        pdf_file = self.create_mock_file("test", content_type="application/pdf")
        self.assertEqual(self.aws_service._get_file_extension(pdf_file), "pdf")

        # Test with filename
        file_with_name = InMemoryUploadedFile(
            file=io.BytesIO(b"test"),
            field_name="test",
            name="document.docx",
            content_type=None,
            size=4,
            charset=None,
        )
        self.assertEqual(self.aws_service._get_file_extension(file_with_name), "docx")

        # Test fallback
        unknown_file = InMemoryUploadedFile(
            file=io.BytesIO(b"test"),
            field_name="test",
            name=None,
            content_type=None,
            size=4,
            charset=None,
        )
        self.assertEqual(self.aws_service._get_file_extension(unknown_file), "bin")

    @patch.object(AWSService, "upload_files_concurrently")
    def test_legacy_upload_to_s3_compatibility(self, mock_concurrent_upload):
        """Test that legacy upload_to_s3 method uses concurrent upload internally"""

        mock_concurrent_upload.return_value = {
            "front": "s3://bucket/front.jpg",
            "back": "s3://bucket/back.jpg",
            "selfie": "s3://bucket/selfie.jpg",
        }

        front = self.create_mock_file("front")
        back = self.create_mock_file("back")
        selfie = self.create_mock_file("selfie")

        result = self.aws_service.upload_to_s3(
            user_id=self.user.pk, image_front=front, image_back=back, selfie=selfie
        )

        # Verify concurrent upload was called with correct parameters
        mock_concurrent_upload.assert_called_once_with(
            user_id=self.user.pk,
            files={
                "front": front,
                "back": back,
                "selfie": selfie,
                "selfie_video": None,
            },
            file_category="id_cards",
            bucket_name=None,
            max_workers=4,
        )

        self.assertEqual(len(result), 3)


class FileExtensionTestCase(TestCase):
    def setUp(self):
        self.aws_service = AWSService()

    def test_content_type_mapping(self):
        """Test various content type to extension mappings"""
        test_cases = [
            ("image/jpeg", "jpg"),
            ("image/png", "png"),
            ("image/gif", "gif"),
            ("image/webp", "webp"),
            ("video/mp4", "mp4"),
            ("video/webm", "webm"),
            ("application/pdf", "pdf"),
            ("text/plain", "txt"),
            ("application/unknown", "unknown"),  # Fallback
        ]

        for content_type, expected_ext in test_cases:
            with self.subTest(content_type=content_type):
                mock_file = Mock()
                mock_file.content_type = content_type
                mock_file.name = None

                result = self.aws_service._get_file_extension(mock_file)
                self.assertEqual(result, expected_ext)
