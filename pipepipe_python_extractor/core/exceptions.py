class ExtractionException(Exception):
    pass

class ContentNotAvailableException(ExtractionException):
    pass

class AgeRestrictedContentException(ContentNotAvailableException):
    pass

class GeographicRestrictionException(ContentNotAvailableException):
    pass

class PaidContentException(ContentNotAvailableException):
    pass

class PrivateContentException(ContentNotAvailableException):
    pass

class ParsingException(ExtractionException):
    pass

class ReCaptchaException(ExtractionException):
    pass

class AccountTerminatedException(ContentNotAvailableException):
    pass

class NotFoundException(ExtractionException):
    pass
