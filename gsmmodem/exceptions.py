""" Module defines exceptions used by gsmmodem """

class GsmModemException(Exception):
    """ Base exception raised for error conditions when interacting with the GSM modem """

class TimeoutException(GsmModemException):
    """ Raised when a write command times out """

class InvalidStateException(GsmModemException):
    """ Raised when an API method call is invoked on an object that is in an incorrect state """
    
    def __init__(self, message):
        super(InvalidStateException, self).__init__(message)

class CommandError(GsmModemException):
    """ Raised if the modem returns an error in response to an AT command
     
    May optionally include an error type (CME or CMS) and -code (error-specific).
    """
    
    def __init__(self, type=None, code=None):
        self.type = type
        self.code = code
