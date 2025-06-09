from dataclasses import dataclass
from datetime import datetime
import hashlib
import io
from typing import Any, Literal, Optional, Dict
from urllib.parse import urlparse
import uuid
from typing_extensions import deprecated
import boto3
import gevent
from gevent import pool
from botocore.exceptions import ClientError
from botocore.client import BaseClient
from loguru import logger
from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile


@dataclass
class ImageUploadResult:
    prefix: str
    content: bytes
    s3_path: str


class AWSService:
    def __init__(self):
        self.s3: BaseClient = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
        )
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        try:
            self.s3.head_bucket(Bucket=self.bucket_name)
            logger.success(f"Bucket {self.bucket_name} exists")
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise Exception(f"Bucket {self.bucket_name} does not exist")
            raise e

    @staticmethod
    def generate_doc_id() -> str:
        doc_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        s3_key = f"documents/{doc_id}_{timestamp}.jpg"
        return s3_key

    def delete_from_s3(self, key: str) -> bool:
        try:
            self.s3.delete_object(Bucket=self.bucket_name, Key=key)
            logger.success(f"Deleted image from S3: {key}")
            return True
        except ClientError as e:
            error_msg = f"Failed to delete image from S3: {str(e)}"
            logger.error(error_msg)
            raise ClientError({"Error": {"Message": error_msg}}, "DeleteObject")

    def get_image_url_if_exists(self, key: str) -> Optional[str]:
        try:
            self.s3.head_object(Bucket=self.bucket_name, Key=key)
            return f"s3://{self.bucket_name}/{key}"
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return None
            error_msg = f"Failed to get image URL from S3: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def upload_files_concurrently(
        self,
        files: Dict[
            Literal["front", "back", "selfie", "selfie_video"] | str,
            Optional[InMemoryUploadedFile],
        ],
        file_category: str = "general",
        bucket_name: Optional[str] = None,
        max_workers: int = 5,
    ) -> Dict[Literal["front", "back", "selfie", "selfie_video"] | str, str | None]:
        """
        Upload multiple files to S3 concurrently using gevent

        Args:
            files: Dictionary of {file_type: file_object} to upload
            file_category: Category for organizing files (e.g., 'id_cards', 'documents')
            bucket_name: S3 bucket name (optional)
            max_workers: Maximum number of concurrent uploads

        Returns:
            Dictionary of {file_type: s3_url} for successfully uploaded files
        """
        uploaded_urls = {}

        valid_files = {k: v for k, v in files.items() if v is not None}

        if not valid_files:
            return uploaded_urls

        upload_pool = pool.Pool(max_workers)

        def upload_single_file(file_type: str, file_obj: InMemoryUploadedFile) -> tuple:
            try:
                file_obj.seek(0)
                content = file_obj.read()
                file_obj.seek(0)

                hash_md5 = hashlib.md5(content).hexdigest()
                file_ext = self._get_file_extension(file_obj)
                key = f"{file_category}/{file_type}/{hash_md5}.{file_ext}"

                existing_url = self.get_image_url_if_exists(key)
                if existing_url:
                    logger.info(f"File already exists in S3: {key}")
                    return (file_type, existing_url, None)

                self.s3.upload_fileobj(
                    io.BytesIO(content),
                    Bucket=self.bucket_name,
                    Key=key,
                    ExtraArgs={
                        "ContentType": file_obj.content_type
                        or "application/octet-stream",
                        "ACL": "private",
                        "Metadata": {
                            "file_type": file_type,
                            "file_category": file_category,
                            "uploaded_at": datetime.now().isoformat(),
                            "original_filename": file_obj.name
                            or f"{file_type}.{file_ext}",
                        },
                    },
                )

                s3_path = f"s3://{self.bucket_name}/{key}"
                logger.success(f"Successfully uploaded {file_type} to S3: {key}")
                return (file_type, s3_path, None)

            except Exception as e:
                raise e
                error_msg = f"Failed to upload {file_type}: {str(e)}"
                logger.error(error_msg)
                return (file_type, None, error_msg)

        try:
            greenlets = []
            for file_type, file_obj in valid_files.items():
                greenlet = upload_pool.spawn(upload_single_file, file_type, file_obj)
                greenlets.append(greenlet)

            gevent.joinall(greenlets)

            errors = []
            for greenlet in greenlets:
                file_type, url, error = greenlet.value
                if error:
                    errors.append(f"{file_type}: {error}")
                elif url:
                    uploaded_urls[file_type] = url

            if errors:
                error_summary = "; ".join(errors)
                logger.warning(f"Some uploads failed: {error_summary}")

        except Exception as e:
            raise e
            error_msg = f"Critical error during concurrent upload: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
        finally:
            upload_pool.kill()

        return uploaded_urls

    def _get_file_extension(self, file_obj: InMemoryUploadedFile) -> str:
        if file_obj.content_type:
            content_type_map = {
                "image/jpeg": "jpg",
                "image/png": "png",
                "image/gif": "gif",
                "image/webp": "webp",
                "video/mp4": "mp4",
                "video/webm": "webm",
                "video/mov": "mov",
                "video/avi": "avi",
                "application/pdf": "pdf",
                "text/plain": "txt",
            }

            extension = content_type_map.get(file_obj.content_type)
            if extension:
                return extension

            try:
                return file_obj.content_type.split("/")[-1].lower()
            except Exception:
                pass

        if file_obj.name and "." in file_obj.name:
            return file_obj.name.split(".")[-1].lower()

        return "bin"

    @deprecated("Use upload_files_concurrently instead", category=DeprecationWarning)
    def upload_to_s3(
        self,
        image_front: Any,
        image_back: Any,
        selfie: Any,
        selfie_video: Any = None,
        bucket_name: Optional[str] = None,
    ) -> Dict[Literal["front", "back", "selfie", "selfie_video"] | str, str | None]:
        """
        Legacy method for backward compatibility
        Uses the new concurrent upload method internally
        """
        files = {
            "front": image_front,
            "back": image_back,
            "selfie": selfie,
            "selfie_video": selfie_video,
        }

        return self.upload_files_concurrently(
            files=files,
            file_category="id_cards",
            bucket_name=bucket_name,
            max_workers=4,
        )

    def generate_presigned_url(self, key: str, expiration: int = 3600) -> str:
        url = self.s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.bucket_name,
                "Key": key,
                "ResponseContentDisposition": "inline",
            },
            ExpiresIn=expiration,
        )
        return url

    @staticmethod
    def get_s3_key(s3_url: str) -> str:
        parsed = urlparse(s3_url)
        return parsed.path.lstrip("/")

    @staticmethod
    def get_s3_bucket(s3_url: str) -> str:
        parsed = urlparse(s3_url)
        return parsed.netloc


aws_service = AWSService()
