import base64
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile
from idanalyzer2 import Profile, Scanner
from loguru import logger

from ..choices import DocumentTypeChoices
from ..schemas import CardData, DocumentVerificationResponse, Warning


class VerificationService:
    SUPPORTED_DOCUMENT_TYPES = [choice[0] for choice in DocumentTypeChoices.choices]
    DOCUMENT_TYPE_MAPPING = {
        DocumentTypeChoices.PASSPORT: "passport",
        DocumentTypeChoices.NATIONAL_ID: "national_id",
        DocumentTypeChoices.DRIVER_LICENSE: "driver_license",
    }

    def __init__(self):
        profile = Profile(Profile.SECURITY_MEDIUM)
        self.scanner = Scanner(settings.ID_ANALYZER_API_KEY)
        self.scanner.throwApiException(True)
        self.scanner.setProfile(profile)

    @staticmethod
    def encode_file(file: InMemoryUploadedFile | None) -> str | None:
        if file is None:
            return None
        file.seek(0)
        file_content = file.read()
        file.seek(0)
        return base64.b64encode(file_content).decode("utf-8")

    def verify_document(
        self,
        id_card_front: InMemoryUploadedFile,
        id_card_back: InMemoryUploadedFile | None,
        face: InMemoryUploadedFile,
        face_video: Optional[InMemoryUploadedFile] = None,
    ) -> DocumentVerificationResponse:
        try:
            with ThreadPoolExecutor() as executor:
                front_encoded, back_encoded, face_encoded, face_video_encoded = (
                    executor.map(
                        self.encode_file,
                        [id_card_front, id_card_back, face, face_video],
                    )
                )

            if face_video_encoded and back_encoded:
                resp = self.scanner.scan(
                    front_encoded, back_encoded, face_encoded, face_video_encoded
                )
            elif back_encoded:
                resp = self.scanner.scan(front_encoded, back_encoded, face_encoded)
            else:
                resp = self.scanner.scan(front_encoded, "", face_encoded)

            return DocumentVerificationResponse(
                success=resp.get("success", False),
                transaction_id=resp.get("transactionId", ""),
                data=[
                    CardData(
                        field=k,
                        value=v[0]["value"] if isinstance(v, list) and v else str(v),
                        confidence=v[0]["confidence"]
                        if isinstance(v, list) and v and "confidence" in v[0]
                        else 0.0,
                    )
                    for k, v in resp.get("data", {}).items()
                ],
                warnings=[
                    Warning(
                        code=w.get("code", ""),
                        description=w.get("description", ""),
                        severity=w.get("severity", ""),
                        confidence=w.get("confidence", 0.0),
                        decision=w.get("decision", ""),
                    )
                    for w in resp.get("warning", [])
                ],
                review_score=resp.get("reviewScore", 0),
                reject_score=resp.get("rejectScore", 0),
                decision=resp.get("decision", "pending"),
            )

        except Exception as e:
            logger.error(f"Error during document verification: {str(e)}")
            return DocumentVerificationResponse(
                success=False,
                transaction_id="",
                data=[],
                warnings=[
                    Warning(
                        code="VERIFICATION_ERROR",
                        description=f"Verification failed: {str(e)}",
                        severity="high",
                        confidence=0.0,
                        decision="reject",
                    )
                ],
                review_score=0,
                reject_score=100,
                decision="reject",
            )


verification_service = VerificationService()
