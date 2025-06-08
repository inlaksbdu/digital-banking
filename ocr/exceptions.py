class CardVerificationError(Exception):
    pass


class UnsupportedDocumentTypeError(Exception):
    pass


class CardAlreadyExistsError(Exception):
    pass


class CardExpiredError(Exception):
    pass


class CardNotVerifiedError(Exception):
    pass


class FileTooLargeError(Exception):
    pass


class FileTooSmallError(Exception):
    pass


class InvalidFileTypeError(Exception):
    pass
