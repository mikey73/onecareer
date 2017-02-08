# coding: utf-8

from .compat import class_types


class APIError(Exception):
    error_code = 1000
    log_message = "Houston, We've Got a Problem"

    def __init__(self, message=None):
        if message is not None:
            self.log_message = message

    def __str__(self):
        return "(%d: %s)" % (self.error_code, self.log_message)


class TornadoError(APIError):
    error_code = 1001
    log_message = "Tornado Error"


class JsonDecodeError(TornadoError):
    error_code = 1002
    log_message = "Could not decode JSON string"


class SchemaInvalidError(TornadoError):
    error_code = 1003
    log_message = "Schema validation failed"


class RateLimitExceededError(APIError):
    error_code = 1004
    log_message = "API Rate limit exceeded"


# exceptions raised during request handling and validation
class RequestError(APIError):
    error_code = 1100
    log_message = "The request could not be processed"


class NotFoundError(RequestError):
    error_code = 1101
    log_message = "The requested endpoint does not exist"


class MaxContentLength(RequestError):
    error_code = 1102
    log_message = "Request content length limit exceeded"


class MissingParameter(RequestError):
    error_code = 1103
    log_message = "Required parameter not found"


class FileError(RequestError):
    error_code = 1104
    log_message = "The parameter value is not a valid file"


class DateError(RequestError):
    error_code = 1105
    log_message = "The parameter value is not a valid date"


class FloatFormatError(RequestError):
    error_code = 1106
    log_message = "The parameter value is not a valid float"


class OutofRangeError(RequestError):
    error_code = 1107
    log_message = "The parameter value is out of range"


class IntegerFormatError(RequestError):
    error_code = 1108
    log_message = "The parameter value is not a valid integer"


class InvalidPDFError(RequestError):
    error_code = 1109
    log_message = "The file is not a valid PDF"


class DecimalFormatError(RequestError):
    error_code = 1110
    log_message = "The parameter value is not a valid decimal"


class ValueNotStringError(RequestError):
    error_code = 1111
    log_message = "The parameter value(s) is not of basestring type"


class FileNameError(RequestError):
    error_code = 1112
    log_message = "The file name is invalid"


class InvalidBoundingBoxError(RequestError):
    error_code = 1113
    log_message = "The bounding box is not valid"


class StateNotFoundError(RequestError):
    error_code = 1801
    log_message = "The parameter value is not a valid state abbreviation"


class ZipcodeFormatError(RequestError):
    error_code = 1802
    log_message = "The parameter value is not a valid zipcode"


class InvalidTimezoneError(RequestError):
    error_code = 1803
    log_message = "The parameter value is not a valid timezone"


class PhoneNumberFormatError(RequestError):
    error_code = 1804
    log_message = "The parameter value is not a valid phone number"


class OrgTypeNotFoundError(RequestError):
    error_code = 1805
    log_message = "The parameter value is not a valid organization type"


# exceptions raised during OAuth2 authentication
class AuthError(APIError):
    error_code = 1200
    log_message = "Authentication failed"


class InvalidRefreshToken(AuthError):
    error_code = 1201
    log_message = "Invalid refresh token"


class InvalidAccessToken(AuthError):
    error_code = 1202
    log_message = "Invalid access token"


class InvalidAuthCredentials(AuthError):
    error_code = 1203
    log_message = "Invalid authorization credentials"


class APIKeyError(AuthError):
    error_code = 1204
    log_message = "Invalid API key credentials"


# exceptions raised during account creation and fetching
class AccountError(APIError):
    error_code = 1300
    log_message = "An unknown account error occurred"


class PasswordFormatError(AccountError):
    error_code = 1301
    log_message = "Invalid password format"


class PasswordConfirmError(AccountError):
    error_code = 1302
    log_message = "Password and confirmation do not match"


class PasswordLoginError(AccountError):
    error_code = 1303
    log_message = "Incorrect password"


class EmailFormatError(AccountError):
    error_code = 1304
    log_message = "Invalid or blank email"


class EmailExistsError(AccountError):
    error_code = 1305
    log_message = "An account with that email address exists"


class EmailOrPasswordNotFoundError(AccountError):
    error_code = 1306
    log_message = "Email and/or password not found"


class AccountInactive(AccountError):
    error_code = 1307
    log_message = "Account is not active"


class AccountNotVerified(AccountError):
    error_code = 1308
    log_message = "Account is not verified"


class InvalidVerification(AccountError):
    error_code = 1309
    log_message = "Invalid verification code"


class VerificationExpired(AccountError):
    error_code = 1310
    log_message = "Verification code has expired"


class BadPassword(AccountError):
    error_code = 1311
    log_message = "Invalid password"


class EmailNotFoundError(AccountError):
    error_code = 1312
    log_message = "Email not found"


class AccountInfoNotFoundError(AccountError):
    error_code = 1313
    log_message = "Account info not found"


class AccountNotFoundError(AccountError):
    error_code = 1399
    log_message = "Account not found"


class InvalidRoleError(AccountError):
    error_code = 1400
    log_message = "Invalid role"


# permission errors
class PermissionError(APIError):
    error_code = 2100
    log_message = "Invalid Permission"


class EndpointPermissionError(PermissionError):
    error_code = 2101
    log_message = "No permission to access this endpoint"


class AccountPermissionError(PermissionError):
    error_code = 2103
    log_message = "Account permission error"


# workflow server error
class WorkflowError(APIError):
    error_code = 2200
    log_message = "Workflow Error"


class PDFNotFoundError(WorkflowError):
    error_code = 2201
    log_message = "PDF Not Found"


# database error
class DataBaseError(APIError):
    error_code = 2300
    log_message = "Database Error"


class DBNotFoundError(DataBaseError):
    error_code = 2301
    log_message = "DB Object Not Found"


# exceptions raised when fetching from s3
class S3KeyError(APIError):
    error_code = 1900
    log_message = "An S3Key error occurred"


class S3BucketError(APIError):
    error_code = 1901
    log_message = "An S3Bucket error occurred"



_locals = locals().copy()
error_map = {e.error_code: e for e in _locals.values() if (isinstance(e, class_types) and
                                                           issubclass(e, APIError))}
del _locals


# Client Error
class ServerHTTPError(Exception):
    def __init__(self, code, message=""):
        self.code = code
        self.message = message

    def __str__(self):
        return "(%d: %s)" % (self.code, self.message)
