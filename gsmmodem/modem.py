#!/usr/bin/env python

""" High-level API classes for an attached GSM modem """

import re, logging, weakref, time, threading, abc
from datetime import datetime

from .serial_comms import SerialComms
from .exceptions import CommandError, InvalidStateException, CmeError, CmsError, InterruptedException, TimeoutException
from .pdu import encodeSmsSubmitPdu, decodeSmsPdu
from .util import SimpleOffsetTzInfo

import compat # For Python 2.6 compatibility

class GsmModem(SerialComms):
    """ Main class for interacting with an attached GSM modem """
    
    log = logging.getLogger('gsmmodem.modem.GsmModem')

    # Used for parsing AT command errors
    CM_ERROR_REGEX = re.compile(r'^\+(CM[ES]) ERROR: (\d+)$')
    # Used for parsing signal strength query responses
    CSQ_REGEX = re.compile(r'^\+CSQ:\s*(\d+),')
    # Used for parsing caller ID announcements for incoming calls. Group 1 is the number
    CLIP_REGEX = re.compile(r'^\+CLIP:\s*"(\+{0,1}\d+)",(\d+).*$')
    # Used for parsing new SMS message indications
    CMTI_REGEX = re.compile(r'^\+CMTI:\s*([^,]+),(\d+)$')
    # Used for parsing SMS message reads (text mode)
    CMGR_SM_DELIVER_REGEX_TEXT = re.compile(r'^\+CMGR: "([^"]+)","([^"]+)",[^,]*,"([^"]+)"$')
    # Used for parsing SMS message reads (PDU mode)
    CMGR_SM_DELIVER_REGEX_PDU = re.compile(r'^\+CMGR: (\d+),(\d*),(\d+)$')
    # Used for parsing USSD event notifications
    CUSD_REGEX = re.compile(r'^\+CUSD:\s*(\d),"(.*)",(\d+)$', re.DOTALL)    
    
    def __init__(self, port, baudrate=115200, incomingCallCallbackFunc=None, smsReceivedCallbackFunc=None):
        super(GsmModem, self).__init__(port, baudrate, notifyCallbackFunc=self._handleModemNotification)
        self.incomingCallCallback = incomingCallCallbackFunc or self._placeholderCallback
        self.smsReceivedCallback = smsReceivedCallbackFunc or self._placeholderCallback
        # Flag indicating whether caller ID for incoming call notification has been set up
        self._callingLineIdentification = False
        # Flag indicating whether incoming call notifications have extended information
        self._extendedIncomingCallIndication = False
        # Current active calls (ringing and/or answered), key is the unique call ID (not the remote number)
        self.activeCalls = {}
        # Dict containing sent SMS messages (to track their delivery status)
        self.sentSms = {}
        self._ussdSessionEvent = None # threading.Event
        self._ussdResponse = None # gsmmodem.modem.Ussd
        self._dialEvent = None # threading.Event
        self._dialResponse = None # gsmmodem.modem.Call
        self._waitForAtdResponse = True # Flag that controls if we should wait for an immediate response to ATD, or not
        self.callStatusUpdates = [] # populated during connect() - contains regexes and handlers for detecting/handling call status updates
        self._writeWait = 0 # Time (in seconds to wait after writing a command (adjusted when 515 errors are detected)
        self._smsTextMode = False # Storage variable for the smsTextMode property
        
    def connect(self, runInit=True):
        """ Opens the port and initializes the modem """
        self.log.info('Connecting to modem on port %s at %dbps', self.port, self.baudrate)        
        super(GsmModem, self).connect()                
        # Send some initialization commands to the modem        
        self.write('ATZ') # reset configuration
        self.write('ATE0') # echo off
        try:
            cfun = int(self.write('AT+CFUN?')[0][7:]) # example response: +CFUN: 1
            if cfun != 1:
                self.write('AT+CFUN=1')
        except CommandError:
            pass # just ignore if the +CFUN command isn't supported
         
        self.write('AT+CMEE=1') # enable detailed error messages
        
        # Get list of supported commands from modem
        commands = self.supportedCommands

        # Device-specific settings
        if commands != None:
            if '^CVOICE' in commands:
                self.write('AT^CVOICE=0', parseError=False) # Enable voice calls
            if '+VTS' in commands: # Check for DTMF sending support
                Call.dtmfSupport = True
            elif '^DTMF' in commands:
                # Huawei modems use ^DTMF to send DTMF tones; use that instead
                Call.DTMF_COMMAND_BASE = '^DTMF=1,'
                Call.dtmfSupport = True
            
        # Enable general notifications on Wavecom-like devices - also use result to select the type of call status updates we will receive
        try:
            wind = self.write('AT+WIND?')[0] # Check current WIND value; example response: +WIND: 63            
            if int(wind[7:]) != 50:
                self.write('AT+WIND=50') # Enabled notifications for call setup, hangup, etc
        except CommandError:
            # Modem does not support +WIND notifications, use Hauwei's ^NOTIFICATIONs
            self.log.info('Loading Huawei call update table')
            self.callStatusUpdates = ((re.compile(r'^\^ORIG:(\d),(\d)$'), self._handleCallInitiated),
                                      (re.compile(r'^\^CONN:(\d),(\d)$'), self._handleCallAnswered),
                                      (re.compile(r'^\^CEND:(\d),(\d),(\d)+,(\d)+$'), self._handleCallEnded))            
            self._waitForAtdResponse = True # Huawei modems return OK immediately after issuing ATD            
        else:
            # +WIND notifications supported
            self.log.info('Loading Wavecom call update table')
            self.callStatusUpdates = ((re.compile(r'^\+WIND: 5,(\d)$'), self._handleCallInitiated),
                                      (re.compile(r'^OK$'), self._handleCallAnswered),
                                      (re.compile(r'^\+WIND: 6,(\d)$'), self._handleCallEnded))            
            self._waitForAtdResponse = False # Wavecom modems return OK only when the call is answered
            if commands == None: # older modem, assume it has standard DTMF support
                Call.dtmfSupport = True
        
        # General meta-information setup
        self.write('AT+COPS=3,0', parseError=False) # Use long alphanumeric name format
                
        # SMS setup
        self.write('AT+CMGF={0}'.format(1 if self._smsTextMode else 0)) # Switch to text or PDU mode for SMS messages
        self.write('AT+CSMP=49,167,0,0') # Enable delivery reports
        
        # Set message storage, but first check what the modem supports - example response: +CPMS: (("SM","BM","SR"),("SM"))
        lines = self.write('AT+CPMS=?')        
        cpmsSupport = lines[0].split(' ', 1)[1].split('),(')        
        cpmsItems = ['"SM"', '"SM"', '"SR"'][:len(cpmsSupport)]
        #cpmsItems = cpmsItems[:len(cpmsSupport)]
        for i in xrange(len(cpmsItems)):            
            if cpmsItems[i] not in cpmsSupport[i]:
                cpmsItems[i] = ''
        self.write('AT+CPMS={0}'.format(','.join(cpmsItems))) # Set message storage        
        #self.write('AT+CPMS="SM","SM","SR"') # Set message storage
        self.write('AT+CNMI=2,1,0,2') # Set message notifications
        
        # Incoming call notification setup        
        try:
            self.write('AT+CLIP=1') # Enable calling line identification presentation
        except CommandError, clipError:
            self._callingLineIdentification = False
            self.log.warn('Incoming call calling line identification (caller ID) not supported by modem. Error: {0}'.format(clipError))
        else:
            self._callingLineIdentification = True
            try:
                self.write('AT+CRC=1') # Enable extended format of incoming indication (optional)
            except CommandError, crcError:
                self._extendedIncomingCallIndication = False
                self.log.warn('Extended format incoming call indication not supported by modem. Error: {0}'.format(crcError))
            else:
                self._extendedIncomingCallIndication = True        

        # Call control setup
        self.write('AT+CVHU=0', parseError=False) # Enable call hang-up with ATH command (ignore if command not supported)
                    
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
        self.log.debug('write: %s', data)
        responseLines = SerialComms.write(self, data + writeTerm, waitForResponse=waitForResponse, timeout=timeout, expectedResponseTermSeq=expectedResponseTermSeq)
        if self._writeWait > 0: # Sleep a bit if required (some older modems suffer under load)            
            time.sleep(self._writeWait)
        if waitForResponse:
            cmdStatusLine = responseLines[-1]
            if parseError and 'ERROR' in cmdStatusLine:
                cmErrorMatch = self.CM_ERROR_REGEX.match(cmdStatusLine)
                if cmErrorMatch:
                    errorType = cmErrorMatch.group(1)
                    errorCode = int(cmErrorMatch.group(2))
                    if errorCode == 515:
                        # 515 means: "Please wait, init or command processing in progress."
                        self._writeWait += 0.2 # Increase waiting period temporarily
                        # Retry the command after waiting a bit
                        self.log.debug('515 error detected; self._writeWait adjusted to %ds', self._writeWait)
                        time.sleep(self._writeWait)
                        result = self.write(data, waitForResponse, timeout, parseError, writeTerm, expectedResponseTermSeq)
                        self.log.debug('self_writeWait set to 0.1 because of recovering from 515 error')
                        self._writeWait = 0.1 # Set this to something sane for further commands
                        return result
                    if errorType == 'CME':
                        raise CmeError(data, int(errorCode))
                    elif errorType == 'CMS':
                        raise CmsError(data, int(errorCode))
                    else:
                        raise CommandError(data, errorType, int(errorCode))
                else:
                    raise CommandError(data)
            return responseLines

    @property
    def signalStrength(self):
        """ @return: The network signal strength as an integer between 0 and 99, or -1 if it is unknown """
        csq = self.CSQ_REGEX.match(self.write('AT+CSQ')[0])
        if csq:
            ss = int(csq.group(1))
            return ss if ss != 99 else -1
        else:
            raise CommandError()

    @property
    def manufacturer(self):
        """ @return: The modem's manufacturer's name """
        return self.write('AT+CGMI')[0]
    
    @property
    def model(self):
        """ @return: The modem's model name """
        return self.write('AT+CGMM')[0]
    
    @property
    def revision(self):
        """ @return: The modem's software revision, or None if not known/supported """
        try:
            return self.write('AT+CGMR')[0]
        except CommandError:
            return None
    
    @property
    def imei(self):
        """ @return: The modem's serial number (IMEI number) """
        return self.write('AT+CGSN')[0]
    
    @property
    def imsi(self):
        """ @return: The IMSI (International Mobile Subscriber Identity) of the SIM card. The PIN may need to be entered before reading the IMSI """
        return self.write('AT+CIMI')[0]
    
    @property
    def networkName(self):
        """ @return: the name of the GSM Network Operator to which the modem is connected """
        response = self.write('AT+COPS?')[0] # response format: +COPS: mode,format,"operator_name",x
        copsMatch = re.match(r'^\+COPS: (\d),(\d),"(.+)",\d$', response[0])
        if copsMatch:
            return copsMatch.group(3)

    @property
    def supportedCommands(self):
        """ @return: list of AT commands supported by this modem (without the AT prefix). Returns None if not known """
        try:
            return self.write('AT+CLAC')[0][6:].split(',') # remove the +CLAC: prefix before splitting
        except CommandError:
            return None

    @property
    def smsTextMode(self):
        """ @return: True if the modem is set to use text mode for SMS, False if it is set to use PDU mode """
        return self._smsTextMode
    @smsTextMode.setter
    def smsTextMode(self, textMode):
        """ Set to True for the modem to use text mode for SMS, or False for it to use PDU mode """
        if textMode != self._smsTextMode:
            if self.alive:
                self.write('AT+CMGF={0}'.format(1 if textMode else 0))
            self._smsTextMode = textMode

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
        if self._smsTextMode:
            self.write('AT+CMGS="{0}"'.format(destination), timeout=3, expectedResponseTermSeq='> ')
            self.write(text, timeout=15, writeTerm=chr(26))
        else:
            smsPdu, tpduLength = encodeSmsSubmitPdu(destination, text)
            smsPduHex = str(smsPdu).encode('hex').upper()
            self.write('AT+CMGS={0}'.format(tpduLength), timeout=3, expectedResponseTermSeq='> ')
            self.write(smsPduHex, timeout=15, writeTerm=chr(26))
        return sms
    
    def sendUssd(self, ussdString, responseTimeout=15):
        """ Starts a USSD session by dialing the the specified USSD string, or \
        sends the specified string in the existing USSD session (if any)
                
        @param ussdString: The USSD access number to dial
        @param responseTimeout: Maximum time to wait a response, in seconds
        
        @raise TimeoutException: if no response is received in time
        
        @return: The USSD response message/session (as a Ussd object)
        @rtype: gsmmodem.modem.Ussd
        """
        self.write('AT+CUSD=1,"{0}",15'.format(ussdString)) # responds with "OK"
        # Wait for the +CUSD notification message
        self._ussdSessionEvent = threading.Event()
        if self._ussdSessionEvent.wait(responseTimeout):
            self._ussdSessionEvent = None
            return self._ussdResponse
        else: # Response timed out
            self._ussdSessionEvent = None            
            raise TimeoutException()
    
    def dial(self, number, timeout=5):
        """ Calls the specified phone number using a voice phone call
        
        @param number: The phone number to dial
        @param timeout: Maximum time to wait for the call to be established
        """
        self.write('ATD{0};'.format(number), waitForResponse=self._waitForAtdResponse)
        # Wait for the ^ORIG notification message
        self._dialEvent = threading.Event()
        if self._dialEvent.wait(timeout):
            self._dialEvent = None
            callId, callType = self._dialResponse
            call = Call(self, callId, callType, number)
            self.activeCalls[callId] = call
            return call
        else: # Call establishing timed out
            self._dialEvent = None            
            raise TimeoutException()

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
        #firstLine = lines[0]
        for line in lines:
            if 'RING' in line:
                # Incoming call (or existing call is ringing)
                self._handleIncomingCall(lines)
                return
            elif line.startswith('+CMTI'):
                # New SMS message indication
                self._handleSmsReceived(line)
                return
            elif line.startswith('+CUSD'):
                # USSD notification - either a response or a MT-USSD ("push USSD") message
                self._handleUssd(line)
                return
            else:
                # Check for call status updates            
                for updateRegex, handlerFunc in self.callStatusUpdates:
                    match = updateRegex.match(line)
                    if match:
                        # Handle the update
                        handlerFunc(match)
                        return
        # If this is reached, the notification wasn't handled
        self.log.debug('Unhandled unsolicited modem notification: %s', lines)    
    
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
                #TODO: re-add support for this
                callerName = None
                #callerName = clipMatch.group(3)
                #if callerName != None and len(callerName) == 0:
                #    callerName = None
            else:
                callerNumber = ton = callerName = None
        else:
            callerNumber = ton = callerName = None
        
        call = None
        for activeCall in self.activeCalls.itervalues():
            if activeCall.number == callerNumber:
                call = activeCall
                call.ringCount += 1
        if call == None:
            callId = len(self.activeCalls) + 1;
            call = IncomingCall(self, callerNumber, ton, callerName, callId, callType)
            self.activeCalls[callId] = call
        self.incomingCallCallback(call)
    
    def _handleCallInitiated(self, regexMatch):
        """ Handler for "outgoing call initiated" event notification line """
        if self._dialEvent:
            groups = regexMatch.groups()
            if len(groups) >= 2:                                
                self._dialResponse = (int(groups[0]) , int(groups[1]))
            else:
                self._dialResponse = (int(groups[0]), 1) # assume call type: VOICE
            self._dialEvent.set()
                
    def _handleCallAnswered(self, regexMatch):
        """ Handler for "outgoing call answered" event notification line """
        groups = regexMatch.groups()
        if len(groups) > 1:
            callId = int(groups[0])
            self.activeCalls[callId].answered = True
        else:
            # Call ID not available for this notificaiton - check for the first outgoing call that has not been answered
            for call in self.activeCalls.itervalues():
                if call.answered == False and type(call) == Call:
                    call.answered = True
                    return
    
    def _handleCallEnded(self, regexMatch):
        callId = int(regexMatch.group(1))
        if callId in self.activeCalls:
            self.activeCalls[callId].answered = False
            del self.activeCalls[callId]
    
    def _handleSmsReceived(self, notificationLine):
        """ Handler for "new SMS" unsolicited notification line """
        cmtiMatch = self.CMTI_REGEX.match(notificationLine)
        if cmtiMatch:
            msgIndex = cmtiMatch.group(2)
            sms = self._readStoredSmsMessage(msgIndex)
            self._deleteStoredMessage(msgIndex)
            self.smsReceivedCallback(sms)            
    
    def _readStoredSmsMessage(self, msgIndex):
        msgData = self.write('AT+CMGR={0}'.format(msgIndex))
        # Parse meta information
        if self._smsTextMode:
            cmgrMatch = self.CMGR_SM_DELIVER_REGEX_TEXT.match(msgData[0])
            if not cmgrMatch:
                raise CommandError('Failed to parse the SMS message +CMGR response: {0}'.format(msgData))
            msgStatus, number, msgTime = cmgrMatch.groups()
            msgText = '\n'.join(msgData[1:-1])
            # Parse date/time
            timeStr = msgTime[:-3]
            tzOffsetHours = int(msgTime[-3:])        
            parsedTime = datetime.strptime(timeStr, '%y/%m/%d,%H:%M:%S').replace(tzinfo=SimpleOffsetTzInfo(tzOffsetHours))
            return ReceivedSms(self, Sms.TEXT_MODE_STATUS_MAP[msgStatus], number, parsedTime, msgText)
        else:
            cmgrMatch = self.CMGR_SM_DELIVER_REGEX_PDU.match(msgData[0])
            if not cmgrMatch:
                raise CommandError('Failed to parse the SMS message +CMGR response: {0}'.format(msgData))
            stat, alpha, length = cmgrMatch.groups()
            pdu = msgData[1]
            smsDict = decodeSmsPdu(pdu)
            return ReceivedSms(self, int(stat), smsDict['number'], smsDict['time'], smsDict['text'], smsDict['smsc'])
            
    def _deleteStoredMessage(self, msgIndex):
        self.write('AT+CMGD={0}'.format(msgIndex))
    
    def _handleUssd(self, notificationLine):
        """ Handler for USSD event notification line """
        if self._ussdSessionEvent:
            # A sendUssd() call is waiting for this response - parse it
            cusdMatch = self.CUSD_REGEX.match(notificationLine)
            if cusdMatch:                
                self._ussdResponse = Ussd(self, (cusdMatch.group(1) == '1'), cusdMatch.group(2))                        
            # Notify waiting thread
            self._ussdSessionEvent.set()

    def _placeHolderCallback(self, *args):
        """ Does nothing """
        self.log.debug('called with args: {0}'.format(args))


class Call(object):
    """ A voice call """
    
    DTMF_COMMAND_BASE = '+VTS='    
    dtmfSupport = False # Indicates whether or not DTMF tones can be sent in calls
    
    def __init__(self, gsmModem, callId, callType, number):
        """
        @param gsmModem: GsmModem instance that created this object
        @param number: The number that is being called        
        """
        self._gsmModem = weakref.proxy(gsmModem)
        # Unique ID of this call
        self.id = callId
        # Call type (VOICE == 0, etc)
        self.type = callType        
        # The remote number of this call (destination or origin)
        self.number = number                
        # Flag indicating whether the call has been answered or not
        self.answered = False        
    
    def sendDtmfTone(self, tones):
        """ Send one or more DTMF tones to the remote party (only allowed for an answered call) 
        
        Note: this is highly device-dependent, and might not work
        
        @param digits: A str containining one or more DTMF tones to play, e.g. "3" or "*123#"

        @raise CommandError: if the command failed/is not supported        
        @raise InvalidStateException: if the call has not been answered, or is ended while the command is still executing
        """        
        if self.answered:
            toneLen = len(tones)
            if len(tones) > 1:
                cmd = ('AT{0}{1};{0}' + ';{0}'.join(tones[1:])).format(self.DTMF_COMMAND_BASE, tones[0])                
            else:
                cmd = 'AT+VTS={0}'.format(tones)
            try:
                self._gsmModem.write(cmd, timeout=(5 + toneLen))
            except CmeError, e:
                if e.code == 30:
                    # No network service - can happen if call is ended during DTMF transmission (but also if DTMF is sent immediately after call is answered)
                    raise InterruptedException('No network service', e)
                elif e.code == 3:
                    # Operation not allowed - can happen if call is ended during DTMF transmission
                    raise InterruptedException('Operation not allowed', e)
                else:
                    raise e
        else:
            raise InvalidStateException('Call is not active (it has not yet been answered, or it has ended).')
    
    def hangup(self):
        """ End the phone call. """
        self._gsmModem.write('ATH')
        self.answered = False
        if self.id in self._gsmModem.activeCalls:
            del self._gsmModem.activeCalls[self.id]


class IncomingCall(Call):
    
    CALL_TYPE_MAP = {'VOICE': 0}
    
    """ Represents an incoming call, conveniently allowing access to call meta information and -control """     
    def __init__(self, gsmModem, number, ton, callerName, callId, callType):
        """
        @param gsmModem: GsmModem instance that created this object
        @param number: Caller number
        @param ton: TON (type of number/address) in integer format
        @param callType: Type of the incoming call (VOICE, FAX, DATA, etc)
        """
        if type(callType) == str:
            callType = self.CALL_TYPE_MAP[callType] 
        super(IncomingCall, self).__init__(gsmModem, callId, callType, number)        
        # Type attribute of the incoming call
        self.ton = ton
        self.callerName = callerName        
        # Flag indicating whether the call is ringing or not
        self.ringing = True        
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

    def hangup(self):
        """ End the phone call. """
        self.ringing = False
        super(IncomingCall, self).hangup()


class Sms(object):
    """ Abstract SMS message base class """
    __metaclass__ = abc.ABCMeta
    
    # Some constants to ease handling SMS statuses
    STATUS_RECEIVED_UNREAD = 0
    STATUS_RECEIVED_READ = 1
    STATUS_STORED_UNSENT = 2
    STATUS_STORED_SENT = 3
    # ...and a handy converter for text mode statuses
    TEXT_MODE_STATUS_MAP = {'REC UNREAD': STATUS_RECEIVED_UNREAD,
                            'REC READ': STATUS_RECEIVED_READ,
                            'STO UNSENT': STATUS_STORED_UNSENT,
                            'STO SENT': STATUS_STORED_SENT}

    def __init__(self, number, text, smsc=None):
        self.number = number
        self.text = text
        self.smsc = smsc


class ReceivedSms(Sms):
    """ An SMS message that has been received (MT) """
    
    def __init__(self, gsmModem, status, number, time, text, smsc=None):
        super(ReceivedSms, self).__init__(number, text, smsc)
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
    
    def __init__(self, number, text, smsc=None):
        super(SentSms, self).__init__(number, text, smsc)
        self.status = SentSms.ENROUTE

class Ussd(object):
    """ Unstructured Supplementary Service Data (USSD) message.
    
    This class contains convenient methods for replying to a USSD prompt
    and to cancel the USSD session
    """
    
    def __init__(self, gsmModem, sessionActive, message):
        self._gsmModem = weakref.proxy(gsmModem)
        # Indicates if the session is active (True) or has been closed (False)
        self.sessionActive = sessionActive
        self.message = message
    
    def reply(self, message):
        """ Sends a reply to this USSD message in the same USSD session 
        
        @raise InvalidStateException: if the USSD session is not active (i.e. it has ended)
        
        @return: The USSD response message/session (as a Ussd object)
        """
        if self.sessionActive:
            return self._gsmModem.sendUssd(message)
        else:
            raise InvalidStateException('USSD session is inactive')
                
    def cancel(self):
        """ Terminates/cancels the USSD session (without sending a reply)
        
        Does nothing if the USSD session is inactive.
        """
        if self.sessionActive:
            self._gsmModem.write('AT+CUSD=2')
