from config.exceptions import BaseException


class CardVerificationError(BaseException):
    pass


class UnsupportedDocumentTypeError(BaseException):
    pass


class CardAlreadyExistsError(BaseException):
    pass


class CardExpiredError(BaseException):
    pass


class CardNotVerifiedError(BaseException):
    pass


class FileTooLargeError(BaseException):
    pass


class FileTooSmallError(BaseException):
    pass


class InvalidFileTypeError(BaseException):
    pass


class DocumentVerificationError(BaseException):
    pass
