VERIFICATION_FAILED = 10001
NO_REFERENCED_BY = 10002
FAILED_REFERENCED_BY = 10003
RESOURCES_EXCEEDED = 10004
METHOD_PROHIBITED = 10005
DUPLICATE_RESOURCE = 10006

error_messages = {
    VERIFICATION_FAILED: 'Verification failed',
    NO_REFERENCED_BY: 'Missing referenced_by resource',
    FAILED_REFERENCED_BY: 'Verification failed for referenced_by resource',
    RESOURCES_EXCEEDED: 'Number of allowed resources exceeded',
    METHOD_PROHIBITED: 'The method is prohibited for the resource',
    DUPLICATE_RESOURCE: 'Duplicate resource detected'
}


class ValidationException(Exception):
    """Base class for Validator exceptions"""
    pass


class ValidationError(ValidationException):
    """
    Validator modules raise ValidationError upon failure
    """
    def __init__(self, code, details=""):
        if code not in error_messages:
            code = VERIFICATION_FAILED

        message = error_messages[code]

        self.error = {'code': code,
                      'message': message,
                      'details': details}
