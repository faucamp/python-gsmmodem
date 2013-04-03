#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Test suite for SMS PDU encoding/decoding algorithms """

import sys, unittest, random
from datetime import datetime, timedelta

import compat # For Python 2.6 compatibility

import gsmmodem.pdu
from gsmmodem.util import SimpleOffsetTzInfo

class TestSemiOctets(unittest.TestCase):
    """ Tests the semi-octet encoder/decoder """
    
    def setUp(self):
        self.tests = (('15125551234', bytearray([0x51, 0x21, 0x55, 0x15, 0x32, 0xf4])),
                      ('123', bytearray([0x21, 0xf3])),
                      ('1234', bytearray([0x21, 0x43]))) 
    
    def test_encode(self):
        """ Tests the semi-octet encoding algorithm """        
        for plaintext, encoded in self.tests:
            result = gsmmodem.pdu.encodeSemiOctets(plaintext)
            self.assertEqual(result, encoded, 'Failed to encode plaintext string: "{0}". Expected: "{1}", got: "{2}"'.format(plaintext, [b for b in encoded], [b for b in result]))
    
    def test_decode(self):
        """ Tests the semi-octet decoding algorithm """        
        for plaintext, encoded in self.tests:
            result = gsmmodem.pdu.decodeSemiOctets(encoded)
            self.assertEqual(result, plaintext, 'Failed to decode data. Expected: "{0}", got: "{1}"'.format(plaintext, result))
        
    def test_decodeIter(self):
        """ Tests semi-octet decoding when using a bytearray iterator and number of octets as input argument """
        iterTests = (('0123456789', 9, iter(bytearray('1032547698'.decode('hex')))),)
        for plaintext, numberOfOctets, byteIter in iterTests:
            result = gsmmodem.pdu.decodeSemiOctets(byteIter, numberOfOctets)
            self.assertEqual(result, plaintext, 'Failed to decode data iter. Expected: "{0}", got: "{1}"'.format(plaintext, result))


class TestGsm7(unittest.TestCase):
    """ Tests the GSM-7 encoding/decoding algorithms """    
    
    def setUp(self):
        self.tests = (('123', bytearray('123'), bytearray([49, 217, 12])),
                      ('12345678', bytearray('12345678'), bytearray([49, 217, 140, 86, 179, 221, 112])),
                      ('123456789', bytearray('123456789'), bytearray([49, 217, 140, 86, 179, 221, 112, 57])),
                      ('Hello World!', bytearray([0x48, 0x65, 0x6C, 0x6C, 0x6F, 0x20, 0x57, 0x6F, 0x72, 0x6C, 0x64, 0x21]), bytearray([200, 50, 155, 253, 6, 93, 223, 114, 54, 57, 4])),
                      ('[{abc}]~', bytearray([0x1B, 0x3C, 0x1B, 0x28, 0x61, 0x62, 0x63, 0x1B, 0x29, 0x1B, 0x3E, 0x1B, 0x3D]), bytearray([27, 222, 6, 21, 22, 143, 55, 169, 141, 111, 211, 3])),
                      ('123456789012345678901234567890', bytearray([49, 50, 51, 52, 53, 54, 55, 56, 57, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 48]), 
                       bytearray([49, 217, 140, 86, 179, 221, 112, 57, 88, 76, 54, 163, 213, 108, 55, 92, 14, 22, 147, 205, 104, 53, 219, 13, 151, 131, 1])),
                      (u'{åΦΓΛΩΠΨΣΘ€}', bytearray([27, 40, 15, 18, 19, 20, 21, 22, 23, 24, 25, 27, 101, 27, 41]), bytearray([27, 212, 67, 50, 161, 84, 44, 23, 76, 102, 83, 222, 164, 0])),
                      (u'a[]{}€', bytearray([97, 27, 60, 27, 62, 27, 40, 27, 41, 27, 101]), bytearray([225, 13, 111, 227, 219, 160, 54, 169, 77, 25])),
                      )
    
    def test_encode(self):
        """ Tests GSM-7 encoding algorithm """
        for plaintext, encoded, septets in self.tests:
            result = gsmmodem.pdu.encodeGsm7(plaintext)
            self.assertEqual(result, encoded, u'Failed to GSM-7 encode plaintext string: "{0}". Expected: "{1}", got: "{2}"'.format(plaintext, [b for b in encoded], [b for b in result]))

    def test_decode(self):
        """ Tests GSM-7 decoding algorithm """
        for plaintext, encoded, septets in self.tests:
            result = gsmmodem.pdu.decodeGsm7(encoded)
            self.assertEqual(result, plaintext, u'Failed to decode GSM-7 string: "{0}". Expected: "{1}", got: "{2}"'.format([b for b in encoded], plaintext, result))
            
    def test_packSeptets(self):
        """ Tests the septet-packing alogrithm for GSM-7-encoded strings """
        for plaintext, encoded, septets in self.tests:
            result = gsmmodem.pdu.packSeptets(encoded)
            self.assertEqual(result, septets, u'Failed to pack GSM-7 octets into septets for string: "{0}". Expected: "{1}", got: "{2}"'.format(plaintext, [b for b in septets], [b for b in result]))
    
    def test_unpackSeptets_no_limits(self):
        """ Tests the septet-unpacking alogrithm for GSM-7-encoded strings (no maximum number of septets specified) """
        for plaintext, encoded, septets in self.tests:
            result = gsmmodem.pdu.unpackSeptets(septets)
            self.assertEqual(result, encoded, u'Failed to unpack GSM-7 septets into octets for string: "{0}". Expected: "{1}", got: "{2}"'.format(plaintext, [b for b in encoded], [b for b in result]))
    
    def test_unpackSeptets_with_limits(self):
        """ Tests the septet-unpacking alogrithm for GSM-7-encoded strings (max number of septets specified) """        
        for plaintext, encoded, septets in self.tests:
            limit = len(septets)
            septets.extend([random.randint(0,255), random.randint(0,255), random.randint(0,255), random.randint(0,255)]) # add some garbage data (should be ignored due to numberOfSeptets being set)
            result = gsmmodem.pdu.unpackSeptets(septets, limit)
            self.assertEqual(result, encoded, u'Failed to unpack GSM-7 septets into {0} octets for string: "{1}". Expected: "{2}", got: "{3}"'.format(len(encoded), plaintext, [b for b in encoded], [b for b in result]))

    def test_encodeInvalid(self):
        """ Test encoding a string that cannot be encoded with GSM-7 """
        tests = (u'世界您好！',)
        # First check without "discard invalid chars"
        for invalidStr in tests:
            self.assertRaises(ValueError, gsmmodem.pdu.encodeGsm7, invalidStr, discardInvalid=False)

    def test_encodeInvalidDiscard(self):
        """ Tests encoding a string containing invalid GSM-7 characters when set to discard them """
        tests = ((u'a世界b您c好！', bytearray([97, 98, 99])),)
        for invalidStr, encoded in tests:
            result = gsmmodem.pdu.encodeGsm7(invalidStr, discardInvalid=True)
            self.assertEqual(result, encoded, u'Failed to GSM-7 encode invalid plaintext string: "{0}". Expected: "{1}", got: "{2}"'.format(invalidStr, [b for b in encoded], [b for b in result]))


class TestSmsPduAddressFields(unittest.TestCase):
    """ Tests for SMS PDU address fields (these methods are not meant to be public) """
    
    def setUp(self):
        self.tests = (('+9876543210', 7, '0A918967452301', '0A918967452301'),
                 ('+9876543210', 7, '0A918967452301000000', '0A918967452301'), # same as above, but checking read limits
                 ('+987654321', 7, '099189674523F1000000', '099189674523F1'), 
                 ('+27829135934', 8, '0B917228195339F4', '0B917228195339F4'),
                 ('abc', 5, '06D061F118', '06D061F118'),
                 ('abc', 5, '06D061F118D3F1FF0032', '06D061F118'), # same as above, but checking read limits                 
                 ('FRANCOIS', 9, '0ED04669D0397C26A7', '0ED04669D0397C26A7'),
                 (u'a[]{}€', 12, '14D0E10D6FE3DBA036A94D19', '14D0E10D6FE3DBA036A94D19'),                 
                 )
    
    def test_decodeAddressField(self):        
        for plaintext, bytesRead, hexEncoded, realHexEncoded in self.tests:
            byteIter = iter(bytearray(hexEncoded.decode('hex')))
            resultValue, resultNumBytesRead = gsmmodem.pdu._decodeAddressField(byteIter)
            self.assertEqual(resultValue, plaintext, u'Failed to decode address field data "{0}". Expected: "{1}", got: "{2}"'.format(hexEncoded, plaintext, resultValue))
            self.assertEqual(resultNumBytesRead, bytesRead, u'Incorrect "number of bytes read" returned for data "{0}". Expected: "{1}", got: "{2}"'.format(hexEncoded, bytesRead, resultNumBytesRead))
    
    def test_encodeAddressField(self):
        for plaintext, bytesRead, hexEncoded, realHexEncoded in self.tests:
            expected = bytearray(realHexEncoded.decode('hex'))
            result = gsmmodem.pdu._encodeAddressField(plaintext)
            self.assertEqual(result, expected, u'Failed to encode address field data "{0}". Expected: "{1}", got: "{2}"'.format(plaintext, realHexEncoded, str(result).encode('hex').upper()))            

class TestSmsPduSmscFields(unittest.TestCase):
    """ Tests for SMS PDU SMSC-specific address fields (these methods are not meant to be public)

    Note: SMSC fields are encoded *slightly* differently from "normal" address fields (the length indicator is different)
    """
    
    def setUp(self):
        self.tests = (('+9876543210', 7, '06918967452301', '06918967452301'),
                 ('+9876543210', 7, '06918967452301000000', '06918967452301'), # same as above, but checking read limits
                 ('+987654321', 7, '069189674523F1000000', '069189674523F1'), 
                 ('+2782913593', 7, '06917228195339', '06917228195339'))
        
    def test_decodeSmscField(self):        
        for plaintext, bytesRead, hexEncoded, realHexEncoded in self.tests:
            byteIter = iter(bytearray(hexEncoded.decode('hex')))
            resultValue, resultNumBytesRead = gsmmodem.pdu._decodeAddressField(byteIter, smscField=True)
            self.assertEqual(resultValue, plaintext, u'Failed to decode SMSC address field data "{0}". Expected: "{1}", got: "{2}"'.format(hexEncoded, plaintext, resultValue))
            self.assertEqual(resultNumBytesRead, bytesRead, u'Incorrect "number of bytes read" returned for data "{0}". Expected: "{1}", got: "{2}"'.format(hexEncoded, bytesRead, resultNumBytesRead))
    
    def test_encodeSmscField(self):
        for plaintext, bytesRead, hexEncoded, realHexEncoded in self.tests:
            expected = bytearray(realHexEncoded.decode('hex'))
            result = gsmmodem.pdu._encodeAddressField(plaintext, smscField=True)
            self.assertEqual(result, expected, u'Failed to encode SMSC address field data "{0}". Expected: "{1}", got: "{2}"'.format(plaintext, realHexEncoded, str(result).encode('hex').upper()))

class TestRelativeValidityPeriod(unittest.TestCase):
    """ Tests for SMS PDU relative validity period encoding/decoding (these methods are not meant to be public) """
    
    def setUp(self):
        self.tests = ((timedelta(minutes=30), 5),
                      (timedelta(hours=16), 151),
                      (timedelta(days=3), 169),
                      (timedelta(weeks=5), 197))
        
    def test_encode(self):
        for validity, tpVp in self.tests:
            result = gsmmodem.pdu._encodeRelativeValidityPeriod(validity)
            self.assertEqual(result, tpVp, u'Failed to encode relative validity period: {0}. Expected: "{1}", got: "{2}"'.format(validity, tpVp, result))
    
    def test_decode(self):
        for validity, tpVp in self.tests:
            result = gsmmodem.pdu._decodeRelativeValidityPeriod(tpVp)
            self.assertEqual(result, validity, u'Failed to decode relative validity period: {0}. Expected: "{1}", got: "{2}"'.format(tpVp, validity, result))

class TestSmsPdu(unittest.TestCase):
    """ Tests encoding/decoding of SMS PDUs """
        
    def test_encodeSmsSubmit(self):
        """ Tests SMS PDU encoding """
        tests = (('+27820001111', 'Hello World!', 0, None, None, False, '0001000B917228001011F100000CC8329BFD065DDF72363904'),
                 ('+123456789', u'世界您好！', 0, None, None, False, '000100099121436587F900080CFFFE164E4C75A8607D5901FF'),
                 ('+31628870634', 'www.diafaan.com', 13, timedelta(days=3), '+31624000000', True, '07911326040000F0310D0B911326880736F40000A90FF7FBDD454E87CDE1B0DB357EB701'))
        for number, text, reference, validity, smsc, rejectDuplicates, pduHex in tests:
            pdu = bytearray(pduHex.decode('hex'))
            result = gsmmodem.pdu.encodeSmsSubmitPdu(number, text, reference, validity, smsc, rejectDuplicates)[0]            
            self.assertEqual(result, pdu, u'Failed to encode SMS PDU for number: "{0}" and text "{1}". Expected: "{2}", got: "{3}"'.format(number, text, pduHex, str(result).encode('hex').upper()))

    def test_decode(self):
        """ Tests SMS PDU decoding """
        tests = (('06917228195339040B917228214365F700003130805120618005D4F29C2E03', {'type': 'SMS-DELIVER',
                                                                                     'smsc': '+2782913593',
                                                                                     'number': '+27821234567',
                                                                                     'protocol_id': 0,                                                            
                                                                                     'time': datetime(2013, 3, 8, 15, 2, 16, tzinfo=SimpleOffsetTzInfo(2)),
                                                                                     'text': 'Test2'}),
                 ('07915892000000F0040B915892214365F700007040213252242331493A283D0795C3F33C88FE06C9CB6132885EC6D341EDF27C1E3E97E7207B3A0C0A5241E377BB1D7693E72E',
                  {'type': 'SMS-DELIVER',
                   'smsc': '+85290000000',
                   'number': '+85291234567',
                   'time': datetime(2007, 4, 12, 23, 25, 42, tzinfo=SimpleOffsetTzInfo(8)),
                   'text': 'It is easy to read text messages via AT commands.'}),
                 ('06917228195339040B917228214365F70000313062315352800A800D8A5E98D337A910', 
                  {'type': 'SMS-DELIVER',
                   'number': '+27821234567',
                   'text': u'@{tést}!'}),
                 ('07911326040000F0310D0B911326880736F40000A90FF7FBDD454E87CDE1B0DB357EB701',
                  {'type': 'SMS-SUBMIT',
                   'smsc': '+31624000000',
                   'number': '+31628870634',
                   'validity': timedelta(days=3),
                   'text': 'www.diafaan.com'}),
                 ('0006D60B911326880736F4111011719551401110117195714000',
                  {'type': 'SMS-STATUS-REPORT',
                   'number': '+31628870634',
                   'reference': 214}))
        
        for pdu, expected in tests:
            result = gsmmodem.pdu.decodeSmsPdu(pdu)
            self.assertIsInstance(result, dict)
            for key, value in expected.iteritems():
                self.assertIn(key, result)
                self.assertEqual(result[key], value, u'Failed to decode PDU value for "{0}". Expected "{1}", got "{2}".'.format(key, value, result[key]))

if __name__ == "__main__":
    unittest.main()