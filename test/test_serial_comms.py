#!/usr/bin/env python

""" Test suite for gsmmodem.serial_comms """

from __future__ import print_function

import sys, time, unittest, logging
from copy import copy

from . import compat # For Python 2.6 compatibility

import gsmmodem.serial_comms
from gsmmodem.exceptions import TimeoutException

class MockSerialPackage(object):
    """ Fake serial package for the GsmModem/SerialComms classes to import during tests """
    
    class Serial():
        
        _REPONSE_TIME = 0.02
        
        """ Mock serial object for use by the GsmModem class during tests """
        def __init__(self, *args, **kwargs):
            # The default value to read/"return" if responseSequence isn't set up, or None for nothing
            #self.defaultResponse = 'OK\r\n'
            self.responseSequence = []
            self.flushResponseSequence = True
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
                time.sleep(0.001)
#                time.sleep(min(timeout, self._REPONSE_TIME))                
#                if timeout > self._REPONSE_TIME and len(self.writeQueue) == 0:
#                    time.sleep(timeout - self._REPONSE_TIME)
                return ''
            else:
                while self._alive:
                    if len(self.writeQueue) > 0:
                        self._setupReadValue(self.writeQueue.pop(0))
                        if len(self._readQueue) > 0:
                            return self._readQueue.pop(0)                       
#                    time.sleep(self._REPONSE_TIME)
                    time.sleep(0.05)
                    
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

        def write(self, data):            
            if self.writeCallbackFunc != None:
                self.writeCallbackFunc(data)
            self.writeQueue.append(data)
            
        def close(self):
            pass
            
        def inWaiting(self):
            rqLen = len(self._readQueue)
            for item in self.responseSequence:
                if type(item) in (int, float):
                    break
                else:
                    rqLen += len(item)
            return rqLen
            
    
    class SerialException(Exception):
        """ Mock Serial Exception """

class TestNotifications(unittest.TestCase):
    """ Tests reading unsolicited notifications from the serial devices """
    
    def setUp(self):
        self.mockSerial = MockSerialPackage()
        gsmmodem.serial_comms.serial = self.mockSerial
        self.tests = (['ABC\r\n'], 
                      [' blah blah blah \r\n', '12345\r\n'])

    def test_callback(self):
        """ Tests if the notification callback method is correctly called """        
        for test in self.tests:
            callbackCalled = [False]
            def callback(data):
                callbackCalled[0] = [True]
                self.assertIsInstance(data, list)
                self.assertEqual(len(data), len(test))
                for i in range(len(test)):
                    self.assertEqual(data[i], test[i][:-2])
        
            serialComms = gsmmodem.serial_comms.SerialComms('-- PORT IGNORED DURING TESTS --', notifyCallbackFunc=callback)
            serialComms.connect()
            # Fake a notification
            serialComms.serial.responseSequence = copy(test)
            # Wait a bit for the event to be picked up
            while len(serialComms.serial._readQueue) > 0 or len(serialComms.serial.responseSequence) > 0:
                time.sleep(0.05)
            self.assertTrue(callbackCalled[0], 'Notification callback function not called')
            serialComms.close()
    
    def test_noCallback(self):
        """ Tests notifications when no callback method was specified (nothing should happen) """
        for test in self.tests:
            serialComms = gsmmodem.serial_comms.SerialComms('-- PORT IGNORED DURING TESTS --')
            serialComms.connect()
            # Fake a notification
            serialComms.serial.responseSequence = copy(test)
            # Wait a bit for the event to be picked up
            while len(serialComms.serial._readQueue) > 0 or len(serialComms.serial.responseSequence) > 0:
                time.sleep(0.05)            
            serialComms.close()

class TestSerialException(unittest.TestCase):
    """ Tests SerialException handling """
    
    def setUp(self):
        self.mockSerial = MockSerialPackage()
        gsmmodem.serial_comms.serial = self.mockSerial
        self.serialComms = gsmmodem.serial_comms.SerialComms('-- PORT IGNORED DURING TESTS --')
        self.serialComms.connect()
    
    def tearDown(self):
        self.serialComms.close()        

    def test_readLoopException(self):
        """ Tests handling a SerialException from inside the read loop thread """
        self.assertTrue(self.serialComms.alive)
        exceptionRaised = [False]
        callbackCalled = [False]
        
        def brokenRead(*args, **kwargs):
            exceptionRaised[0] = True
            raise MockSerialPackage.SerialException()        
        self.serialComms.serial.read = brokenRead
        
        def errorCallback(ex):
            callbackCalled[0] = True
            self.assertIsInstance(ex, MockSerialPackage.SerialException)
        self.serialComms.fatalErrorCallback = errorCallback
        
        # Let the serial comms object attempt to read something
        self.serialComms.serial.responseSequence = ['12345\r\n']
        while not exceptionRaised[0]:
            time.sleep(0.05)        
        self.assertFalse(self.serialComms.alive)
        time.sleep(0.05)
        self.assertTrue(callbackCalled[0], 'Error callback not called on fatal error')


class TestWrite(unittest.TestCase):
    """ Tests writing to the serial device """
     
    def setUp(self):
        self.mockSerial = MockSerialPackage()
        gsmmodem.serial_comms.serial = self.mockSerial
        self.serialComms = gsmmodem.serial_comms.SerialComms('-- PORT IGNORED DURING TESTS --')
        self.serialComms.connect()
    
    def tearDown(self):
        self.serialComms.close()
        
    def test_write(self):
        """ Tests basic writing operations """
        tests = ((['OK\r\n'], ['OK']),
                 (['ERROR\r\n'], ['ERROR']),
                 (['first line\r\n', 'second line\r\n', 'OK\r\n'], ['first line', 'second line', 'OK']),
                 # Some Huawei modems issue this response instead of ERROR for unknown commands; ensure we detect it correctly
                 (['COMMAND NOT SUPPORT\r\n'], ['COMMAND NOT SUPPORT']))
        for actual, expected in tests:
            self.serialComms.serial.responseSequence = actual
            self.serialComms.serial.flushResponseSequence = True
            response = self.serialComms.write('test\r')            
            self.assertEqual(response, expected)
            # Now write without expecting a response
            response = self.serialComms.write('test2\r', waitForResponse=False)
            self.assertEqual(response, None) 
    
    def test_writeTimeout(self):
        """ Tests that the serial comms write timeout parameter """
        # Serial comms will not response (no response sequence specified)
        self.assertRaises(TimeoutException, self.serialComms.write, 'test\r', waitForResponse=True, timeout=0.1)

    def test_writeTimeout_data(self):
        """ Tests passing partial data along with a TimeoutException """
        self.serialComms.serial.responseSequence = ['abc\r\n', 0.5, 'def\r\n']
        self.serialComms.serial.flushResponseSequence = True
        try:
            self.serialComms.write('test\r', waitForResponse=True, timeout=0.1)
        except TimeoutException as timeout:
            # The 0.5s pause in the response should cause the write to timeout but still return the first part
            self.assertEqual(timeout.data, ['abc'])
        else:
            self.fail('TimeoutException not thrown')
    
    def test_writeTimeout_noData(self):
        """ Similar to test_writeTimeout(), but checks TimeoutException's data field is None """
        try:
            self.serialComms.write('test\r', waitForResponse=True, timeout=0.1)
        except TimeoutException as timeout:
            self.assertEqual(timeout.data, None)
        else:
            self.fail('TimeoutException not thrown')


if __name__ == "__main__":
    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)
    unittest.main()
