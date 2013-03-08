# -*- coding: utf8 -*-

""" SMS PDU encoding methods """

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
                 '€':  chr(0x65)}
                
def encodeSmsPdu(number, text):
    """ Creates an SMS-SUBMIT PDU for sending a message with the specified text to the specified number
    
    @param number: the destination mobile number
    @type number: str
    @param text: the message text
    @type text: str
    
    @return: The SMS PDU
    @rtype: bytearray
    """ 
    pdu = bytearray()
    pdu.append(0x00) # Don't supply an SMSC number - use the one configured in the device
    pdu.append(0x01) # SMS-SUBMIT PDU
    pdu.append(0x00) # message reference - not used in this implementation
    # Add destination number
    if number[0] == '+':
        ton = 145 # 0x91
        number = number[1:] # remove the + character
    else:
        ton = 145 # TODO: get real value
    pdu.append(len(number)) # size of destination mobile number
    pdu.append(ton) # Type of nubmer 145 == 0x91 == international number format
    pdu.extend(encodeReverseNibble(number)) # destination phone number
    pdu.append(0x00) # Protocol identifier - no higher-level protocol
    #TODO: dynamically set data coding scheme based on text contents
    pdu.append(0x00) # Data Coding scheme - 00: GSM7 (default), 08: UCS-2
    encodedText = encodeGsm7(text)
    pdu.append(len(encodedText)) # Payload size in septets/characters
    userData = packSeptets(encodeGsm7(text))
    pdu.extend(userData) # User Data (payload)
    return pdu

def encodeReverseNibble(number):
    """ Reverse nibble encoding algorithm for phone numbers
        
    @return: bytearray containing the encoded octets
    @rtype: bytearray
    """
    if len(number) % 2 == 1:
        number = number + 'F' # append the "end" indicator
    octets = [int(number[i+1] + number[i], 16) for i in xrange(0, len(number), 2)]
    return bytearray(octets)

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
            raise ValueError('Cannot encode char "{0}" using GSM-7 encoding')
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
    """
    result = bytearray()
    if type(octets) == str:
        octets = bytearray(octets)
    bits = 0
    octetsLen = len(octets)
    for i in xrange(octetsLen):    
        if bits == 7:
            bits = 0
            continue
        octet = (octets[i] & 0x7f) >> bits;
        if i < octetsLen - 1:
            octet |= (octets[i+1] << (7 - bits)) & 0xff        
        result.append(octet)
        bits += 1    
    return result
