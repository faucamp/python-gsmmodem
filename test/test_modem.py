#!/usr/bin/env python

""" Test suite for gsmmodem.modem """

from __future__ import print_function

import time
import unittest

import compat # For Python 2.6 compatibility
import gsmmodem.serial_comms
import gsmmodem.modem

class MockSerialPackage():
    """ Fake serial package for the GsmModem/SerialComms classes to import during tests """

    class Serial():
        
        _REPONSE_TIME = 0.1
        
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
            
            if timeout != None:
                time.sleep(min(timeout, self._REPONSE_TIME))                
                if timeout > self._REPONSE_TIME and len(self.writeQueue) == 0:
                    time.sleep(timeout - self._REPONSE_TIME)
                return ''
            else:
                while self._alive:
                    if len(self.writeQueue) > 0:
                        self._setupReadValue(self.writeQueue.pop(0))
                        if len(self._readQueue) > 0:
                            return self._readQueue.pop(0)                       
                    time.sleep(self._REPONSE_TIME)
                    
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
                self.assertEqual(test[1], data, 'Invalid data written to modem; expected "{0}", got: "{1}"'.format(test[1], data))                            
            self.modem.serial.responseSequence = ['OK\r\n', 0.3, test[2]]
            self.modem.serial.flushResponseSequence = True
            self.modem.serial.writeCallbackFunc = writeCallbackFunc
            ussd = self.modem.sendUssd(test[0])
            self.assertIsInstance(ussd, gsmmodem.modem.Ussd)
            self.assertEqual(ussd.sessionActive, test[4], 'Session state is invalid for test case: {0}'.format(test))
            self.assertEquals(ussd.message, test[3])
        
    def test_manufacturer(self):
        def writeCallbackFunc(data):
            self.assertEqual('AT+CGMI\r', data, 'Invalid data written to modem; expected "{0}", got: "{1}"'.format('AT+CGMI\r', data))
        self.modem.serial.writeCallbackFunc = writeCallbackFunc
        tests = ['huawei', 'ABCDefgh1235', 'Some Random Manufacturer']
        for test in tests:
            self.modem.serial.responseSequence = ['{0}\r\n'.format(test), 'OK\r\n']
            self.modem.serial.flushResponseSequence = True
            self.assertEqual(test, self.modem.manufacturer)
    
    def test_model(self):
        def writeCallbackFunc(data):
            self.assertEqual('AT+CGMM\r', data, 'Invalid data written to modem; expected "{0}", got: "{1}"'.format('AT+CGMM\r', data))
        self.modem.serial.writeCallbackFunc = writeCallbackFunc
        tests = ['K3715', '1324-Qwerty', 'Some Random Model']
        for test in tests:
            self.modem.serial.responseSequence = ['{0}\r\n'.format(test), 'OK\r\n']
            self.modem.serial.flushResponseSequence = True
            self.assertEqual(test, self.modem.model)
            
    def test_revision(self):
        def writeCallbackFunc(data):
            self.assertEqual('AT+CGMR\r', data, 'Invalid data written to modem; expected "{0}", got: "{1}"'.format('AT+CGMR\r', data))
        self.modem.serial.writeCallbackFunc = writeCallbackFunc
        tests = ['1', '1324-56768-23414', 'r987']
        for test in tests:
            self.modem.serial.responseSequence = ['{0}\r\n'.format(test), 'OK\r\n']
            self.modem.serial.flushResponseSequence = True
            self.assertEqual(test, self.modem.revision)
        # Fake a modem that does not support this command
        self.modem.serial.defaultResponse = 'ERROR\r\n'
        self.assertEqual(None, self.modem.revision)
    
    def test_imei(self):
        def writeCallbackFunc(data):
            self.assertEqual('AT+CGSN\r', data, 'Invalid data written to modem; expected "{0}", got: "{1}"'.format('AT+CGSN\r', data))
        self.modem.serial.writeCallbackFunc = writeCallbackFunc
        tests = ['012345678912345']
        for test in tests:
            self.modem.serial.responseSequence = ['{0}\r\n'.format(test), 'OK\r\n']
            self.modem.serial.flushResponseSequence = True
            self.assertEqual(test, self.modem.imei)
            
    def test_imsi(self):
        def writeCallbackFunc(data):
            self.assertEqual('AT+CIMI\r', data, 'Invalid data written to modem; expected "{0}", got: "{1}"'.format('AT+CIMI\r', data))
        self.modem.serial.writeCallbackFunc = writeCallbackFunc
        tests = ['987654321012345']
        for test in tests:
            self.modem.serial.responseSequence = ['{0}\r\n'.format(test), 'OK\r\n']
            self.modem.serial.flushResponseSequence = True
            self.assertEqual(test, self.modem.imsi)
    
    def test_supportedCommands(self):
        def writeCallbackFunc(data):
            self.assertEqual('AT+CLAC\r', data, 'Invalid data written to modem; expected "{0}", got: "{1}"'.format('AT+CLAC\r', data))
        self.modem.serial.writeCallbackFunc = writeCallbackFunc
        tests = (('&C,D,E,\S,+CGMM,^DTMF', ['&C', 'D', 'E', '\S', '+CGMM', '^DTMF']),
                 ('Z', ['Z']))
        for test in tests:
            self.modem.serial.responseSequence = ['+CLAC:{0}\r\n'.format(test[0]), 'OK\r\n']
            self.modem.serial.flushResponseSequence = True
            commands = self.modem.supportedCommands
            self.assertListEqual(commands, test[1])
        # Fake a modem that does not support this command
        self.modem.serial.defaultResponse = 'ERROR\r\n'
        commands = self.modem.supportedCommands
        self.assertEqual(commands, None)
        
            
class TestGsmModemDial(unittest.TestCase):
    
    def init_modem(self):
        self.mockSerial = MockSerialPackage()
        gsmmodem.serial_comms.serial = self.mockSerial
        self.modem = gsmmodem.modem.GsmModem('-- PORT IGNORED DURING TESTS --')        
        self.modem.connect()
        
    def test_dial(self):
        self.init_modem()
        
        tests = (['0123456789', '1', '0'],
                 ['5551112223', '3', '0'])
        
        for number, callId, callType in tests: 
            def writeCallbackFunc(data):
                self.assertEqual('ATD{0};\r'.format(number), data, 'Invalid data written to modem; expected "{0}", got: "{1}"'.format('ATD{0};\r'.format(number), data))
            self.modem.serial.writeCallbackFunc = writeCallbackFunc
            self.modem.serial.responseSequence = ['OK\r\n', '^ORIG:{0},{1}\r\n'.format(callId, callType), 0.2, '^CONF:{0}\r\n'.format(callId)]
            self.modem.serial.flushResponseSequence = True
            call = self.modem.dial(number)
            self.assertIsInstance(call, gsmmodem.modem.Call)
            self.assertIs(call.number, number)
            self.assertFalse(call.answered, 'Call state invalid: should not yet be answered')            
            self.assertIn(call.id, self.modem.activeCalls)
            self.assertEqual(len(self.modem.activeCalls), 1)
            # Fake an answer
            while len(self.modem.serial._readQueue) > 0:
                time.sleep(0.1)
            self.modem.serial._readQueue = list('^CONN:{0},{1}\r\n'.format(callId, callType))
            # Wait a bit for the event to be picked up
            while len(self.modem.serial._readQueue) > 0:
                time.sleep(0.1)
            self.assertTrue(call.answered, 'Remote call answer was not detected')
            def hangupCallback(data):
                self.assertEqual('ATH\r'.format(number), data, 'Invalid data written to modem; expected "{0}", got: "{1}"'.format('ATH\r'.format(number), data))
            self.modem.serial.writeCallbackFunc = hangupCallback
            call.hangup()
            self.assertFalse(call.answered, 'Hangup call did not change call state')
            self.assertNotIn(call.id, self.modem.activeCalls)
            self.assertEqual(len(self.modem.activeCalls), 0)
            # Check remote hangup detection
            self.modem.serial.writeCallbackFunc = writeCallbackFunc
            self.modem.serial.responseSequence = ['OK\r\n', '^ORIG:{0},{1}\r\n'.format(callId, callType), '^CONF:{0}\r\n'.format(callId), '^CONN:{0},{1}\r\n'.format(callId, callType)]
            self.modem.serial.flushResponseSequence = True
            call = self.modem.dial(number)
            # Wait a bit for the event to be picked up
            while len(self.modem.serial._readQueue) > 0:
                time.sleep(0.1)
            self.assertTrue(call.answered, 'Remote call answer was not detected')
            self.assertIn(call.id, self.modem.activeCalls)
            self.assertEqual(len(self.modem.activeCalls), 1)
            # Now fake a remote hangup
            self.modem.serial._readQueue = list('^CEND:{0},5,29,16\r\n'.format(callId))
            # Wait a bit for the event to be picked up
            while len(self.modem.serial._readQueue) > 0:
                time.sleep(0.1)
            self.assertFalse(call.answered, 'Remote hangup was not detected')
            self.assertNotIn(call.id, self.modem.activeCalls)
            self.assertEqual(len(self.modem.activeCalls), 0)

class TestIncomingCall(unittest.TestCase):
    
    def test_incomingCallAnswer(self):
        mockSerial = MockSerialPackage()
        gsmmodem.serial_comms.serial = mockSerial
        
        callReceived = [False]
        def incomingCallCallbackFunc(call):
            try:
                self.assertIsInstance(call, gsmmodem.modem.IncomingCall)
                self.assertIn(call.id, self.modem.activeCalls)
                self.assertEqual(len(self.modem.activeCalls), 1)
                self.assertFalse(call.answered, 'Call state invalid: should not yet be answered')
                self.assertIsInstance(call.type, int)
                self.assertEqual(call.type, callReceived[1], 'Invalid call type; expected {0}, got {1}'.format(callReceived[1], call.type))
                def writeCallbackFunc1(data):
                    self.assertEqual('ATA\r', data, 'Invalid data written to modem; expected "{0}", got: "{1}"'.format('ATA\r', data))
                self.modem.serial.writeCallbackFunc = writeCallbackFunc1
                call.answer()
                self.assertTrue(call.answered, 'Call state invalid: should be answered')
                def writeCallbackFunc2(data):
                    self.assertEqual('ATH\r', data, 'Invalid data written to modem; expected "{0}", got: "{1}"'.format('ATH\r', data))
                self.modem.serial.writeCallbackFunc = writeCallbackFunc2
                call.hangup()
                self.assertFalse(call.answered, 'Call state invalid: hangup did not change call state')
                self.assertNotIn(call.id, self.modem.activeCalls)
                self.assertEqual(len(self.modem.activeCalls), 0)
            finally:
                callReceived[0] = True
        
        self.modem = gsmmodem.modem.GsmModem('-- PORT IGNORED DURING TESTS --', incomingCallCallbackFunc=incomingCallCallbackFunc)        
        self.modem.connect()
        
        tests = (('+27820001234', 'VOICE', 0),)
        
        for number, cringParam, callType in tests: 
            callReceived = [False, callType]
            # Fake incoming voice call
            self.modem.serial._readQueue = list('+CRING: {0}\r\n+CLIP: "{1}",145,,,,0\r\n'.format(cringParam, number))
            # Wait a bit for the event to be picked up
            while callReceived[0] == False:
                time.sleep(0.1)
        
        
if __name__ == "__main__":
    unittest.main()
