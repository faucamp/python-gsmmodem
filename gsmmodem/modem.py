#!/usr/bin/env python

import re, logging, weakref, time, threading, abc

from .serial_comms import SerialComms
from .exceptions import CommandError, InvalidStateException
from gsmmodem.exceptions import TimeoutException

class GsmModem(SerialComms):
    
    log = logging.getLogger('gsmmodem.modem.GsmModem')
    
    # Used for parsing AT command errors
    CM_ERROR_REGEX = re.compile(r'^\+(CM[ES]) ERROR: (\d+)$')
    # Used for parsing signal strength query responses
    CSQ_REGEX = re.compile(r'^\+CSQ:\s*(\d+),')
    # Used for parsing caller ID announcements for incoming calls. Group 1 is the number, group 3 is the caller's name (if available)
    CLIP_REGEX = re.compile(r'^\+CLIP:\s*"(\+{0,1}\d+)",\d+,[^,]*,[^,]*,("([^"]+)"|,.*)$')
    # Used for parsing new SMS message indications
    CMTI_REGEX = re.compile(r'^\+CMTI:\s*([^,]+),(\d+)$')
    # Used for parsing SMS message reads
    CMGR_SM_DELIVER_REGEX = re.compile(r'^\+CMGR:\s*"([^"]+)","([^"]+)",[^,]*,"([^"]+)"$')
    
    def __init__(self, port, baudrate=9600, incomingCallCallbackFunc=None, smsReceivedCallbackFunc=None):
        super(GsmModem, self).__init__(port, baudrate, notifyCallbackFunc=self._handleModemNotification)
        self.incomingCallCallback = incomingCallCallbackFunc or self._placeholderCallback
        self.smsReceivedCallback = smsReceivedCallbackFunc or self._placeholderCallback
        # Flag indicating whether caller ID for incoming call notification has been set up
        self._callingLineIdentification = False
        # Flag indicating whether incoming call notifications have extended information
        self._extendedIncomingCallIndication = False
        # Dict containing current active calls (ringing and/or answered)
        self.activeCalls = {}#weakref.WeakValueDictionary()
        # Dict containing sent SMS messages (to track their delivery status)
        self.sentSms = {}#weakref.WeakValueDictionary()
        
    def connect(self, runInit=True):
        self.log.debug('Connecting to modem on port {} at {}bps'.format(self.port, self.baudrate))
        super(GsmModem, self).connect()                
        # Send some initialization commands to the modem
        self.write('ATZ') # reset configuration
        self.write('ATE0') # echo off
        self.write('AT+CFUN=1') # enable full modem functionality
        self.write('AT+CMEE=1') # enable detailed error messages
        # disable misc notifications (we will enable what we need in a bit) - not all modems support this command; doesn't matter
        self.write('AT+WIND=0', parseError=False)        
        
        # SMS setup
        self.write('AT+CMGF=1') # Switch to text mode for SMS messages
        self.write('AT+CSMP=49,167') # Enable delivery reports
        self.write('AT+CPMS="SM","SM","SR"') # Set message storage
        self.write('AT+CNMI=2,1,0,2') # Set message notifications
        
        # Incoming call notification setup        
        try:
            self.write('AT+CLIP=1') # Enable calling line identification presentation
        except CommandError, clipError:
            self._callingLineIdentification = False
            self.log.warn('Incoming call calling line identification (caller ID) not supported by modem. Error: {}'.format(clipError))
        else:
            self._callingLineIdentification = True
            try:
                self.write('AT+CRC=1') # Enable extended format of incoming indication (optional)
            except CommandError, crcError:
                self._extendedIncomingCallIndication = False
                self.log.info('Extended format incoming call indication not supported by modem. Error: {}'.format(crcError))
            else:
                self._extendedIncomingCallIndication = True        

        # Call control setup
        self.write('AT+CVHU=0') # Enable call hang-up with ATH command

    def write(self, data, waitForResponse=True, timeout=5, parseError=True, writeTerm='\r', expectedResponseTermSeq=None):
        """ Write data to the modem
        
        This method adds the '\r\n' end-of-line sequence to the data parameter, and
        writes it to the modem
        
        @param data: Command/data to be written to the modem
        @param waitForResponse: Whether this method should block and return the response from the modem or not
        @param timeout: Maximum amount of time in seconds to wait for a response from the modem
        @param parseError: If True, a CommandError is raised if the modem responds with an error (otherwise the response is returned as-is) 

        @raise CommandError: if the command returns an error (only if parseError parameter is True)
        @raise TimeoutException: if no response to the command was received from the modem
        
        @return: A list containing the response lines from the modem, or None if waitForResponse is False
        """
        responseLines = SerialComms.write(self, data + writeTerm, waitForResponse=waitForResponse, timeout=timeout, expectedResponseTermSeq=expectedResponseTermSeq)
        if waitForResponse:
            cmdStatusLine = responseLines[-1]
            if parseError and 'ERROR' in cmdStatusLine:
                cmErrorMatch = self.CM_ERROR_REGEX.match(cmdStatusLine)
                if cmErrorMatch:
                    errorType, errorCode = cmErrorMatch.groups()
                    raise CommandError(errorType, int(errorCode))
                else:
                    raise CommandError()
            return responseLines
    
    @property
    def signalStrength(self):
        """ @return The network signal strength as an integer between 0 and 99, or -1 if it is unknown """
        csq = self.CSQ_REGEX.match(self.write('AT+CSQ')[0])
        if csq:
            ss = int(csq.group(1))
            return ss if ss != 99 else -1
        else:
            raise CommandError()
    
    def waitForNetworkCoverage(self, timeout=None):
        """ Block until the modem has GSM network coverage.
        
        This method blocks until the modem is registered with the network 
        and the signal strength is greater than 0, optionally timing out
        if a timeout was specified
        
        @param timeout: Maximum time to wait for network coverage, in seconds
        
        @raise TimeoutException: if a timeout was specified and reached
        
        @return: the current signal strength as an integer
        """
        block = [True]
        if timeout != None:
            # Set up a timeout mechanism
            def _cancelBlock():                
                block[0] = False                
            t = threading.Timer(timeout, _cancelBlock)
            t.start()
        ss = -1
        while block[0]:
            ss = self.signalStrength
            if ss:
                return ss
            time.sleep(1)
        else:
            # If this is reached, the timer task has triggered
            raise TimeoutException()
        
    def sendSms(self, destination, text, waitForDeliveryReport=False, deliveryTimeout=15):
        """ Send an SMS text message
        
        @param destination: The recipient's phone number
        @param text: The message text
        """
        sms = SentSms(destination, text)            
        self.write('AT+CMGS="{0}"'.format(destination), timeout=3, expectedResponseTermSeq='> ')    
        self.write(text, timeout=15, writeTerm=chr(26))
        return sms

    def _handleModemNotification(self, lines):
        """ Handler for unsolicited notifications from the modem
        
        This method simply spawns a separate thread to handle the actual notification
        (in order to release the read thread so that the handlers are able to write back to the modem, etc)
         
        @param lines The lines that were read
        """
        threading.Thread(target=self.__threadedHandleModemNotification, kwargs={'lines': lines}).start()
    
    def __threadedHandleModemNotification(self, lines):
        """ Implementation of _handleModemNotification() to be run in a separate thread 
        
        @param lines The lines that were read
        """
        firstLine = lines[0]
        if 'RING' in firstLine:
            # Incoming call (or existing call is ringing)
            self._handleIncomingCall(lines)
        elif firstLine.startswith('+CMTI'):
            # New SMS message indication
            self._handleSmsReceived(firstLine)
        else:
            self.log.debug('Unhandled unsolicited modem notification:', lines)
    
    def _handleIncomingCall(self, lines):
        ringLine = lines.pop(0)
        if self._extendedIncomingCallIndication:
            callType = ringLine.split(' ', 1)[1]
        else:
            callType = None
        if self._callingLineIdentification and len(lines) > 0:
            clipLine = lines.pop(0)
            clipMatch = self.CLIP_REGEX.match(clipLine)
            if clipMatch:
                callerNumber = clipMatch.group(1)
                ton = clipMatch.group(2)
                callerName = clipMatch.group(3)
                if callerName != None and len(callerName) == 0:
                    callerName = None
            else:
                callerNumber = ton = callerName = None
        else:
            callerNumber = ton = callerName = None
            
        if callerNumber in self.activeCalls:
            call = self.activeCalls[callerNumber]
            call.ringCount += 1
        else:        
            call = IncomingCall(self, callerNumber, ton, callerName, callType)
            self.activeCalls[callerNumber] = call        
        self.incomingCallCallback(call)
        
    def _handleSmsReceived(self, notificationLine):
        """ Handler for "new SMS" unsolicited notification line """
        cmtiMatch = self.CMTI_REGEX.match(notificationLine)
        if cmtiMatch:
            msgIndex = cmtiMatch.group(2)
            sms = self._readStoredSmsMessage(msgIndex)
            self._deleteStoredMessage(msgIndex)
            self.smsReceivedCallback(sms)            
    
    def _readStoredSmsMessage(self, msgIndex):
        msgData = self.write('AT+CMGR={}'.format(msgIndex))
        # Parse meta information
        cmgrMatch = self.CMGR_SM_DELIVER_REGEX.match(msgData[0])
        if not cmgrMatch:
            # TODO: provide more insight into error
            raise CommandError()
        msgStatus, number, msgTime = cmgrMatch.groups()
        msgText = '\n'.join(msgData[1:-1])
        return ReceivedSms(self, msgStatus, number, msgTime, msgText)
            
    def _deleteStoredMessage(self, msgIndex):
        self.write('AT+CMGD={}'.format(msgIndex))
    
    def _placeHolderCallback(self, *args):
        """ Does nothing """
        self.log.debug('called with args: {}'.format(args))


class IncomingCall(object):
    """ Represents an incoming call, conveniently allowing access to call meta information and -control """     
    def __init__(self, gsmModem, number, ton, callerName, callType):
        """
        @param gsmModem: GsmModem instance that created this object
        @param number: Caller number
        @param ton: TON (type of number/address) in integer format
        @param callType: Type of the incoming call (VOICE, FAX, DATA, etc)
        """
        self._gsmModem = weakref.proxy(gsmModem)
        # The number that is dialling
        self.number = number
        # Type attribute of the incoming call
        self.ton = ton
        self.callerName = callerName
        self.type = callType
        # Flag indicating whether the call is ringing or not
        self.ringing = True
        # Flag indicating whether the call has been answered or not
        self.answered = False
        # Amount of times this call has rung (before answer/hangup)
        self.ringCount = 1
    
    def answer(self):
        """ Answer the phone call.        
        @return: self (for chaining method calls)
        """
        if self.ringing:
            self._gsmModem.write('ATA')
            self.ringing = False
            self.answered = True
        return self
    
    def sendDtmfTone(self, tones):
        """ Send a DTMF tone to the remote party (only allowed for an answered call) 
        
        Note: this is highly device-dependent, and might not work
        
        @param digits: A str containining one or more DTMF tones to play, e.g. "3" or "*123#"

        @raise CommandError: if the command failed/is not supported
        """
        if self.answered:
            if len(tones) > 1:
                cmd = 'AT+VTS={}'.format(';+VTS='.join(tones))
            else:
                cmd = 'AT+VTS={}'.format(tones)            
            self._gsmModem.write(cmd)
        else:
            raise InvalidStateException('Call is not active (it has not yet been answered, or it has ended).')

    def hangup(self):
        """ End the phone call.        
        @return: self (for chaining method calls)
        """
        self._gsmModem.write('ATH')
        self.ringing = False
        self.answered = False
        if self.number in self._gsmModem.activeCalls:
            del self._gsmModem.activeCalls[self.number]


class Sms(object):
    """ Abstract SMS message base class """
    __metaclass__ = abc.ABCMeta
    
    def __init__(self, number, text):
        self.number = number
        self.text = text


class ReceivedSms(Sms):
    """ An SMS message that has been received (MT) """
    
    def __init__(self, gsmModem, status, number, time, text):
        super(ReceivedSms, self).__init__(number, text)
        self._gsmModem = weakref.proxy(gsmModem)
        self.status = status
        self.time = time
        
    def reply(self, message):
        """ Convenience method that sends a reply SMS to the sender of this message """
        return self._gsmModem.sendSms(self.number, message)


class SentSms(Sms):
    """ An SMS message that has been sent (MO) """
        
    ENROUTE = 0 # Status indicating message is still enroute to destination
    RECEIVED = 1 # Status indicating message has been received by destination handset
    
    def __init__(self, number, text):
        super(SentSms, self).__init__(number, text)
        self.status = SentSms.ENROUTE
    
        
    