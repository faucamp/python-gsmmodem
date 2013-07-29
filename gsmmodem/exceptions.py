""" Module defines exceptions used by gsmmodem """

class GsmModemException(Exception):
    """ Base exception raised for error conditions when interacting with the GSM modem """


class TimeoutException(GsmModemException):
    """ Raised when a write command times out """
    
    def __init__(self, data=None):
        """ @param data: Any data that was read was read before timeout occurred (if applicable) """
        super(TimeoutException, self).__init__(data)
        self.data = data 


class InvalidStateException(GsmModemException):
    """ Raised when an API method call is invoked on an object that is in an incorrect state """


class InterruptedException(InvalidStateException):
    """ Raised when execution of an AT command is interrupt by a state change.
    May contain another exception that was the cause of the interruption """
    
    def __init__(self, message, cause=None):
        """ @param cause: the exception that caused this interruption (usually a CmeError) """
        super(InterruptedException, self).__init__(message)
        self.cause = cause


class CommandError(GsmModemException):
    """ Raised if the modem returns an error in response to an AT command
     
    May optionally include an error type (CME or CMS) and -code (error-specific).
    """
    
    _description = ''
    
    def __init__(self, command=None, type=None, code=None):
        self.command = command
        self.type = type
        self.code = code
        if type != None and code != None:
            super(CommandError, self).__init__('{0} {1}{2}'.format(type, code, ' ({0})'.format(self._description) if len(self._description) > 0 else ''))
        elif command != None:
            super(CommandError, self).__init__(command)
        else:
            super(CommandError, self).__init__()


class CmeError(CommandError):
    """ ME error result code : +CME ERROR: <error>
     
    Issued in response to an AT command
    """

    def __new__(cls, *args, **kwargs):
        # Return a specialized version of this class if possible
        if len(args) >= 2:
            code = args[1]
            if code == 11:
                return PinRequiredError(args[0])
            elif code == 16:
                return IncorrectPinError(args[0])
            elif code == 12:
                return PukRequiredError(args[0])
        return super(CmeError, cls).__new__(cls, *args, **kwargs)

    def __init__(self, command, code):
        super(CmeError, self).__init__(command, 'CME', code)


class SecurityException(CmeError):
    """ Security-related CME error """

    def __init__(self, command, code):
        super(SecurityException, self).__init__(command, code)


class PinRequiredError(SecurityException):
    """ Raised if an operation failed because the SIM card's PIN has not been entered """

    _description = 'SIM card PIN is required'

    def __init__(self, command, code=11):
        super(PinRequiredError, self).__init__(command, code)


class IncorrectPinError(SecurityException):
    """ Raised if an incorrect PIN is entered """

    _description = 'Incorrect PIN entered'

    def __init__(self, command, code=16):
        super(IncorrectPinError, self).__init__(command, code)


class PukRequiredError(SecurityException):
    """ Raised an operation failed because the SIM card's PUK is required (SIM locked) """
    
    _description = "PUK required (SIM locked)"
    
    def __init__(self, command, code=12):
        super(PukRequiredError, self).__init__(command, code)


class CmsError(CommandError):
    """ Message service failure result code: +CMS ERROR : <er>
    
    Issued in response to an AT command
    """

    def __new__(cls, *args, **kwargs):
        # Return a specialized version of this class if possible
        if len(args) >= 2:
            code = args[1]
            if code == 330:
                return SmscNumberUnknownError(args[0])
        return super(CmsError, cls).__new__(cls, *args, **kwargs)
    
    def __init__(self, command, code):
        super(CmsError, self).__init__(command, 'CMS', code)


class SmscNumberUnknownError(CmsError):
    """ Raised if the SMSC (service centre) address is missing when trying to send an SMS message """
    
    _description = 'SMSC number not set'

    def __init__(self, command, code=330):
        super(SmscNumberUnknownError, self).__init__(command, code)


class EncodingError(GsmModemException):
    """ Raised if a decoding- or encoding operation failed """
