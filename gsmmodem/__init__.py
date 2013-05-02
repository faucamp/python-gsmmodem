""" Package that allows easy control of an attached GSM modem 

The main class for controlling a modem is GsmModem, which can be imported
directly from this module.

Other important and useful classes are:
gsmmodem.modem.IncomingCall: wraps an incoming call and passed to the incoming call hanndler callback function
gsmmodem.modem.ReceivedSms: wraps a received SMS message and passed to the sms received hanndler callback function
gsmmodem.modem.SentSms: returned when sending SMS messages; used for tracking the status of the SMS message

All python-gsmmodem-specific exceptions are defined in the gsmmodem.modem.exceptions package.

@author: Francois Aucamp <francois.aucamp@gmail.com>
@license: LGPLv3+
"""

from .modem import GsmModem
