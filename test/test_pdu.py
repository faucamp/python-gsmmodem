#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Test suite for SMS PDU encoding/decoding algorithms """

from __future__ import unicode_literals

import sys, unittest, random, codecs
from datetime import datetime, timedelta

from . import compat # For Python 2.6, 3.0-2 compatibility
 
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
            # Test different parameter types: bytearray, str
            for param in (encoded, codecs.encode(compat.str(encoded), 'hex_codec')):
                result = gsmmodem.pdu.decodeSemiOctets(param)
                self.assertEqual(result, plaintext, 'Failed to decode data. Expected: "{0}", got: "{1}"'.format(plaintext, result))
        
    def test_decodeIter(self):
        """ Tests semi-octet decoding when using a bytearray iterator and number of octets as input argument """
        iterTests = (('0123456789', 9, iter(bytearray(codecs.decode(b'1032547698', 'hex_codec')))),)
        for plaintext, numberOfOctets, byteIter in iterTests:
            result = gsmmodem.pdu.decodeSemiOctets(byteIter, numberOfOctets)
            self.assertEqual(result, plaintext, 'Failed to decode data iter. Expected: "{0}", got: "{1}"'.format(plaintext, result))


class TestGsm7(unittest.TestCase):
    """ Tests the GSM-7 encoding/decoding algorithms """
    
    def setUp(self):
        self.tests = (('123', bytearray(b'123'), bytearray([49, 217, 12])),
                      ('12345678', bytearray(b'12345678'), bytearray([49, 217, 140, 86, 179, 221, 112])),
                      ('123456789', bytearray(b'123456789'), bytearray([49, 217, 140, 86, 179, 221, 112, 57])),
                      ('Hello World!', bytearray([0x48, 0x65, 0x6C, 0x6C, 0x6F, 0x20, 0x57, 0x6F, 0x72, 0x6C, 0x64, 0x21]), bytearray([200, 50, 155, 253, 6, 93, 223, 114, 54, 57, 4])),
                      ('[{abc}]~', bytearray([0x1B, 0x3C, 0x1B, 0x28, 0x61, 0x62, 0x63, 0x1B, 0x29, 0x1B, 0x3E, 0x1B, 0x3D]), bytearray([27, 222, 6, 21, 22, 143, 55, 169, 141, 111, 211, 3])),
                      ('123456789012345678901234567890', bytearray([49, 50, 51, 52, 53, 54, 55, 56, 57, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 48]), 
                       bytearray([49, 217, 140, 86, 179, 221, 112, 57, 88, 76, 54, 163, 213, 108, 55, 92, 14, 22, 147, 205, 104, 53, 219, 13, 151, 131, 1])),
                      ('{åΦΓΛΩΠΨΣΘ€}', bytearray([27, 40, 15, 18, 19, 20, 21, 22, 23, 24, 25, 27, 101, 27, 41]), bytearray([27, 212, 67, 50, 161, 84, 44, 23, 76, 102, 83, 222, 164, 0])),
                      ('a[]{}€', bytearray([97, 27, 60, 27, 62, 27, 40, 27, 41, 27, 101]), bytearray([225, 13, 111, 227, 219, 160, 54, 169, 77, 25])),
                      )
    
    def test_encode(self):
        """ Tests GSM-7 encoding algorithm """
        for plaintext, encoded, septets in self.tests:
            result = gsmmodem.pdu.encodeGsm7(plaintext)
            self.assertEqual(result, encoded, 'Failed to GSM-7 encode plaintext string: "{0}". Expected: "{1}", got: "{2}"'.format(plaintext, [b for b in encoded], [b for b in result]))

    def test_decode(self):
        """ Tests GSM-7 decoding algorithm """
        for plaintext, encoded, septets in self.tests:
            # Test different parameter types: bytearray, str
            for param in (encoded, compat.bytearrayToStr(encoded)):
                result = gsmmodem.pdu.decodeGsm7(param)
                self.assertEqual(result, plaintext, 'Failed to decode GSM-7 string: "{0}". Expected: "{1}", got: "{2}"'.format([b for b in encoded], plaintext, result))
            
    def test_packSeptets(self):
        """ Tests the septet-packing alogrithm for GSM-7-encoded strings """
        for plaintext, encoded, septets in self.tests:
            # Test different parameter types: bytearray, str, iter(bytearray)
            i = 0
            for param in (encoded, compat.bytearrayToStr(encoded), iter(encoded)):
                result = gsmmodem.pdu.packSeptets(param)
                self.assertEqual(result, septets, 'Failed to pack GSM-7 octets into septets for string: "{0}" using parameter type: {1}. Expected: "{2}", got: "{3}"'.format(plaintext, type(param), [b for b in septets], [b for b in result]))
                i+=1
    
    def test_unpackSeptets_no_limits(self):
        """ Tests the septet-unpacking alogrithm for GSM-7-encoded strings (no maximum number of septets specified) """
        for plaintext, encoded, septets in self.tests:
            # Test different parameter types: bytearray, str, iter(bytearray)
            for param in (septets, compat.bytearrayToStr(septets), iter(septets)):
                result = gsmmodem.pdu.unpackSeptets(param)
                self.assertEqual(result, encoded, 'Failed to unpack GSM-7 septets into octets for string: "{0}". Expected: "{1}", got: "{2}"'.format(plaintext, [b for b in encoded], [b for b in result]))
    
    def test_unpackSeptets_with_limits(self):
        """ Tests the septet-unpacking alogrithm for GSM-7-encoded strings (max number of septets specified) """        
        for plaintext, encoded, septets in self.tests:
            limit = len(septets)
            septets.extend([random.randint(0,255), random.randint(0,255), random.randint(0,255), random.randint(0,255)]) # add some garbage data (should be ignored due to numberOfSeptets being set)
            result = gsmmodem.pdu.unpackSeptets(septets, limit)
            self.assertEqual(result, encoded, 'Failed to unpack GSM-7 septets into {0} octets for string: "{1}". Expected: "{2}", got: "{3}"'.format(len(encoded), plaintext, [b for b in encoded], [b for b in result]))

    def test_encodeInvalid(self):
        """ Test encoding a string that cannot be encoded with GSM-7 """
        tests = ('世界您好！',)
        for invalidStr in tests:
            self.assertRaises(ValueError, gsmmodem.pdu.encodeGsm7, invalidStr, discardInvalid=False)

    def test_encodeInvalidDiscard(self):
        """ Tests encoding a string containing invalid GSM-7 characters when set to discard them """
        tests = (('a世界b您c好！', bytearray([97, 98, 99])),)
        for invalidStr, encoded in tests:
            result = gsmmodem.pdu.encodeGsm7(invalidStr, discardInvalid=True)
            self.assertEqual(result, encoded, 'Failed to GSM-7 encode invalid plaintext string: "{0}". Expected: "{1}", got: "{2}"'.format(invalidStr, [b for b in encoded], [b for b in result]))


class TestUcs2(unittest.TestCase):
    """ Tests the UCS2 encoding/decoding algorithms """

    def setUp(self):
        self.tests = (('あ叶葉', bytearray([0x30, 0x42, 0x53, 0xF6, 0x84, 0x49])),
                         ('はい', bytearray([0x30, 0x6F, 0x30, 0x44])))
    
    def test_encode(self):
        """ Tests GSM-7 encoding algorithm """
        for plaintext, encoded in self.tests:
            result = gsmmodem.pdu.encodeUcs2(plaintext)
            self.assertEqual(result, encoded, 'Failed to UCS-2 encode plaintext string: "{0}". Expected: "{1}", got: "{2}"'.format(plaintext, [b for b in encoded], [b for b in result]))

    def test_decode(self):
        """ Tests GSM-7 decoding algorithm """
        for plaintext, encoded in self.tests:
            result = gsmmodem.pdu.decodeUcs2(iter(encoded), len(encoded))
            self.assertEqual(result, plaintext, 'Failed to decode UCS-2 string: "{0}". Expected: "{1}", got: "{2}"'.format([b for b in encoded], plaintext, result))
            

class TestSmsPduAddressFields(unittest.TestCase):
    """ Tests for SMS PDU address fields (these methods are not meant to be public) """
    
    def setUp(self):
        self.tests = (('+9876543210', 7, b'0A918967452301', b'0A918967452301'),
                 ('+9876543210', 7, b'0A918967452301000000', b'0A918967452301'), # same as above, but checking read limits
                 ('+987654321', 7, b'099189674523F1000000', b'099189674523F1'), 
                 ('+27829135934', 8, b'0B917228195339F4', b'0B917228195339F4'),
                 ('abc', 5, b'06D061F118', b'06D061F118'),
                 ('abc', 5, b'06D061F118D3F1FF0032', b'06D061F118'), # same as above, but checking read limits                 
                 ('FRANCOIS', 9, b'0ED04669D0397C26A7', b'0ED04669D0397C26A7'),
                 ('a[]{}€', 12, b'14D0E10D6FE3DBA036A94D19', b'14D0E10D6FE3DBA036A94D19'),
                 ('0129998765', 7, b'0AA11092997856', b'0AA11092997856') # local number
                 )
    
    def test_decodeAddressField(self):        
        for plaintext, bytesRead, hexEncoded, realHexEncoded in self.tests:
            byteIter = iter(bytearray(codecs.decode(hexEncoded, 'hex_codec')))
            resultValue, resultNumBytesRead = gsmmodem.pdu._decodeAddressField(byteIter, log=True)
            self.assertEqual(resultValue, plaintext, 'Failed to decode address field data "{0}". Expected: "{1}", got: "{2}"'.format(hexEncoded, plaintext, resultValue))
            self.assertEqual(resultNumBytesRead, bytesRead, 'Incorrect "number of bytes read" returned for data "{0}". Expected: "{1}", got: "{2}"'.format(hexEncoded, bytesRead, resultNumBytesRead))
    
    def test_encodeAddressField(self):
        for plaintext, bytesRead, hexEncoded, realHexEncoded in self.tests:
            expected = bytearray(codecs.decode(realHexEncoded, 'hex_codec'))
            result = gsmmodem.pdu._encodeAddressField(plaintext)
            self.assertEqual(result, expected, 'Failed to encode address field data "{0}". Expected: "{1}", got: "{2}"'.format(plaintext, realHexEncoded, codecs.encode(compat.str(result), 'hex_codec').upper()))

class TestSmsPduSmscFields(unittest.TestCase):
    """ Tests for SMS PDU SMSC-specific address fields (these methods are not meant to be public)

    Note: SMSC fields are encoded *slightly* differently from "normal" address fields (the length indicator is different)
    """
    
    def setUp(self):
        self.tests = (('+9876543210', 7, b'06918967452301', b'06918967452301'),
                 ('+9876543210', 7, b'06918967452301000000', b'06918967452301'), # same as above, but checking read limits
                 ('+987654321', 7, b'069189674523F1000000', b'069189674523F1'), 
                 ('+2782913593', 7, b'06917228195339', b'06917228195339'))
        
    def test_decodeSmscField(self):        
        for plaintext, bytesRead, hexEncoded, realHexEncoded in self.tests:
            byteIter = iter(bytearray(codecs.decode(hexEncoded, 'hex_codec')))
            resultValue, resultNumBytesRead = gsmmodem.pdu._decodeAddressField(byteIter, smscField=True)
            self.assertEqual(resultValue, plaintext, 'Failed to decode SMSC address field data "{0}". Expected: "{1}", got: "{2}"'.format(hexEncoded, plaintext, resultValue))
            self.assertEqual(resultNumBytesRead, bytesRead, 'Incorrect "number of bytes read" returned for data "{0}". Expected: "{1}", got: "{2}"'.format(hexEncoded, bytesRead, resultNumBytesRead))
    
    def test_encodeSmscField(self):
        for plaintext, bytesRead, hexEncoded, realHexEncoded in self.tests:
            expected = bytearray(codecs.decode(realHexEncoded, 'hex_codec'))
            result = gsmmodem.pdu._encodeAddressField(plaintext, smscField=True)
            self.assertEqual(result, expected, 'Failed to encode SMSC address field data "{0}". Expected: "{1}", got: "{2}"'.format(plaintext, realHexEncoded, codecs.encode(compat.str(result), 'hex_codec').upper()))


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
            self.assertEqual(result, tpVp, 'Failed to encode relative validity period: {0}. Expected: "{1}", got: "{2}"'.format(validity, tpVp, result))
            self.assertIsInstance(result, tpVp.__class__, 'Invalid data type returned; expected {0}, got {1}'.format(tpVp.__class__, result.__class__))
    
    def test_decode(self):
        for validity, tpVp in self.tests:
            result = gsmmodem.pdu._decodeRelativeValidityPeriod(tpVp)
            self.assertEqual(result, validity, 'Failed to decode relative validity period: {0}. Expected: "{1}", got: "{2}"'.format(tpVp, validity, result))
    
    def test_decode_invalidTpVp(self):
        tpVp = 2048 # invalid since > 255
        self.assertRaises(ValueError, gsmmodem.pdu._decodeRelativeValidityPeriod, tpVp)
    
    def test_encode_validityPeriodTooLong(self):
        validity = timedelta(weeks=1000)
        self.assertRaises(ValueError, gsmmodem.pdu._encodeRelativeValidityPeriod, validity)


class TestTimestamp(unittest.TestCase):
    """ Tests for SMS PDU timestamp encoding used for absolute validity period encoding/decoding (these methods are not meant to be public) """
    
    def setUp(self):
        self.tests = ((datetime(2015, 11, 27, 0, 0, 0, tzinfo=SimpleOffsetTzInfo(0)), b'51117200000000'),
                      (datetime(2015, 11, 27, 0, 0, 0, tzinfo=SimpleOffsetTzInfo(2)), b'51117200000080'), # same as previous but with GMT+2 timezone
                      (datetime(2007, 4, 12, 23, 25, 42, tzinfo=SimpleOffsetTzInfo(8)), b'70402132522423'),
                      (datetime(2007, 4, 12, 23, 25, 42, tzinfo=SimpleOffsetTzInfo(-8)), b'7040213252242B'), # same as previous but with GMT-8 timezone
                      )
    
    def test_encode(self):
        for timestamp, encodedHex in self.tests:
            encoded = bytearray(codecs.decode(encodedHex, 'hex_codec'))
            result = gsmmodem.pdu._encodeTimestamp(timestamp)
            self.assertEqual(result, encoded, 'Failed to encode timestamp: {0}. Expected: "{1}", got: "{2}"'.format(timestamp, encodedHex, codecs.encode(compat.str(result), 'hex_codec').upper()))
    
    def test_decode(self):
        for timestamp, encoded in self.tests:
            result = gsmmodem.pdu._decodeTimestamp(encoded)
            self.assertEqual(result, timestamp, 'Failed to decode timestamp: {0}. Expected: "{1}", got: "{2}"'.format(encoded, timestamp, result))
            
    def test_encode_noTimezone(self):
        """ Tests encoding without timezone information """
        timestamp = datetime(2013, 3, 1, 12, 30, 21)
        self.assertRaises(ValueError, gsmmodem.pdu._encodeTimestamp, timestamp)


class TestSmsPduTzInfo(unittest.TestCase):
    """ Basic tests for the SmsPduTzInfo class """
    
    def test_pickle(self):
        """ Ensure SmsPduTzInfo objects can be pickled (mentioneded as requirement of tzinfo implementations in Python docs) """
        import pickle
        obj = gsmmodem.pdu.SmsPduTzInfo('08')
        self.assertIsInstance(obj, gsmmodem.pdu.SmsPduTzInfo)
        pickledObj = pickle.dumps(obj)
        self.assertNotEqual(obj, pickledObj)
        unpickledObj = pickle.loads(pickledObj)
        self.assertIsInstance(unpickledObj, gsmmodem.pdu.SmsPduTzInfo)
        self.assertEqual(obj.utcoffset(0), unpickledObj.utcoffset(0))
    
    def test_dst(self):
        """ Test SmsPduTzInfo.dst() """
        obj = gsmmodem.pdu.SmsPduTzInfo('08')
        self.assertEqual(obj.dst(0), timedelta(0))
        
    def test_utcoffset(self):
        """ Test SmsPduTzInfo.utcoffest() """
        tests = (('08', 2), ('B2', -8))
        for pduOffsetStr, offset in tests:
            result = gsmmodem.pdu.SmsPduTzInfo(pduOffsetStr)
            expected = SimpleOffsetTzInfo(offset)
            self.assertEqual(result.utcoffset(0), expected.utcoffset(0))


class TestUdhConcatenation(unittest.TestCase):
    """ Tests for UDH concatenation information element """
    
    def setUp(self):
        self.tests = ((23, 1, 3, b'0003170301'), # 8-bit reference
                      (384, 2, 4, b'080401800402') # 16-bit reference
                      )
        
    def test_encode(self):
        for ref, number, parts, ieHex in self.tests:
            concatIe = gsmmodem.pdu.Concatenation()
            concatIe.reference = ref
            concatIe.number = number
            concatIe.parts = parts
            expected = bytearray(codecs.decode(ieHex, 'hex_codec'))
            result = concatIe.encode()
            self.assertEqual(result, expected, 'Failed to encode Concatenation Information Element; expected: "{0}", got: "{1}"'.format(ieHex, codecs.encode(compat.str(result), 'hex_codec').upper()))
            # Now modify some values and ensure encoded values changes
            concatIe.reference = ref+1
            result = concatIe.encode()
            self.assertNotEqual(result, expected, 'Modifications to UDH information element object not reflected in encode()')
    
    def test_decode(self):
        for ref, number, parts, ieHex in self.tests:
            ieData = bytearray(codecs.decode(ieHex, 'hex_codec'))
            # Test IE constructor with args
            result = gsmmodem.pdu.InformationElement(ieData[0], ieData[1], ieData[2:])
            self.assertIsInstance(result, gsmmodem.pdu.Concatenation, 'Invalid object type returned; expected Concatenation, got {0}'.format(type(result)))
            self.assertEqual(result.reference, ref, 'Invalid reference; expected {0}, got {1}'.format(ref, result.reference))
            self.assertEqual(result.number, number, 'Invalid part number; expected {0}, got {1}'.format(number, result.number))
            self.assertEqual(result.parts, parts, 'Invalid total number of parts; expected {0}, got {1}'.format(parts, result.parts))
            # Test IE constructor with kwargs
            result = gsmmodem.pdu.InformationElement(iei=ieData[0], ieLen=ieData[1], ieData=ieData[2:])
            self.assertIsInstance(result, gsmmodem.pdu.Concatenation, 'Invalid object type returned; expected Concatenation, got {0}'.format(type(result)))
            self.assertEqual(result.reference, ref, 'Invalid reference; expected {0}, got {1}'.format(ref, result.reference))
            self.assertEqual(result.number, number, 'Invalid part number; expected {0}, got {1}'.format(number, result.number))
            self.assertEqual(result.parts, parts, 'Invalid total number of parts; expected {0}, got {1}'.format(parts, result.parts))


class TestUdhPortAddress(unittest.TestCase):
    """ Tests for UDH application port addressing scheme information element """
    
    def setUp(self):
        self.tests = ((100, 50, b'04026432'), # 8-bit addresses
                      (1234, 5222, b'050404D21466') # 16-bit addresses
                      )
        
    def test_encode(self):
        for destination, source, ieHex in self.tests:
            portIe = gsmmodem.pdu.PortAddress()
            portIe.source = source
            portIe.destination = destination
            expected = bytearray(codecs.decode(ieHex, 'hex_codec'))
            result = portIe.encode()
            self.assertEqual(result, expected, 'Failed to encode PortAddress Information Element; expected: "{0}", got: "{1}"'.format(ieHex, codecs.encode(compat.str(result), 'hex_codec').upper()))
            # Now modify some values and ensure encoded values changes
            portIe.destination = destination+1
            result = portIe.encode()
            self.assertNotEqual(result, expected, 'Modifications to UDH information element object not reflected in encode()')
    
    def test_decode(self):
        for destination, source, ieHex in self.tests:
            ieData = bytearray(codecs.decode(ieHex, 'hex_codec'))
            # Test IE constructor with args
            result = gsmmodem.pdu.InformationElement(ieData[0], ieData[1], ieData[2:])
            self.assertIsInstance(result, gsmmodem.pdu.PortAddress, 'Invalid object type returned; expected Concatenation, got {0}'.format(type(result)))
            self.assertEqual(result.source, source, 'Invalid origin port number; expected {0}, got {1}'.format(source, result.source))
            self.assertEqual(result.destination, destination, 'Invalid destination port number; expected {0}, got {1}'.format(destination, result.destination))
            # Test IE constructor with kwargs
            result = gsmmodem.pdu.InformationElement(iei=ieData[0], ieLen=ieData[1], ieData=ieData[2:])
            self.assertIsInstance(result, gsmmodem.pdu.PortAddress, 'Invalid object type returned; expected Concatenation, got {0}'.format(type(result)))
            self.assertEqual(result.source, source, 'Invalid origin port number; expected {0}, got {1}'.format(source, result.source))
            self.assertEqual(result.destination, destination, 'Invalid destination port number; expected {0}, got {1}'.format(destination, result.destination))

class TestSmsPdu(unittest.TestCase):
    """ Tests encoding/decoding of SMS PDUs """

    def test_encodeSmsSubmit(self):
        """ Tests SMS PDU encoding """
        tests = (('+27820001111', 'Hello World!', 0, None, None, False, False, b'0001000B917228001011F100000CC8329BFD065DDF72363904'),
                 ('+27820001111', 'Flash SMS', 0, None, None, False, True, b'0005000B917228001011F10000094676788E064D9B53'),
                 ('+123456789', '世界您好！', 0, timedelta(weeks=52), '+44000000000', False, False, b'07914400000000F01100099121436587F90008F40A4E16754C60A8597DFF01'),
                 ('0126541234', 'Test message: local numbers', 13, timedelta(days=3), '12345', True, False, b'04A12143F5310D0AA110624521430000A91BD4F29C0E6A97E7F3F0B9AC03B1DFE3301BE4AEB7C565F91C'),
                 ('+27820001111', 'Timestamp validity test', 0, datetime(2013, 7, 10, 13, 39, tzinfo=SimpleOffsetTzInfo(2)), None, False, False, b'0019000B917228001011F100003170013193008017D474BB3CA787DB70903DCC4E93D3F43C885E9ED301'),
                 )
        for number, text, reference, validity, smsc, rejectDuplicates, sendFlash, pduHex in tests:
            pdu = bytearray(codecs.decode(pduHex, 'hex_codec'))
            result = gsmmodem.pdu.encodeSmsSubmitPdu(number, text, reference, validity, smsc, rejectDuplicates, sendFlash)
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 1, 'Only 1 PDU should have been created, but got {0}'.format(len(result)))
            self.assertIsInstance(result[0], gsmmodem.pdu.Pdu)
            self.assertEqual(result[0].data, pdu, 'Failed to encode SMS PDU for number: "{0}" and text "{1}". Expected: "{2}", got: "{3}"'.format(number, text, pduHex, codecs.encode(compat.str(result[0].data), 'hex_codec').upper()))

    def test_decode(self):
        """ Tests SMS PDU decoding """
        tests = ((b'06917228195339040B917228214365F700003130805120618005D4F29C2E03', {'type': 'SMS-DELIVER',
                                                                                     'smsc': '+2782913593',
                                                                                     'number': '+27821234567',
                                                                                     'protocol_id': 0,                                                            
                                                                                     'time': datetime(2013, 3, 8, 15, 2, 16, tzinfo=SimpleOffsetTzInfo(2)),
                                                                                     'text': 'Test2'}),
                 (b'07915892000000F0040B915892214365F700007040213252242331493A283D0795C3F33C88FE06C9CB6132885EC6D341EDF27C1E3E97E7207B3A0C0A5241E377BB1D7693E72E',
                  {'type': 'SMS-DELIVER',
                   'smsc': '+85290000000',
                   'number': '+85291234567',
                   'time': datetime(2007, 4, 12, 23, 25, 42, tzinfo=SimpleOffsetTzInfo(8)),
                   'text': 'It is easy to read text messages via AT commands.'}),
                 (b'06917228195339040B917228214365F70000313062315352800A800D8A5E98D337A910', 
                  {'type': 'SMS-DELIVER',
                   'number': '+27821234567',
                   'text': '@{tést}!'}),
                 (b'07911326040000F0310D0B911326880736F40000A90FF7FBDD454E87CDE1B0DB357EB701',
                  {'type': 'SMS-SUBMIT',
                   'smsc': '+31624000000',
                   'number': '+31628870634',
                   'validity': timedelta(days=3),
                   'text': 'www.diafaan.com'}),
                 (b'0006D60B911326880736F4111011719551401110117195714000',
                  {'type': 'SMS-STATUS-REPORT',
                   'number': '+31628870634',
                   'reference': 214}),
                 (b'0591721891F1400781721881F800003160526104848059050003C30101916536FB1DCABEEB2074D85E064941B19CAB060319A5C522289C96D3D3ED32286C0FA7D96131BBEC024941B19CAB0603DDD36C36A88C87A7E565D0DB0D82C55EB0DB4B068BCD5C20',
                  {'type': 'SMS-DELIVER',
                   'number': '2781188',
                   'smsc': '+2781191',
                   'text': 'Hello!You have R 19.50 FREE airtime available. R 19.50 will expire on 01/07/2013. ',
                   'udh': [gsmmodem.pdu.Concatenation(0x00, 0x03, [0xC3, 0x01, 0x01])]}),
                 (b'07914346466554F601000B914316565811F9000806304253F68449', # Valid UCS-2 PDU
                  {'type': 'SMS-SUBMIT',
                   'number': '+34616585119',
                   'smsc': '+34646456456',
                   'text': 'あ叶葉'}),
                 (b'0041010C910661345542F60008A0050003000301306F3044', # UCS-2 PDU; User data length is invalid in this PDU (too long)
                  {'type': 'SMS-SUBMIT',
                   'number': '+60164355246',
                   'smsc': None,
                   'udh': [gsmmodem.pdu.Concatenation(0x00, 0x03, [0x00, 0x03, 0x01])],
                   'text': 'はい'}),
                 (b'0591721891F101000B917228214365F700040C48656C6C6F20776F726C6421', # 8-bit data coding
                  {'type': 'SMS-SUBMIT',
                   'number': '+27821234567',
                   'smsc': '+2781191',
                   'text': 'Hello world!'}),
                 (b'0019000B917228001011F100003170013193008017D474BB3CA787DB70903DCC4E93D3F43C885E9ED301', # absolute validity period
                  {'text': 'Timestamp validity test',
                   'validity': datetime(2013, 7, 10, 13, 39, tzinfo=SimpleOffsetTzInfo(2))}),
                 # Semi-invalid status report PDU captured from a ZTE modem 
                 (b'0297F1061C0F910B487228297020F5317062419272803170624192138000',
                  {'type': 'SMS-STATUS-REPORT',
                   'number': '+b08427829207025', # <- broken number (invalid PDU data; the reference number is more than a single byte (or they added something))
                   'reference': 28,
                   'time': datetime(2013, 7, 26, 14, 29, 27, tzinfo=SimpleOffsetTzInfo(2)),
                   'discharge': datetime(2013, 7, 26, 14, 29, 31, tzinfo=SimpleOffsetTzInfo(2))}),
                 (b'07919762020033F1400DD0CDF2396C7EBB010008415072411084618C0500035602010053004D005300200063006F00640065003A00200034003800350036002C00200063006F006E006600690072006D006100740069006F006E0020006F00660020006100730073006F00630069006100740069006F006E0020006200650074007700650065006E0020006100630063006F0075006E007400200061006E00640020004D00650067',
                  {'type': 'SMS-DELIVER',
                   'smsc': '+79262000331',
                   'number': 'Megafon',
                   'text': 'SMS code: 4856, confirmation of association between account and Meg',
                   'time': datetime(2014, 5, 27, 14, 1, 48, tzinfo=SimpleOffsetTzInfo(4))})
                 )

        for pdu, expected in tests:
            result = gsmmodem.pdu.decodeSmsPdu(pdu)
            self.assertIsInstance(result, dict)
            for key, value in expected.items():
                self.assertIn(key, result)
                if key == 'udh':
                    self.assertEqual(len(result[key]), len(value), 'Incorrect number of UDH information elements; expected {0}, got {1}'.format(len(result[key]), len(value)))
                    for i in range(len(value)):
                        got = result[key][i]
                        expected = value[i]
                        self.assertIsInstance(got, expected.__class__)
                        self.assertEqual(expected.id, got.id)
                        self.assertEqual(expected.dataLength, got.dataLength)
                        self.assertEqual(expected.data, got.data)
                        if isinstance(expected, gsmmodem.pdu.Concatenation):
                            self.assertEqual(got.reference, expected.reference)
                            self.assertEqual(got.parts, expected.parts)
                            self.assertEqual(got.number, expected.number)
                        elif isinstance(expected, gsmmodem.pdu.PortAddress):
                            self.assertEqual(got.destination, expected.destination)
                            self.assertEqual(got.source, expected.source)
                else:
                    self.assertEqual(result[key], value, 'Failed to decode PDU value for "{0}". Expected "{1}", got "{2}".'.format(key, value, result[key]))

    def test_encodeSmsSubmit_concatenated(self):
        """ Tests concatenated SMS encoding """
        tests = (('Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.Ut enim ad minim veniam, quinostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.Duis aute irure dolor in reprehenderit in voluptate velit esse cillum doloe eu fugiat nulla pariatur.Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum',
                  '+15125551234',
                  [b'0045000B915121551532F40000A0050003000301986F79B90D4AC3E7F53688FC66BFE5A0799A0E0AB7CB741668FC76CFCB637A995E9783C2E4343C3D4F8FD3EE33A8CC4ED359A079990C22BF41E5747DDE7E9341F4721BFE9683D2EE719A9C26D7DD74509D0E6287C56F791954A683C86FF65B5E06B5C36777181466A7E3F5B0AB4A0795DDE936284C06B5D3EE741B642FBBD3E1360B14AFA7DD',
                   b'0045000B915121551532F40000A0050003000302DE73BABC4E0695F165F9384D0FD3D36F37A8CE6687DBE337881D16BFE5E939C89D9EA741753A28CC4EC7EB6938A88C0795C3A0F1BBDD7E93DFA0F1DB3D2FC7EB61BA8B584FCF41E13ABD0C4ACBEBF23288FC66BFE5A0B41B242FC3E56574D94D2ECBD37450DA0DB2BFD975383D4C2F83EC65769A0E2ACFE765D038CD66D7DB20F29BFD2E83CA',
                   b'0045000B915121551532F400008C050003000303EA2073FD9C0ED341EE3A9B1D06C1C3F274985E97BB8AF871194E2FD7E5A079DA4D07BDC7E370791CA683C675789A1CA687E920F7DB0D82CBDF6972D94D6781E675371D947683C675363C0C8AD7D3A0B7D99C1EA7C32072795E96D7DD7450FBCD66A7E9A0B03BDD06A5C9A0F29C0E6287C56F79BD0D']
                 ),)
        for text, number, hexPdus in tests:
            result = gsmmodem.pdu.encodeSmsSubmitPdu(number, text, reference=0, requestStatusReport=False, rejectDuplicates=True)
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), len(hexPdus), 'Invalid number of PDUs returned; expected {0}, got {1}'.format(len(hexPdus), len(result)))
            i = 0
            for pdu in result:
                self.assertIsInstance(pdu, gsmmodem.pdu.Pdu)
                expectedPduHex = hexPdus[i]
                expectedPdu = bytearray(codecs.decode(expectedPduHex, 'hex_codec'))
                self.assertEqual(pdu.data, expectedPdu, 'Failed to encode concatentated SMS PDU (PDU {0}/{1}). Expected: "{2}", got: "{3}"'.format(i+1, len(result), expectedPduHex, codecs.encode(compat.str(pdu.data), 'hex_codec').upper()))
                i += 1
    
    def test_encodeSmsSubmit_invalidValidityType(self):
        """ Tests SMS PDU encoding when specifying an invalid object type for validity """
        self.assertRaises(TypeError, gsmmodem.pdu.encodeSmsSubmitPdu, **{'number': '123', 'text': 'abc', 'validity': 'INVALID'})
    
    def test_decode_invalidPduType(self):
        """ Tests SMS PDU decoding when an invalid PDU type is specified """
        # PDU first octect: 0x43; thus PDU type: 0x03 (invalid)
        pdu = '0043010C910661345542F60008A0050003000301306F3044'
        self.assertRaises(gsmmodem.exceptions.EncodingError, gsmmodem.pdu.decodeSmsPdu, pdu)
    
    def test_decode_invalidData(self):
        """ Tests SMS PDU decoding when completely invalid data is specified """
        pdu = 'AFSDSDF LJJFKLDJKLFJ# #$KJLKJL SF'
        self.assertRaises(gsmmodem.exceptions.EncodingError, gsmmodem.pdu.decodeSmsPdu, pdu)
        pdu = 'AEFDSDFSDFSDFS'
        self.assertRaises(gsmmodem.exceptions.EncodingError, gsmmodem.pdu.decodeSmsPdu, pdu)


if __name__ == "__main__":
    unittest.main()