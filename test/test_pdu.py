#!/usr/bin/env python

""" Test suite for SMS PDU encoding/decoding algorithms """

import sys, unittest

    
import compat # For Python 2.6 compatibility
import gsmmodem.pdu

class TestReverseNibble(unittest.TestCase):
    """ Tests the reverse nibble encoding algorithm """
    
    def test_encode(self):
        """ Tests the reverse nibble encoding algorithm """
        tests = (('15125551234', bytearray([0x51, 0x21, 0x55, 0x15, 0x32, 0xf4])),)
        for plaintext, encoded in tests:
            result = gsmmodem.pdu.encodeReverseNibble(plaintext)
            self.failUnlessEqual(result, encoded, 'Failed to reverse nibble encode plaintext string: "{0}". Expected: "{1}", got: "{2}"'.format(plaintext, encoded, result))


class TestGsm7(unittest.TestCase):
    """ Tests the GSM-7 encoding/decoding algorithms """    
    
    def test_encode(self):
        """ Tests GSM-7 encoding algorithm """
        tests = (('a', chr(97)),
                 ('Hello World!', bytearray([0x48, 0x65, 0x6C, 0x6C, 0x6F, 0x20, 0x57, 0x6F, 0x72, 0x6C, 0x64, 0x21])))
        
        for plaintext, encoded in tests:
            result = gsmmodem.pdu.encodeGsm7(plaintext)
            self.failUnlessEqual(result, encoded, 'Failed to GSM-7 encode plaintext string: "{0}". Expected: "{1}", got: "{2}"'.format(plaintext, encoded, result))
       
if __name__ == "__main__":
    unittest.main()