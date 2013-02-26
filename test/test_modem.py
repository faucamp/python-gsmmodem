#!/usr/bin/env python

""" Test suite for gsmmodem.modem """

from __future__ import print_function

import time
import unittest

import gsmmodem.serial_comms
import gsmmodem.modem

class MockSerialPackage():
    """ Fake serial package for the GsmModem/SerialComms classes to import during tests """

    class Serial():
        """ Mock serial object for use by the GsmModem class during tests """
        def __init__(self, *args, **kwargs):
            # The default value to read/"return" if responseSequence isn't set up, or None for nothing
            self.defaultResponse = 'OK\r\n'
            self.responseSequence = []
            self.flushResponseSequence = False
            self.writeQueue = []
            self._alive = True
            self._readQueue = []
            self.writeCallbackFunc = None
        
        def read(self, timeout=None):
            if len(self._readQueue) > 0:                
                return self._readQueue.pop(0)                        
            elif len(self.writeQueue) > 0:               
                self._setupReadValue(self.writeQueue.pop(0))
                if len(self._readQueue) > 0:
                    return self._readQueue.pop(0)
            elif self.flushResponseSequence and len(self.responseSequence) > 0:
                self._setupReadValue(None)
            
            if timeout > 0.2:
                time.sleep(min(timeout, 0.2))                
                if timeout > 0.2 and len(self.writeQueue) == 0:
                    time.sleep(timeout - 0.2)
                return ''
            else:
                while self._alive:
                    if len(self.writeQueue) > 0:                        
                        self._setupReadValue(self.writeQueue.pop(0))
                        if len(self._readQueue) > 0:
                            return self._readQueue.pop(0)                       
                    time.sleep(0.2)
                    
        def _setupReadValue(self, command):
            if len(self._readQueue) == 0:                
                if len(self.responseSequence) > 0:                    
                    value = self.responseSequence.pop(0)                    
                    if type(value) in (float, int):
                        time.sleep(value)                        
                        if len(self.responseSequence) > 0:                            
                            self._setupReadValue(command)                        
                    else:                        
                        self._readQueue = list(value)
                elif self.defaultResponse != None:
                    self._readQueue = list(self.defaultResponse)            
                
        def write(self, data):
            print('Serial.write(): ', data)
            if self.writeCallbackFunc != None:
                self.writeCallbackFunc(data)
            self.writeQueue.append(data)
            
        def close(self):
            pass
            
        def inWaiting(self):
            return len(self._readQueue)        
    
    class SerialException(Exception):
        """ Mock serial exception """
 
class TestGsmModemGeneralApi(unittest.TestCase):
    """ Tests the API of GsmModem class (excluding connect/close) """
    
    def setUp(self):
        # Override the pyserial import
        self.mockSerial = MockSerialPackage()
        gsmmodem.serial_comms.serial = self.mockSerial
        self.modem = gsmmodem.modem.GsmModem('-- PORT IGNORED DURING TESTS --')        
        self.modem.connect()
    
    def tearDown(self):
        self.modem.close()
    
    def test_sendUssd(self):
        # tests tuple format: (USSD_STRING_TO_WRITE, MODEM_WRITE, MODEM_RESPONSE, USSD_MESSAGE, USSD_SESSION_ACTIVE)
        tests = [('*101#', 'AT+CUSD=1,"*101#",15\r', '+CUSD: 0,"Available Balance: R 96.45 .",15\r\n', 'Available Balance: R 96.45 .', False),
                 ('*120*500#', 'AT+CUSD=1,"*120*500#",15\r', '+CUSD: 1,"Hallo daar",15\r\n', 'Hallo daar', True)]                     
                
        for test in tests:            
            def writeCallbackFunc(data):                
                self.assertEqual(test[1], data, 'Invalid data written to modem; expected "{}", got: "{}"'.format(test[1], data))                            
            self.modem.serial.responseSequence = ['OK\r\n', 0.3, test[2]]
            self.modem.serial.flushResponseSequence = True
            self.modem.serial.writeCallbackFunc = writeCallbackFunc
            ussd = self.modem.sendUssd(test[0])
            self.assertIsInstance(ussd, gsmmodem.modem.Ussd)
            self.assertEqual(ussd.sessionActive, test[4], 'Session state is invalid for test case: {}'.format(test))
            self.assertEquals(ussd.message, test[3])
        
    

if __name__ == "__main__":
    unittest.main()
