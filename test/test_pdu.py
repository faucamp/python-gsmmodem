#!/usr/bin/env python

""" Test suite for SMS PDU encoding/decoding algorithms """

import sys, unittest

    
import compat # For Python 2.6 compatibility
import gsmmodem.pdu

class TestReverseNibble(unittest.TestCase):
    """ Tests the reverse nibble encoding algorithm """
    
    def test_encode(self):
        """ Tests the reverse nibble encoding algorithm """
        tests = (('15125551234', bytearray([0x51, 0x21, 0x55, 0x15, 0x32, 0xf4])),
                 ('123', bytearray([0x21, 0xf3])),
                 ('1234', bytearray([0x21, 0x43])),)
        for plaintext, encoded in tests:
            result = gsmmodem.pdu.encodeReverseNibble(plaintext)
            self.failUnlessEqual(result, encoded, 'Failed to reverse nibble encode plaintext string: "{0}". Expected: "{1}", got: "{2}"'.format(plaintext, [b for b in encoded], [b for b in result]))


class TestGsm7(unittest.TestCase):
    """ Tests the GSM-7 encoding/decoding algorithms """    
    
    def setUp(self):
        self.tests = (('abc', chr(97) + chr(98) + chr(99), bytearray([0x61, 0xf1, 0x18])),
                      ('Hello World!', bytearray([0x48, 0x65, 0x6C, 0x6C, 0x6F, 0x20, 0x57, 0x6F, 0x72, 0x6C, 0x64, 0x21]), bytearray([200, 50, 155, 253, 6, 93, 223, 114, 54, 57, 4])),
                      ('[{abc}]~', bytearray([0x1B, 0x3C, 0x1B, 0x28, 0x61, 0x62, 0x63, 0x1B, 0x29, 0x1B, 0x3E, 0x1B, 0x3D]), bytearray([27, 222, 6, 21, 22, 143, 55, 169, 141, 111, 211, 3])),
                      ("Howdy y'all!", bytearray([0x48, 0x6F, 0x77, 0x64, 0x79, 0x20, 0x79, 0x27, 0x61, 0x6C, 0x6C, 0x21]), bytearray([0xC8, 0xF7, 0x9D, 0x9C, 0x07, 0xE5, 0x4F, 0x61, 0x36, 0x3B, 0x04])))
    
    def test_encode(self):
        """ Tests GSM-7 encoding algorithm """
        for plaintext, encoded, septets in self.tests:
            result = gsmmodem.pdu.encodeGsm7(plaintext)
            self.failUnlessEqual(result, encoded, 'Failed to GSM-7 encode plaintext string: "{0}". Expected: "{1}", got: "{2}"'.format(plaintext, [b for b in encoded], [b for b in result]))

    def test_decode(self):
        """ Tests GSM-7 decoding algorithm """
        for plaintext, encoded, septets in self.tests:
            result = gsmmodem.pdu.decodeGsm7(encoded)
            self.failUnlessEqual(result, plaintext, 'Failed to decode GSM-7 string: "{0}". Expected: "{1}", got: "{2}"'.format([b for b in encoded], plaintext, result))
            
    def test_packSeptets(self):
        """ Tests the septet-packing alogrithm for GSM-7-encoded strings """
        for plaintext, encoded, septets in self.tests:
            result = gsmmodem.pdu.packSeptets(encoded)
            self.failUnlessEqual(result, septets, 'Failed to pack GSM-7 octets into septets for string: "{0}". Expected: "{1}", got: "{2}"'.format(plaintext, [b for b in septets], [b for b in result]))


class TestSmsPdu(unittest.TestCase):
    """ Tests encoding/decoding of SMS PDUs """
    
    def setUp(self):
        self.tests = (('+27820001111', 'Hello World!', bytearray([0x00, 0x01, 0x00, 0x0B, 0x91, 114, 40, 0, 16, 17, 241, 0x00, 0x00, 0x0C, 200, 50, 155, 253, 6, 93, 223, 114, 54, 57, 4])),)    

    def test_encode(self):
        """ Tests SMS PDU encoding """
        for number, text, pdu in self.tests:
            result = gsmmodem.pdu.encodeSmsPdu(number, text)
            self.failUnlessEqual(result, pdu, 'Failed to encode SMS PDU for number: "{0}" and text "{1}". Expected: "{2}", got: "{3}"'.format(number, text, [b for b in pdu], [b for b in result]))


if __name__ == "__main__":
    unittest.main()