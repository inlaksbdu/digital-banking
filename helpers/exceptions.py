from config.exceptions import BaseException


class GeneralException(BaseException):
    status_code = 400
    default_code = 100
    default_detail = "Sorry an error occured"


class LoginException(BaseException):
    status_code = 400
    default_code = 101
    default_detail = "Invalid username or password"


class AccountExistsException(BaseException):
    status_code = 400
    default_code = 102
    default_detail = "A user with the provided details already exists."


class UserDoesNotExistException(BaseException):
    status_code = 400
    default_code = 103
    default_detail = "A user does not exist with the given credentials"


class InactiveAccountException(BaseException):
    status_code = 400
    default_code = 104
    default_detail = (
        "Account not activated, an OTP has been sent "
        "to your email, please verify your account."
    )


class EmailDoesNotExistsException(BaseException):
    status_code = 400
    default_code = 105
    default_detail = "No user account found for the provided email"


class UsernameDoesNotExistsException(BaseException):
    status_code = 400
    default_code = 106
    default_detail = "No user account found for the provided username"


class AccountDoesNotExistException(BaseException):
    status_code = 400
    default_code = 107
    default_detail = "Account not found"


class AccountAlreadyVerifiedException(BaseException):
    status_code = 400
    default_code = 108
    default_detail = "Account already verified or active"


class EmailAlreadyVerifiedException(BaseException):
    status_code = 400
    default_code = 109
    default_detail = "Email already verified or active"


class EmailNotVerifiedException(BaseException):
    status_code = 400
    default_code = 110
    default_detail = "Email is unverified"


class InvalidOTPException(BaseException):
    status_code = 400
    default_code = 111
    default_detail = "OTP is invalid or expired."


class OTPExpiredException(BaseException):
    status_code = 400
    default_code = 112
    default_detail = "The provided OTP is expired"


class EmailOrUsernameRequiredException(BaseException):
    status_code = 400
    default_code = 113
    default_detail = "At least email or username is required"


class PasswordsDoNotMatchException(BaseException):
    default_code = 115
    default_detail = "The two password fields didn't match."


class InvalidPasswordException(BaseException):
    default_code = 116
    default_detail = "Invalid passwords. Please use prescribed format"


class EmailAlreadyInUseException(BaseException):
    default_code = 118
    default_detail = "The provided email is already in use."


class ProvideUsernameOrPasswordException(BaseException):
    status_code = 400
    default_code = 119
    default_detail = "Provide username or password"


class ChangePasswordException(BaseException):
    status_code = 400
    default_code = 120
    default_detail = "Please reset your password."


class PhoneNumberAlreadyInUseException(BaseException):
    status_code = 400
    default_code = 121
    default_detail = "The provided phone number is already in use."


class InvalidRegistrationToken(BaseException):
    status_code = 400
    default_code = 122
    default_detail = "Invalid account registration token"


class InvalidGenderException(BaseException):
    status_code = 400
    default_code = 123
    default_detail = "Gender should be Male or Female"


class InvalidDOBException(BaseException):
    status_code = 400
    default_code = 124
    default_detail = "Invalid Date of Birth, please check and try again"


class InvalidToken(BaseException):
    status_code = 400
    default_code = 125
    default_detail = "The provided token is invalid."


class AccountNumberNotExist(BaseException):
    status_code = 400
    default_code = 126
    default_detail = "Account Number Does Not Exist"


class AccountDeactivatedException(BaseException):
    status_code = 400
    default_code = 127
    default_detail = (
        "Sorry your user Account has been deactivated, Please Visit the nearest Branch."
    )


class InvalidAccessCdoe(BaseException):
    status_code = 400
    default_code = 128
    default_detail = "Invalid Access Code"


class ProvideAccessCodeUsernamePassword(BaseException):
    status_code = 400
    default_code = 129
    default_detail = "Please provide access code and username and password"


class AccountNotAllowed(BaseException):
    status_code = 400
    default_code = 130
    default_detail = "Sorry, this account is not authorized to use this service"


class InvalidCredentials(BaseException):
    status_code = 400
    default_code = 131
    default_detail = "Invalid Credentials provided"


class CorporateAccountDeactivatedException(BaseException):
    status_code = 400
    default_code = 132
    default_detail = "Corporate with the provided access code have been deactivated. Please report ot your admin or visit the nearest branch."


class T24InvalidPhoneNumberException(BaseException):
    status_code = 400
    default_code = 133
    default_detail = "Customer with this phone number does not exist"


class InvalidSecurePINException(BaseException):
    status_code = 400
    default_code = 134
    default_detail = "Invalid PIN"


class TooManyLoginAttemptsException(BaseException):
    status_code = 400
    default_code = 134
    default_detail = "Too many login attempt, please try again, in the next 5 minutes."


class TooManyAttempt(BaseException):
    status_code = 400
    default_code = 134
    default_detail = "Too many attempt, please try again in the next 5 minutes."


class CustomerT24Existance(BaseException):
    status_code = 400
    default_code = 135
    default_detail = "Sorry, You are already an existing customer in GTI, pelase signup up as existing customer"


class CustomerDigitalExistance(BaseException):
    status_code = 400
    default_code = 136
    default_detail = "Sorry, You are already an existing customer in GTI, please login with your account details."


class DeviceNotRecognized(BaseException):
    status_code = 400
    default_code = 137
    default_detail = "Sorry, this device cannot be reconized or its not active"


class InvalidDevicePassword(BaseException):
    status_code = 400
    default_code = 138
    default_detail = "Invalid Password"


class PermissionDenied(BaseException):
    status_code = 400
    default_code = 139
    default_detail = "Sorry, you don't have permission to perform this action."


class NotAuthorizedException(BaseException):
    status_code = 400
    default_code = 140
    default_detail = "Sorry, you are not authorized to perform this action."


class BookingCodeDoesNotExist(BaseException):
    status_code = 400
    default_code = 141
    default_detail = "Sorry, Invalid Booking Code"


class BookingCodeExpired(BaseException):
    status_code = 400
    default_code = 142
    default_detail = "Sorry, Booking code has expired"


class BookingCodeAlreadyUsed(BaseException):
    status_code = 400
    default_code = 143
    default_detail = "Sorry, Booking code has already been used."


class InvalidServiceType(BaseException):
    status_code = 400
    default_code = 143
    default_detail = "No matching query found with the provided service type"


class PhoneNumberRequired(BaseException):
    status_code = 400
    default_code = 144
    default_detail = "Sorry, your phone number is required."


class NotAuthorized(BaseException):
    status_code = 400
    default_code = 145
    default_detail = "Sorry, you are not authorized."
