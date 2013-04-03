# -*- coding: utf8 -*-

""" SMS PDU encoding methods """

import sys
from datetime import datetime, timedelta, tzinfo

from .exceptions import EncodingError

# Tables can be found at: http://en.wikipedia.org/wiki/GSM_03.38#GSM_7_bit_default_alphabet_and_extension_table_of_3GPP_TS_23.038_.2F_GSM_03.38
GSM7_BASIC = (u'@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ\x1bÆæßÉ !\"#¤%&\'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ`¿abcdefghijklmnopqrstuvwxyzäöñüà')
GSM7_EXTENDED = {chr(0xFF): chr(0x0A),
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
                 u'€':  chr(0x65)}

class SmsPduTzInfo(tzinfo):
    """ Simple implementation of datetime.tzinfo for handling timestamp GMT offsets specified in SMS PDUs """
    
    def __init__(self, pduOffsetStr=None):
        """ 
        @param pduOffset: 2 semi-octet timezone offset as specified by PDU (see GSM 03.40 spec)
        @type pduOffset: str 
        
        Note: pduOffsetStr is optional in this constructor due to the special requirement for pickling
        mentioned in the Python docs. It should, however, be used (or otherwise pduOffsetStr must be
        manually set)
        """        
        self._offset = None
        if pduOffsetStr != None:
            self._setPduOffsetStr(pduOffsetStr)
        
    def _setPduOffsetStr(self, pduOffsetStr):
        # See if the timezone difference is positive/negative               
        if int(pduOffsetStr, 16) & 0x80 == 0: # positive            
            self._offset = timedelta(minutes=(int(pduOffsetStr) * 15))
        else: # negative            
            self._offset = timedelta(minutes=(int(pduOffsetStr) * -15))
    
    def utcoffset(self, dt):
        return self._offset
    
    def dst(self, dt):
        """ We do not have enough info in the SMS PDU to implement DST """
        return timedelta(0)
    

def encodeSmsSubmitPdu(number, text, reference=0, validity=None, smsc=None, rejectDuplicates=False):
    """ Creates an SMS-SUBMIT PDU for sending a message with the specified text to the specified number
    
    @param number: the destination mobile number
    @type number: str
    @param text: the message text
    @type text: str
    @param reference: message reference number (see also: rejectDuplicates parameter)
    @type reference: int
    @param validity: message validity period (absolute or relative)
    @type validity: datetime.timedelta (relative) or datetime.datetime (absolute)
    @param smsc: SMSC number to use (leave None to use default)
    @type smsc: str
    @param rejectDuplicates: Flag that controls the TP-RD parameter (messages with same destination and reference may be rejected if True)
    @type rejectDuplicates: bool
            
    @return: A tuple containing the SMS PDU as a bytearray, and the length of the TPDU part
    @rtype: tuple
    """ 
    pdu = bytearray()
    if smsc:
        pdu.extend(_encodeAddressField(smsc, smscField=True))
    else:
        pdu.append(0x00) # Don't supply an SMSC number - use the one configured in the device
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
            raise ValueError('"validity" must be of type datetime.timedelta (for relative value) or datetime.datetime (for absolute value)')        
    else:
        validityPeriod = None
    if rejectDuplicates:
        tpduFirstOctet |= 0x20 # bit5 == 1
    pdu.append(tpduFirstOctet)
    pdu.append(reference) # message reference
    # Add destination number    
    pdu.extend(_encodeAddressField(number))
    pdu.append(0x00) # Protocol identifier - no higher-level protocol
    # Set data coding scheme based on text contents
    try:
        encodedText = encodeGsm7(text)
    except ValueError:
        # Cannot encode text using GSM-7; use UCS2 instead
        alphabet = 0x08 # UCS2        
        encodedText = text.encode('utf-16')
        userDataLength = len(encodedText) # Payload size in septets/characters
        userData = encodedText
    else:
        alphabet = 0x00 # GSM-7        
        userDataLength = len(encodedText) # Payload size in septets/characters
        userData = packSeptets(encodeGsm7(text))    
    pdu.append(alphabet)
    if validityPeriod:
        pdu.extend(validityPeriod)
    pdu.append(userDataLength)
    pdu.extend(userData) # User Data (payload)
    tpdu_length = len(pdu) - 1
    return pdu, tpdu_length

def decodeSmsPdu(pdu):
    """ Decodes SMS pdu data and returns a tuple in format (number, text)
    
    @param pdu: PDU data as a hex string, or a bytearray containing PDU octects
    @type pdu: str or bytearray
    
    @return: The decoded SMS data as a dictionary
    @rtype: dict    
    """ 
    if type(pdu) == str:
        pdu = bytearray(pdu.decode('hex'))       
    result = {}
    pduIter = iter(pdu)
 
    smscNumber, smscBytesRead = _decodeAddressField(pduIter, smscField=True)
    result['smsc'] = smscNumber
    result['tpdu_length'] = len(pdu) - smscBytesRead
    
    tpduFirstOctet = pduIter.next() 
    
    pduType = tpduFirstOctet & 0x03 # bits 1-0
    if pduType == 0x00: # SMS-DELIVER or SMS-DELIVER REPORT        
        result['type'] = 'SMS-DELIVER'
        result['number'] = _decodeAddressField(pduIter)[0]
        result['protocol_id'] = pduIter.next()
        dataCoding = _decodeDataCoding(pduIter.next())
        result['time'] = _decodeTimestamp(pduIter)
        userDataLen = pduIter.next()
        if dataCoding == 0x00: # GSM-7
            userDataSeptets = unpackSeptets(pduIter, userDataLen)
            result['text'] = decodeGsm7(userDataSeptets)
        elif dataCoding == 0x02: # UCS2
            userData = []
            for i in xrange(userDataLen):
                userData.append(chr(pduIter.next()))
            result['text'] = ''.join(userData).decode('utf-16')
        else:
            result['text'] = ''        
    elif pduType == 0x01: # SMS-SUBMIT or SMS-SUBMIT-REPORT
        result['type'] = 'SMS-SUBMIT'
        result['reference'] = pduIter.next() # message reference - we don't really use this
        result['number'] = _decodeAddressField(pduIter)[0]
        result['protocol_id'] = pduIter.next()
        dataCoding = _decodeDataCoding(pduIter.next())
        validityPeriodFormat = (tpduFirstOctet & 0x18) >> 3 # bits 4,3
        if validityPeriodFormat == 0x02: # TP-VP field present and integer represented (relative)
            result['validity'] = _decodeRelativeValidityPeriod(pduIter.next())
        elif validityPeriodFormat == 0x03: # TP-VP field present and semi-octet represented (absolute)            
            result['validity'] = _decodeTimestamp(pduIter)
        userDataLen = pduIter.next()
        if dataCoding == 0x00: # GSM-7
            userDataSeptets = unpackSeptets(pduIter, userDataLen)
            result['text'] = decodeGsm7(userDataSeptets)
        elif dataCoding == 0x02: # UCS2
            for i in xrange(userDataLen):
                userData.append(pduIter.next())
            result['text'] = ''.join(userData).decode('utf-16')
        else:
            result['text'] = ''        
    elif pduType == 0x02: # SMS-STATUS-REPORT or SMS-COMMAND
        result['type'] = 'SMS-STATUS-REPORT'
        result['reference'] = pduIter.next()
        result['number'] = _decodeAddressField(pduIter)[0]
        result['time'] = _decodeTimestamp(pduIter)
        result['discharge'] = _decodeTimestamp(pduIter)
        result['status'] = pduIter.next()        
    else:
        raise EncodingError('Unknown SMS message type: {0}. First TPDU octect was: {1}'.format(pduType, tpduFirstOctet))
    
    return result

def _decodeRelativeValidityPeriod(tpVp):
    """ Calculates the relative SMS validity period (based on the table in section 9.2.3.12 of GSM 03.40)
    @rtype: datetime.timedelta
    """
    if tpVp <= 143:
        return timedelta(minutes=((tpVp + 1) * 5))
    elif 144 <= tpVp <= 167:
        return timedelta(hours=12, minutes=((tpVp - 143) * 30))
    elif 168 <= tpVp <= 196:
        return timedelta(days=(tpVp - 166))
    elif 197 <= tpVp <= 255:
        return timedelta(weeks=(tpVp - 192))
    
def _encodeRelativeValidityPeriod(validityPeriod):
    """ Encodes the specified relative validity period timedelta into an integer for use in an SMS PDU
    (based on the table in section 9.2.3.12 of GSM 03.40)
    
    @param validityPeriod: The validity period to encode
    @type validityPeriod: datetime.timedelta
    @rtype: int
    """
    seconds = validityPeriod.total_seconds()
    if seconds <= 43200: # 12 hours
        tpVp = (seconds / 300) - 1 # divide by 5 minutes, subtract 1
    elif seconds <= 86400: # 24 hours
        tpVp = (seconds - 43200) / 1800 + 143 # subtract 12 hours, divide by 30 minutes. add 143
    elif validityPeriod.days <= 30: # 30 days
        tpVp = validityPeriod.days + 166 # amount of days + 166
    elif validityPeriod.days > 30:
        tpVp = validityPeriod.days / 7 + 192 # amount of weeks + 192
    return tpVp
        
def _decodeTimestamp(byteIter):
    """ Decodes a 7-octet timestamp """
    dateStr = decodeSemiOctets(byteIter, 7)
    timeZoneStr = dateStr[-2:]        
    return datetime.strptime(dateStr[:-2], '%y%m%d%H%M%S').replace(tzinfo=SmsPduTzInfo(timeZoneStr))

def _encodeTimestamp(timestamp):
    """ Encodes a 7-octet timestamp from the specified date
    
    Note: the specified timestamp must have a UTC offset set; you can use gsmmodem.util.SimpleOffsetTzInfo for simple cases
    
    @param timestamp: The timestamp to encode
    @type timestamp: datetime.datetime
    
    @return: The encoded timestamp
    @rtype: bytearray
    """
    if timestamp.utcoffset == None:
        raise ValueError('Please specify a UTC offset for the timestamp (e.g. by using gsmmodem.util.SimpleOffsetTzInfo)')
    dateStr = timestamp.strftime('%y%m%d%H%M%S%z')[-2]
    return encodeSemiOctets(dateStr)    

def _decodeDataCoding(octet):
    if octet & 0xC0 == 0:
        #compressed = octect & 0x20
        alphabet = (octet & 0x0C) >> 2
        return alphabet # 0x00 == GSM-7, 0x01 == 8-bit data, 0x02 == UCS2
    # We ignore other coding groups
    return 0    

def _decodeAddressField(byteIter, smscField=False):
    """ Decodes the address field at the current position of the bytearray iterator
    
    @param byteIter: Iterator over bytearray
    @type byteIter: iter(bytearray) 
    
    @return: Tuple containing the address value and amount of bytes read (value is or None if it is empty (zero-length))
    @rtype: tuple
    """
    addressLen = byteIter.next()
    if addressLen > 0:
        toa = byteIter.next()
        ton = (toa & 0x70) # bits 6,5,4 of type-of-address == type-of-number
        if ton == 0x50: 
            # Alphanumberic number            
            addressLen /= 2
            septets = unpackSeptets(byteIter, addressLen)
            addressValue = decodeGsm7(septets)
            return (addressValue, (addressLen + 2))
        else:
            # ton == 0x00: Unknown (might be international, local, etc) - leave as is            
            # ton == 0x20: National number
            if smscField:
                addressValue = decodeSemiOctets(byteIter, addressLen-1)
            else:
                addressLen = int(round(addressLen / 2.0))
                addressValue = decodeSemiOctets(byteIter, addressLen)
                addressLen += 1 # for the return value, add the toa byte
            if ton == 0x10: # International number
                addressValue = '+' + addressValue
            return (addressValue, (addressLen + 1))
    else:
        return (None, 1)

def _encodeAddressField(address, smscField=False):
    """ Encodes the address into an address field
    
    @param address: The address to encode (phone number or alphanumeric)
    @type byteIter: str
    
    @return: Encoded SMS PDU address field
    @rtype: bytearray
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
        
    @return: bytearray containing the encoded octets
    @rtype: bytearray
    """
    if len(number) % 2 == 1:
        number = number + 'F' # append the "end" indicator
    octets = [int(number[i+1] + number[i], 16) for i in xrange(0, len(number), 2)]
    return bytearray(octets)

def decodeSemiOctets(encodedNumber, numberOfOctets=None):
    """ Semi-octet decoding algorithm(e.g. for phone numbers)
    
    @param encodedNumber: The semi-octet-encoded telephone number (in bytearray format or hex string)
    @type encodedNumber: bytearray, str or iter(bytearray)
    @param numberOfOctets: The expected amount of octets after decoding (i.e. when to stop)
    @type numberOfOctets: int
    
    @return: decoded telephone number
    @rtype: string
    """
    number = []
    if type(encodedNumber) == str:
        encodedNumber = bytearray(encodedNumber.decode('hex'))
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
    
    @param text: the text string to encode
    @param discardInvalid: if True, characters that cannot be encoded will be silently discarded 
    
    @raise ValueError: if the text string cannot be encoded using GSM-7 encoding (unless discardInvalid == True)
    
    @return: A bytearray containing the string encoded in GSM-7 encoding
    @rtype: bytearray
    """
    result = bytearray()
    for char in plaintext:
        idx = GSM7_BASIC.find(char)
        if idx != -1:
            result.append(chr(idx))
        elif char in GSM7_EXTENDED:
            result.append(chr(0x1B)) # ESC - switch to extended table
            result.append(GSM7_EXTENDED[char])
        elif not discardInvalid:
            raise ValueError(u'Cannot encode char "{0}" using GSM-7 encoding'.format(char))
    return result

def decodeGsm7(encodedText):
    """ GSM-7 text decoding algorithm
    
    Decodes the specified GSM-7-encoded string into a plaintext string.
    
    @param encodedText: the text string to encode
    @type encodedText: bytearray or str
    
    @return: A string containing the decoded text
    @rtype: str
    """
    result = []
    if type(encodedText) == str:
        encodedText = bytearray(encodedText)
    iterEncoded = iter(encodedText)
    for b in iterEncoded:
        if b == 0x1B: # ESC - switch to extended table
            c = chr(iterEncoded.next())
            for char, value in GSM7_EXTENDED.iteritems():
                if c == value:
                    result.append(char)
                    break
        else:
            result.append(GSM7_BASIC[b])
    return ''.join(result)

def packSeptets(octets):
    """ Packs the specified octets into septets
    
    Typically the output of encodeGsm7 would be used as input to this function. The resulting
    bytearray contains the original GSM-7 characters packed into septets ready for transmission.
    
    @rtype: bytearray
    """    
    result = bytearray()    
    if type(octets) == str:
        octets = iter(bytearray(octets))
    elif type(octets) == bytearray:
        octets = iter(octets)
    shift = 0
    prevSeptet = octets.next()
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

def unpackSeptets(septets, numberOfSeptets=None):
    """ Unpacks the specified septets into octets 
    
    @param septets: Iterator or iterable containing the septets packed into octets
    @type septets: iter(bytearray), bytearray or str
    @param numberOfSeptets: The amount of septets to unpack (or None for all remaining in "septets")
    @type numberOfSeptets: int or None
    
    @return: The septets unpacked into octets
    @rtype: bytearray
    """    
    result = bytearray()    
    if type(septets) == str:
        septets = iter(bytearray(septets))
    elif type(septets) == bytearray:
        septets = iter(septets)    
    if numberOfSeptets == None:        
        numberOfSeptets = sys.maxint # Loop until StopIteration
    shift = 7
    prevOctet = None
    i = 0
    for octet in septets:
        i += 1
        if shift == 7:
            shift = 1
            if prevOctet != None:                
                result.append(prevOctet >> 1)            
            #if len(result) < numberOfSeptets:
            if i <= numberOfSeptets:
                result.append(octet & 0x7F)
                prevOctet = octet                
            #if len(result) == numberOfSeptets:
            if i == numberOfSeptets:
                break
            else:
                continue
        b = ((octet << shift) & 0x7F) | (prevOctet >> (8 - shift))
        prevOctet = octet        
        result.append(b)
        shift += 1
        #if len(result) == numberOfSeptets:
        if i == numberOfSeptets:
            break
    if shift == 7:
        b = prevOctet >> (8 - shift)
        if b:
            # The final septet value still needs to be unpacked
            result.append(b)        
    return result
