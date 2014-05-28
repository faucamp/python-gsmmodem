# -*- coding: utf8 -*-

""" SMS PDU encoding methods """

from __future__ import unicode_literals

import sys, codecs, math
from datetime import datetime, timedelta, tzinfo
from copy import copy
from .exceptions import EncodingError

# For Python 3 support
PYTHON_VERSION = sys.version_info[0]
if PYTHON_VERSION >= 3:
    MAX_INT = sys.maxsize
    dictItemsIter = dict.items
    xrange = range
    unichr = chr
    toByteArray = lambda x: bytearray(codecs.decode(x, 'hex_codec')) if type(x) == bytes else bytearray(codecs.decode(bytes(x, 'ascii'), 'hex_codec')) if type(x)  == str else x
    rawStrToByteArray = lambda x: bytearray(bytes(x, 'latin-1'))
else: #pragma: no cover
    MAX_INT = sys.maxint
    dictItemsIter = dict.iteritems
    toByteArray = lambda x: bytearray(x.decode('hex')) if type(x) in (str, unicode) else x
    rawStrToByteArray = bytearray

# Tables can be found at: http://en.wikipedia.org/wiki/GSM_03.38#GSM_7_bit_default_alphabet_and_extension_table_of_3GPP_TS_23.038_.2F_GSM_03.38
GSM7_BASIC = ('@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ\x1bÆæßÉ !\"#¤%&\'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ`¿abcdefghijklmnopqrstuvwxyzäöñüà')
GSM7_EXTENDED = {chr(0xFF): 0x0A,
                 #CR2: chr(0x0D),
                 '^':  chr(0x14),
                 #SS2: chr(0x1B),
                 '{':  chr(0x28),
                 '}':  chr(0x29),
                 '\\': chr(0x2F),
                 '[':  chr(0x3C),
                 '~':  chr(0x3D),
                 ']':  chr(0x3E),
                 '|':  chr(0x40),
                 '€':  chr(0x65)}
# Maximum message sizes for each data coding
MAX_MESSAGE_LENGTH = {0x00: 160, # GSM-7
                      0x04: 140, # 8-bit
                      0x08: 70}  # UCS2

class SmsPduTzInfo(tzinfo):
    """ Simple implementation of datetime.tzinfo for handling timestamp GMT offsets specified in SMS PDUs """
    
    def __init__(self, pduOffsetStr=None):
        """ 
        :param pduOffset: 2 semi-octet timezone offset as specified by PDU (see GSM 03.40 spec)
        :type pduOffset: str 
        
        Note: pduOffsetStr is optional in this constructor due to the special requirement for pickling
        mentioned in the Python docs. It should, however, be used (or otherwise pduOffsetStr must be
        manually set)
        """        
        self._offset = None
        if pduOffsetStr != None:
            self._setPduOffsetStr(pduOffsetStr)
        
    def _setPduOffsetStr(self, pduOffsetStr):
        # See if the timezone difference is positive/negative by checking MSB of first semi-octet
        tzHexVal = int(pduOffsetStr, 16)
        if tzHexVal & 0x80 == 0: # positive
            self._offset = timedelta(minutes=(int(pduOffsetStr) * 15))
        else: # negative
            self._offset = timedelta(minutes=(int('{0:0>2X}'.format(tzHexVal & 0x7F)) * -15))
    
    def utcoffset(self, dt):
        return self._offset
    
    def dst(self, dt):
        """ We do not have enough info in the SMS PDU to implement daylight savings time """
        return timedelta(0)


class InformationElement(object):
    """ User Data Header (UDH) Information Element (IE) implementation
     
    This represents a single field ("information element") in the PDU's
    User Data Header. The UDH itself contains one or more of these
    information elements.
    
    If the IEI (IE identifier) is recognized, the class will automatically
    specialize into one of the subclasses of InformationElement, 
    e.g. Concatenation or PortAddress, allowing the user to easily
    access the specific (and useful) attributes of these special cases.
    """
    
    def __new__(cls, *args, **kwargs): #iei, ieLen, ieData):
        """ Causes a new InformationElement class, or subclass
        thereof, to be created. If the IEI is recognized, a specific
        subclass of InformationElement is returned """
        if len(args) > 0:
            targetClass = IEI_CLASS_MAP.get(args[0], cls)
        elif 'iei' in kwargs:
            targetClass = IEI_CLASS_MAP.get(kwargs['iei'], cls)
        else:
            return super(InformationElement, cls).__new__(cls)
        return super(InformationElement, targetClass).__new__(targetClass)
    
    def __init__(self, iei, ieLen=0, ieData=None):
        self.id = iei # IEI
        self.dataLength = ieLen # IE Length
        self.data = ieData or [] # raw IE data
        
    @classmethod
    def decode(cls, byteIter):
        """ Decodes a single IE at the current position in the specified
        byte iterator 
        
        :return: An InformationElement (or subclass) instance for the decoded IE
        :rtype: InformationElement, or subclass thereof
        """
        iei = next(byteIter)
        ieLen = next(byteIter)
        ieData = []
        for i in xrange(ieLen):
            ieData.append(next(byteIter))
        return InformationElement(iei, ieLen, ieData)
    
    def encode(self):
        """ Encodes this IE and returns the resulting bytes """
        result = bytearray()
        result.append(self.id)
        result.append(self.dataLength)
        result.extend(self.data)
        return result
    
    def __len__(self):
        """ Exposes the IE's total length (including the IEI and IE length octet) in octets """
        return self.dataLength + 2


class Concatenation(InformationElement):
    """ IE that indicates SMS concatenation.

    This implementation handles both 8-bit and 16-bit concatenation
    indication, and exposes the specific useful details of this
    IE as instance variables.

    Exposes:

    reference
        CSMS reference number, must be same for all the SMS parts in the CSMS
    parts
        total number of parts. The value shall remain constant for every short
        message which makes up the concatenated short message. If the value is zero then
        the receiving entity shall ignore the whole information element
    number
        this part's number in the sequence. The value shall start at 1 and
        increment for every short message which makes up the concatenated short message
    """

    def __init__(self, iei=0x00, ieLen=0, ieData=None):
        super(Concatenation, self).__init__(iei, ieLen, ieData)
        if ieData != None:
            if iei == 0x00: # 8-bit reference
                self.reference, self.parts, self.number = ieData
            else: # 0x08: 16-bit reference
                self.reference = ieData[0] << 8 | ieData[1]
                self.parts = ieData[2]
                self.number = ieData[3]

    def encode(self):
        if self.reference > 0xFF:
            self.id = 0x08 # 16-bit reference
            self.data = [self.reference >> 8, self.reference & 0xFF, self.parts, self.number]
        else:
            self.id = 0x00 # 8-bit reference
            self.data = [self.reference, self.parts, self.number]
        self.dataLength = len(self.data)
        return super(Concatenation, self).encode()


class PortAddress(InformationElement):
    """ IE that indicates an Application Port Addressing Scheme.
    
    This implementation handles both 8-bit and 16-bit concatenation
    indication, and exposes the specific useful details of this
    IE as instance variables.
    
    Exposes:
    destination: The destination port number
    source: The source port number
    """
    
    def __init__(self, iei=0x04, ieLen=0, ieData=None):
        super(PortAddress, self).__init__(iei, ieLen, ieData)
        if ieData != None:
            if iei == 0x04: # 8-bit port addressing scheme
                self.destination, self.source = ieData
            else: # 0x05: 16-bit port addressing scheme
                self.destination = ieData[0] << 8 | ieData[1]
                self.source = ieData[2] << 8 | ieData[3]
    
    def encode(self):
        if self.destination > 0xFF or self.source > 0xFF:
            self.id = 0x05 # 16-bit
            self.data = [self.destination >> 8, self.destination & 0xFF, self.source >> 8, self.source & 0xFF]
        else:
            self.id = 0x04 # 8-bit
            self.data = [self.destination, self.source]
        self.dataLength = len(self.data)
        return super(PortAddress, self).encode()


# Map of recognized IEIs
IEI_CLASS_MAP = {0x00: Concatenation, # Concatenated short messages, 8-bit reference number
                 0x08: Concatenation, # Concatenated short messages, 16-bit reference number
                 0x04: PortAddress, # Application port addressing scheme, 8 bit address
                 0x05: PortAddress # Application port addressing scheme, 16 bit address
                }


class Pdu(object):
    """ Encoded SMS PDU. Contains raw PDU data and related meta-information """
    
    def __init__(self, data, tpduLength):
        """ Constructor
        :param data: the raw PDU data (as bytes)
        :type data: bytearray
        :param tpduLength: Length (in bytes) of the TPDU
        :type tpduLength: int
        """
        self.data = data
        self.tpduLength = tpduLength
    
    def __str__(self):
        global PYTHON_VERSION
        if PYTHON_VERSION < 3:
            return str(self.data).encode('hex').upper()
        else: #pragma: no cover
            return str(codecs.encode(self.data, 'hex_codec'), 'ascii').upper() 


def encodeSmsSubmitPdu(number, text, reference=0, validity=None, smsc=None, requestStatusReport=True, rejectDuplicates=False, sendFlash=False):
    """ Creates an SMS-SUBMIT PDU for sending a message with the specified text to the specified number
    
    :param number: the destination mobile number
    :type number: str
    :param text: the message text
    :type text: str
    :param reference: message reference number (see also: rejectDuplicates parameter)
    :type reference: int
    :param validity: message validity period (absolute or relative)
    :type validity: datetime.timedelta (relative) or datetime.datetime (absolute)
    :param smsc: SMSC number to use (leave None to use default)
    :type smsc: str
    :param rejectDuplicates: Flag that controls the TP-RD parameter (messages with same destination and reference may be rejected if True)
    :type rejectDuplicates: bool
            
    :return: A list of one or more tuples containing the SMS PDU (as a bytearray, and the length of the TPDU part
    :rtype: list of tuples
    """     
    tpduFirstOctet = 0x01 # SMS-SUBMIT PDU
    if validity != None:
        # Validity period format (TP-VPF) is stored in bits 4,3 of the first TPDU octet
        if type(validity) == timedelta:
            # Relative (TP-VP is integer)
            tpduFirstOctet |= 0x10 # bit4 == 1, bit3 == 0
            validityPeriod = [_encodeRelativeValidityPeriod(validity)]
        elif type(validity) == datetime:
            # Absolute (TP-VP is semi-octet encoded date)
            tpduFirstOctet |= 0x18 # bit4 == 1, bit3 == 1
            validityPeriod = _encodeTimestamp(validity) 
        else:
            raise TypeError('"validity" must be of type datetime.timedelta (for relative value) or datetime.datetime (for absolute value)')        
    else:
        validityPeriod = None
    if rejectDuplicates:
        tpduFirstOctet |= 0x04 # bit2 == 1
    if requestStatusReport:
        tpduFirstOctet |= 0x20 # bit5 == 1
    
    # Encode message text and set data coding scheme based on text contents
    try:
        encodedText = encodeGsm7(text)
    except ValueError:
        # Cannot encode text using GSM-7; use UCS2 instead
        alphabet = 0x08 # UCS2
    else:
        alphabet = 0x00 # GSM-7    
        
    # Check if message should be concatenated
    if len(text) > MAX_MESSAGE_LENGTH[alphabet]:
        # Text too long for single PDU - add "concatenation" User Data Header
        concatHeaderPrototype = Concatenation()
        concatHeaderPrototype.reference = reference
        pduCount = int(len(text) / MAX_MESSAGE_LENGTH[alphabet]) + 1
        concatHeaderPrototype.parts  = pduCount
        tpduFirstOctet |= 0x40
    else:
        concatHeaderPrototype = None
        pduCount = 1
    
    # Construct required PDU(s)
    pdus = []    
    for i in xrange(pduCount):
        pdu = bytearray()
        if smsc:
            pdu.extend(_encodeAddressField(smsc, smscField=True))
        else:
            pdu.append(0x00) # Don't supply an SMSC number - use the one configured in the device 
    
        udh = bytearray()
        if concatHeaderPrototype != None:
            concatHeader = copy(concatHeaderPrototype)
            concatHeader.number = i + 1
            if alphabet == 0x00:
                pduText = text[i*153:(i+1) * 153]
            elif alphabet == 0x08:
                pduText = text[i * 67 : (i + 1) * 67]
            udh.extend(concatHeader.encode())
        else:
            pduText = text
        
        udhLen = len(udh)        
        
        pdu.append(tpduFirstOctet)
        pdu.append(reference) # message reference
        # Add destination number    
        pdu.extend(_encodeAddressField(number))
        pdu.append(0x00) # Protocol identifier - no higher-level protocol
    
        pdu.append(alphabet if not sendFlash else (0x10 if alphabet == 0x00 else 0x18))
        if validityPeriod:
            pdu.extend(validityPeriod)
        
        if alphabet == 0x00: # GSM-7
            encodedText = encodeGsm7(pduText)
            userDataLength = len(encodedText) # Payload size in septets/characters
            if udhLen > 0:
                shift = ((udhLen + 1) * 8) % 7 # "fill bits" needed to make the UDH end on a septet boundary
                userData = packSeptets(encodedText, padBits=shift)
                if shift > 0:
                    userDataLength += 1 # take padding bits into account
            else:
                userData = packSeptets(encodedText)
        elif alphabet == 0x08: # UCS2
            userData = encodeUcs2(pduText)
            userDataLength = len(userData)
          
        if udhLen > 0:            
            userDataLength += udhLen + 1 # +1 for the UDH length indicator byte
            pdu.append(userDataLength)
            pdu.append(udhLen)
            pdu.extend(udh) # UDH
        else:
            pdu.append(userDataLength)
        pdu.extend(userData) # User Data (message payload)
        tpdu_length = len(pdu) - 1
        pdus.append(Pdu(pdu, tpdu_length))
    return pdus

def decodeSmsPdu(pdu):
    """ Decodes SMS pdu data and returns a tuple in format (number, text)
    
    :param pdu: PDU data as a hex string, or a bytearray containing PDU octects
    :type pdu: str or bytearray
    
    :raise EncodingError: If the specified PDU data cannot be decoded
    
    :return: The decoded SMS data as a dictionary
    :rtype: dict    
    """ 
    try:
        pdu = toByteArray(pdu)
    except Exception as e:
        # Python 2 raises TypeError, Python 3 raises binascii.Error
        raise EncodingError(e)
    result = {}
    pduIter = iter(pdu)
 
    smscNumber, smscBytesRead = _decodeAddressField(pduIter, smscField=True)
    result['smsc'] = smscNumber
    result['tpdu_length'] = len(pdu) - smscBytesRead
    
    tpduFirstOctet = next(pduIter) 
    
    pduType = tpduFirstOctet & 0x03 # bits 1-0
    if pduType == 0x00: # SMS-DELIVER or SMS-DELIVER REPORT
        result['type'] = 'SMS-DELIVER'
        result['number'] = _decodeAddressField(pduIter)[0]
        result['protocol_id'] = next(pduIter)
        dataCoding = _decodeDataCoding(next(pduIter))
        result['time'] = _decodeTimestamp(pduIter)
        userDataLen = next(pduIter)
        udhPresent = (tpduFirstOctet & 0x40) != 0
        ud = _decodeUserData(pduIter, userDataLen, dataCoding, udhPresent)
        result.update(ud)
    elif pduType == 0x01: # SMS-SUBMIT or SMS-SUBMIT-REPORT
        result['type'] = 'SMS-SUBMIT'
        result['reference'] = next(pduIter) # message reference - we don't really use this
        result['number'] = _decodeAddressField(pduIter)[0]
        result['protocol_id'] = next(pduIter)
        dataCoding = _decodeDataCoding(next(pduIter))
        validityPeriodFormat = (tpduFirstOctet & 0x18) >> 3 # bits 4,3
        if validityPeriodFormat == 0x02: # TP-VP field present and integer represented (relative)
            result['validity'] = _decodeRelativeValidityPeriod(next(pduIter))
        elif validityPeriodFormat == 0x03: # TP-VP field present and semi-octet represented (absolute)            
            result['validity'] = _decodeTimestamp(pduIter)
        userDataLen = next(pduIter)
        udhPresent = (tpduFirstOctet & 0x40) != 0
        ud = _decodeUserData(pduIter, userDataLen, dataCoding, udhPresent)
        result.update(ud)
    elif pduType == 0x02: # SMS-STATUS-REPORT or SMS-COMMAND
        result['type'] = 'SMS-STATUS-REPORT'
        result['reference'] = next(pduIter)
        result['number'] = _decodeAddressField(pduIter)[0]
        result['time'] = _decodeTimestamp(pduIter)
        result['discharge'] = _decodeTimestamp(pduIter)
        result['status'] = next(pduIter)        
    else:
        raise EncodingError('Unknown SMS message type: {0}. First TPDU octet was: {1}'.format(pduType, tpduFirstOctet))
    
    return result

def _decodeUserData(byteIter, userDataLen, dataCoding, udhPresent):
    """ Decodes PDU user data (UDHI (if present) and message text) """
    result = {}
    if udhPresent:
        # User Data Header is present
        result['udh'] = []
        udhLen = next(byteIter)
        ieLenRead = 0
        # Parse and store UDH fields
        while ieLenRead < udhLen:
            ie = InformationElement.decode(byteIter)
            ieLenRead += len(ie)
            result['udh'].append(ie)
        del ieLenRead
        if dataCoding == 0x00: # GSM-7
            # Since we are using 7-bit data, "fill bits" may have been added to make the UDH end on a septet boundary
            shift = ((udhLen + 1) * 8) % 7 # "fill bits" needed to make the UDH end on a septet boundary
            # Simulate another "shift" in the unpackSeptets algorithm in order to ignore the fill bits
            prevOctet = next(byteIter)
            shift += 1

    if dataCoding == 0x00: # GSM-7
        if udhPresent:
            userDataSeptets = unpackSeptets(byteIter, userDataLen, prevOctet, shift)
        else:
            userDataSeptets = unpackSeptets(byteIter, userDataLen)
        result['text'] = decodeGsm7(userDataSeptets)
    elif dataCoding == 0x02: # UCS2
        result['text'] = decodeUcs2(byteIter, userDataLen)
    else: # 8-bit (data)
        userData = []
        for b in byteIter:
            userData.append(unichr(b))
        result['text'] = ''.join(userData)
    return result

def _decodeRelativeValidityPeriod(tpVp):
    """ Calculates the relative SMS validity period (based on the table in section 9.2.3.12 of GSM 03.40)
    :rtype: datetime.timedelta
    """
    if tpVp <= 143:
        return timedelta(minutes=((tpVp + 1) * 5))
    elif 144 <= tpVp <= 167:
        return timedelta(hours=12, minutes=((tpVp - 143) * 30))
    elif 168 <= tpVp <= 196:
        return timedelta(days=(tpVp - 166))
    elif 197 <= tpVp <= 255:
        return timedelta(weeks=(tpVp - 192))
    else:
        raise ValueError('tpVp must be in range [0, 255]')

def _encodeRelativeValidityPeriod(validityPeriod):
    """ Encodes the specified relative validity period timedelta into an integer for use in an SMS PDU
    (based on the table in section 9.2.3.12 of GSM 03.40)
    
    :param validityPeriod: The validity period to encode
    :type validityPeriod: datetime.timedelta
    :rtype: int
    """
    # Python 2.6 does not have timedelta.total_seconds(), so compute it manually
    #seconds = validityPeriod.total_seconds()
    seconds = validityPeriod.seconds + (validityPeriod.days * 24 * 3600)
    if seconds <= 43200: # 12 hours
        tpVp = int(seconds / 300) - 1 # divide by 5 minutes, subtract 1
    elif seconds <= 86400: # 24 hours
        tpVp = int((seconds - 43200) / 1800) + 143 # subtract 12 hours, divide by 30 minutes. add 143
    elif validityPeriod.days <= 30: # 30 days
        tpVp = validityPeriod.days + 166 # amount of days + 166
    elif validityPeriod.days <= 441: # max value of tpVp is 255
        tpVp = int(validityPeriod.days / 7) + 192 # amount of weeks + 192
    else:
        raise ValueError('Validity period too long; tpVp limited to 1 octet (max value: 255)')
    return tpVp
        
def _decodeTimestamp(byteIter):
    """ Decodes a 7-octet timestamp """
    dateStr = decodeSemiOctets(byteIter, 7)
    timeZoneStr = dateStr[-2:]        
    return datetime.strptime(dateStr[:-2], '%y%m%d%H%M%S').replace(tzinfo=SmsPduTzInfo(timeZoneStr))

def _encodeTimestamp(timestamp):
    """ Encodes a 7-octet timestamp from the specified date
    
    Note: the specified timestamp must have a UTC offset set; you can use gsmmodem.util.SimpleOffsetTzInfo for simple cases
    
    :param timestamp: The timestamp to encode
    :type timestamp: datetime.datetime
    
    :return: The encoded timestamp
    :rtype: bytearray
    """
    if timestamp.tzinfo == None:
        raise ValueError('Please specify time zone information for the timestamp (e.g. by using gsmmodem.util.SimpleOffsetTzInfo)')

    # See if the timezone difference is positive/negative
    tzDelta = timestamp.utcoffset()
    if tzDelta.days >= 0:
        tzValStr = '{0:0>2}'.format(int(tzDelta.seconds / 60 / 15))
    else: # negative
        tzVal = int((tzDelta.days * -3600 * 24 - tzDelta.seconds) / 60 / 15) # calculate offset in 0.25 hours
        # Cast as literal hex value and set MSB of first semi-octet of timezone to 1 to indicate negative value
        tzVal = int('{0:0>2}'.format(tzVal), 16) | 0x80
        tzValStr = '{0:0>2X}'.format(tzVal)

    dateStr = timestamp.strftime('%y%m%d%H%M%S') + tzValStr

    return encodeSemiOctets(dateStr)

def _decodeDataCoding(octet):
    if octet & 0xC0 == 0:
        #compressed = octect & 0x20
        alphabet = (octet & 0x0C) >> 2
        return alphabet # 0x00 == GSM-7, 0x01 == 8-bit data, 0x02 == UCS2
    # We ignore other coding groups
    return 0    

def _decodeAddressField(byteIter, smscField=False, log=False):
    """ Decodes the address field at the current position of the bytearray iterator
    
    :param byteIter: Iterator over bytearray
    :type byteIter: iter(bytearray) 
    
    :return: Tuple containing the address value and amount of bytes read (value is or None if it is empty (zero-length))
    :rtype: tuple
    """
    addressLen = next(byteIter)
    if addressLen > 0:
        toa = next(byteIter)
        ton = (toa & 0x70) # bits 6,5,4 of type-of-address == type-of-number
        if ton == 0x50: 
            # Alphanumberic number            
            addressLen = int(math.ceil(addressLen / 2.0))
            septets = unpackSeptets(byteIter, addressLen)
            addressValue = decodeGsm7(septets)
            return (addressValue, (addressLen + 2))
        else:
            # ton == 0x00: Unknown (might be international, local, etc) - leave as is            
            # ton == 0x20: National number
            if smscField:
                addressValue = decodeSemiOctets(byteIter, addressLen-1)
            else:
                if addressLen % 2:
                    addressLen = int(addressLen / 2) + 1
                else:
                    addressLen = int(addressLen / 2)                
                addressValue = decodeSemiOctets(byteIter, addressLen)
                addressLen += 1 # for the return value, add the toa byte
            if ton == 0x10: # International number
                addressValue = '+' + addressValue
            return (addressValue, (addressLen + 1))
    else:
        return (None, 1)

def _encodeAddressField(address, smscField=False):
    """ Encodes the address into an address field
    
    :param address: The address to encode (phone number or alphanumeric)
    :type byteIter: str
    
    :return: Encoded SMS PDU address field
    :rtype: bytearray
    """
    # First, see if this is a number or an alphanumeric string
    toa = 0x80 | 0x00 | 0x01 # Type-of-address start | Unknown type-of-number | ISDN/tel numbering plan
    alphaNumeric = False    
    if address.isalnum():
        # Might just be a local number
        if address.isdigit():
            # Local number
            toa |= 0x20
        else:
            # Alphanumeric address
            toa |= 0x50
            toa &= 0xFE # switch to "unknown" numbering plan
            alphaNumeric = True
    else:
        if address[0] == '+' and address[1:].isdigit():
            # International number
            toa |= 0x10
            # Remove the '+' prefix
            address = address[1:]
        else:
            # Alphanumeric address
            toa |= 0x50
            toa &= 0xFE # switch to "unknown" numbering plan
            alphaNumeric = True
    if  alphaNumeric:
        addressValue = packSeptets(encodeGsm7(address, False))
        addressLen = len(addressValue) * 2        
    else:
        addressValue = encodeSemiOctets(address)
        if smscField:            
            addressLen = len(addressValue) + 1
        else:
            addressLen = len(address)
    result = bytearray()
    result.append(addressLen)
    result.append(toa)
    result.extend(addressValue)
    return result

def encodeSemiOctets(number):
    """ Semi-octet encoding algorithm (e.g. for phone numbers)
        
    :return: bytearray containing the encoded octets
    :rtype: bytearray
    """
    if len(number) % 2 == 1:
        number = number + 'F' # append the "end" indicator
    octets = [int(number[i+1] + number[i], 16) for i in xrange(0, len(number), 2)]
    return bytearray(octets)

def decodeSemiOctets(encodedNumber, numberOfOctets=None):
    """ Semi-octet decoding algorithm(e.g. for phone numbers)
    
    :param encodedNumber: The semi-octet-encoded telephone number (in bytearray format or hex string)
    :type encodedNumber: bytearray, str or iter(bytearray)
    :param numberOfOctets: The expected amount of octets after decoding (i.e. when to stop)
    :type numberOfOctets: int
    
    :return: decoded telephone number
    :rtype: string
    """
    number = []
    if type(encodedNumber) in (str, bytes):
        encodedNumber = bytearray(codecs.decode(encodedNumber, 'hex_codec'))
    i = 0
    for octet in encodedNumber:        
        hexVal = hex(octet)[2:].zfill(2)   
        number.append(hexVal[1])
        if hexVal[0] != 'f':
            number.append(hexVal[0])
        else:
            break
        if numberOfOctets != None:
            i += 1
            if i == numberOfOctets:
                break
    return ''.join(number)

def encodeGsm7(plaintext, discardInvalid=False):
    """ GSM-7 text encoding algorithm
    
    Encodes the specified text string into GSM-7 octets (characters). This method does not pack
    the characters into septets.
    
    :param text: the text string to encode
    :param discardInvalid: if True, characters that cannot be encoded will be silently discarded 
    
    :raise ValueError: if the text string cannot be encoded using GSM-7 encoding (unless discardInvalid == True)
    
    :return: A bytearray containing the string encoded in GSM-7 encoding
    :rtype: bytearray
    """
    result = bytearray()
    if PYTHON_VERSION >= 3: 
        plaintext = str(plaintext)
    for char in plaintext:
        idx = GSM7_BASIC.find(char)
        if idx != -1:
            result.append(idx)
        elif char in GSM7_EXTENDED:
            result.append(0x1B) # ESC - switch to extended table
            result.append(ord(GSM7_EXTENDED[char]))
        elif not discardInvalid:
            raise ValueError('Cannot encode char "{0}" using GSM-7 encoding'.format(char))
    return result

def decodeGsm7(encodedText):
    """ GSM-7 text decoding algorithm
    
    Decodes the specified GSM-7-encoded string into a plaintext string.
    
    :param encodedText: the text string to encode
    :type encodedText: bytearray or str
    
    :return: A string containing the decoded text
    :rtype: str
    """
    result = []
    if type(encodedText) == str:
        encodedText = rawStrToByteArray(encodedText) #bytearray(encodedText)
    iterEncoded = iter(encodedText)
    for b in iterEncoded:
        if b == 0x1B: # ESC - switch to extended table
            c = chr(next(iterEncoded))
            for char, value in dictItemsIter(GSM7_EXTENDED):
                if c == value:
                    result.append(char)
                    break
        else:
            result.append(GSM7_BASIC[b])
    return ''.join(result)

def packSeptets(octets, padBits=0):
    """ Packs the specified octets into septets
    
    Typically the output of encodeGsm7 would be used as input to this function. The resulting
    bytearray contains the original GSM-7 characters packed into septets ready for transmission.
    
    :rtype: bytearray
    """
    result = bytearray()    
    if type(octets) == str:
        octets = iter(rawStrToByteArray(octets))
    elif type(octets) == bytearray:
        octets = iter(octets)
    shift = padBits
    if padBits == 0:
        prevSeptet = next(octets)
    else:
        prevSeptet = 0x00
    for octet in octets:
        septet = octet & 0x7f;
        if shift == 7:
            # prevSeptet has already been fully added to result
            shift = 0        
            prevSeptet = septet
            continue            
        b = ((septet << (7 - shift)) & 0xFF) | (prevSeptet >> shift)
        prevSeptet = septet
        shift += 1
        result.append(b)    
    if shift != 7:
        # There is a bit "left over" from prevSeptet
        result.append(prevSeptet >> shift)
    return result

def unpackSeptets(septets, numberOfSeptets=None, prevOctet=None, shift=7):
    """ Unpacks the specified septets into octets 
    
    :param septets: Iterator or iterable containing the septets packed into octets
    :type septets: iter(bytearray), bytearray or str
    :param numberOfSeptets: The amount of septets to unpack (or None for all remaining in "septets")
    :type numberOfSeptets: int or None
    
    :return: The septets unpacked into octets
    :rtype: bytearray
    """    
    result = bytearray()    
    if type(septets) == str:
        septets = iter(rawStrToByteArray(septets))
    elif type(septets) == bytearray:
        septets = iter(septets)    
    if numberOfSeptets == None:        
        numberOfSeptets = MAX_INT # Loop until StopIteration
    i = 0
    for octet in septets:
        i += 1
        if shift == 7:
            shift = 1
            if prevOctet != None:                
                result.append(prevOctet >> 1)            
            if i <= numberOfSeptets:
                result.append(octet & 0x7F)
                prevOctet = octet                
            if i == numberOfSeptets:
                break
            else:
                continue
        b = ((octet << shift) & 0x7F) | (prevOctet >> (8 - shift))
        
        prevOctet = octet        
        result.append(b)
        shift += 1
        
        if i == numberOfSeptets:
            break
    if shift == 7:
        b = prevOctet >> (8 - shift)
        if b:
            # The final septet value still needs to be unpacked
            result.append(b)        
    return result

def decodeUcs2(byteIter, numBytes):
    """ Decodes UCS2-encoded text from the specified byte iterator, up to a maximum of numBytes """
    userData = []
    i = 0
    try:
        while i < numBytes:
            userData.append(unichr((next(byteIter) << 8) | next(byteIter)))
            i += 2
    except StopIteration:
        # Not enough bytes in iterator to reach numBytes; return what we have
        pass
    return ''.join(userData)

def encodeUcs2(text):
    """ UCS2 text encoding algorithm
    
    Encodes the specified text string into UCS2-encoded bytes.
    
    :param text: the text string to encode
    
    :return: A bytearray containing the string encoded in UCS2 encoding
    :rtype: bytearray
    """
    result = bytearray()
    for b in map(ord, text):
        result.append(b >> 8)
        result.append(b & 0xFF)
    return result
