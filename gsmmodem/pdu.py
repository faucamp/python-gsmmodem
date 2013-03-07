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
                
def createSmsPdu(number, text):
    bytes = bytearray()
    bytes.append(0x00) # Don't supply an SMSC number - use the one configured in the device
    bytes.append(0x01) # SMS-SUBMIT PDU
    bytes.append(0x00) # message reference - not used in this implementation
    # Add destination number
    if number[0] == '+':
        ton = 145 # 0x91
        number = number[1:] # remove the + character
    else:
        ton = 145 # TODO: get real value
    bytes.append(len(number)) # size of destination mobile number
    bytes.append(ton) # Type of nubmer 145 == 0x91 == international number format
    bytes.extend(encodeReverseNibble(text)) # destination phone number
    bytes.append(0x00) # Protocol identifier - no higher-level protocol
    #TODO: dynamically set data coding scheme based on text contents
    bytes.append(0x00) # Data Coding scheme - 00: GSM7 (default), 08: UCS-2
    #TODO: finish

def encodeReverseNibble(plaintext):
    """ Reverse nibble encoding algorithm """
    if len(plaintext) % 2 == 1:
        plaintext = plaintext[:-1] + 'f' +plaintext[-1] # insert the "end" indicator
    octets = [int(plaintext[i+1] + plaintext[i], 16) for i in xrange(0, len(plaintext), 2)]
    return bytearray(octets)

def encodeGsm7(text, discardInvalid=False):
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
    for char in text:
        idx = GSM7_BASIC.find(char)
        if idx != -1:
            result.append(chr(idx))
        elif char in GSM7_EXTENDED:
            result.append(char(0x1B)) # ESC - switch to extended table
            result.append(GSM7_EXTENDED[char])
        elif not discardInvalid:
            raise ValueError('Cannot encode char "{0}" using GSM-7 encoding')
    return result
