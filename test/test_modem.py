#!/usr/bin/env python

""" Test suite for gsmmodem.modem """

from __future__ import print_function

import time, unittest, logging
from datetime import datetime

import compat # For Python 2.6 compatibility

import gsmmodem.serial_comms
import gsmmodem.modem
import gsmmodem.pdu
from gsmmodem.util import SimpleOffsetTzInfo

import fakemodems

# The fake modem to use (if any)
FAKE_MODEM = None

class MockSerialPackage(object):
    """ Fake serial package for the GsmModem/SerialComms classes to import during tests """
    
    class Serial():
        
        _REPONSE_TIME = 0.02
        
        """ Mock serial object for use by the GsmModem class during tests """
        def __init__(self, *args, **kwargs):
            # The default value to read/"return" if responseSequence isn't set up, or None for nothing
            self.defaultResponse = 'OK\r\n'
            self.responseSequence = []
            self.flushResponseSequence = True
            self.writeQueue = []
            self._alive = True
            self._readQueue = []
            self.writeCallbackFunc = None
            global FAKE_MODEM
            # Pre-determined responses to specific commands - used for imitating specific modems
            if FAKE_MODEM != None:
                self.responses = FAKE_MODEM.responses
            else:
                self.responses = {'AT+CPMS=?\r': ['+CPMS: ("ME","MT","SM","SR"),("ME","MT","SM","SR"),("ME","MT","SM","SR")\r\n', 'OK\r\n'],
                                  'AT+CFUN?\r': ['+CFUN: 1\r\n', 'OK\r\n'],
                                  'AT+WIND?\r': ['ERROR\r\n']} 
        
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
                elif command in self.responses:
                    self.responseSequence = self.responses[command]
                    if len(self.responseSequence) > 0:
                        self._setupReadValue(command)
                elif self.defaultResponse != None:
                    self._readQueue = list(self.defaultResponse)
                
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
                 ('*120*500#', 'AT+CUSD=1,"*120*500#",15\r', '+CUSD: 1,"Hallo daar",15\r\n', 'Hallo daar', True),
                 ('*130*111#', 'AT+CUSD=1,"*130*111#",15\r', '+CUSD: 2,"Totsiens",15\r\n', 'Totsiens', False),
                 ('*111*502#', 'AT+CUSD=1,"*111*502#",15\r', '+CUSD: 2,"You have the following remaining balances:\n0 free minutes\n20 MORE Weekend minutes ",15\r\n', 'You have the following remaining balances:\n0 free minutes\n20 MORE Weekend minutes ', False)]
                
        for test in tests:            
            def writeCallbackFunc(data):                
                self.assertEqual(test[1], data, 'Invalid data written to modem; expected "{0}", got: "{1}"'.format(test[1], data))                            
            self.modem.serial.responseSequence = ['OK\r\n', 0.3, test[2]]            
            self.modem.serial.writeCallbackFunc = writeCallbackFunc
            ussd = self.modem.sendUssd(test[0])
            self.assertIsInstance(ussd, gsmmodem.modem.Ussd)
            self.assertEqual(ussd.sessionActive, test[4], 'Session state is invalid for test case: {0}'.format(test))
            self.assertEqual(ussd.message, test[3])
            if ussd.sessionActive:
                def writeCallbackFunc2(data):
                    self.assertEqual('AT+CUSD=2\r', data, 'Invalid data written to modem; expected "AT+CUSD=2", got: "{0}"'.format(data))                    
                self.modem.serial.writeCallbackFunc = writeCallbackFunc2                
                ussd.cancel()
            else:
                ussd.cancel() # This call shouldn't do anything
            del ussd
        
    def test_manufacturer(self):
        def writeCallbackFunc(data):
            self.assertEqual('AT+CGMI\r', data, 'Invalid data written to modem; expected "{0}", got: "{1}"'.format('AT+CGMI\r', data))
        self.modem.serial.writeCallbackFunc = writeCallbackFunc
        tests = ['huawei', 'ABCDefgh1235', 'Some Random Manufacturer']
        for test in tests:
            self.modem.serial.responseSequence = ['{0}\r\n'.format(test), 'OK\r\n']            
            self.assertEqual(test, self.modem.manufacturer)
    
    def test_model(self):
        def writeCallbackFunc(data):
            self.assertEqual('AT+CGMM\r', data, 'Invalid data written to modem; expected "{0}", got: "{1}"'.format('AT+CGMM\r', data))
        self.modem.serial.writeCallbackFunc = writeCallbackFunc
        tests = ['K3715', '1324-Qwerty', 'Some Random Model']
        for test in tests:
            self.modem.serial.responseSequence = ['{0}\r\n'.format(test), 'OK\r\n']            
            self.assertEqual(test, self.modem.model)
            
    def test_revision(self):
        def writeCallbackFunc(data):
            self.assertEqual('AT+CGMR\r', data, 'Invalid data written to modem; expected "{0}", got: "{1}"'.format('AT+CGMR\r', data))
        self.modem.serial.writeCallbackFunc = writeCallbackFunc
        tests = ['1', '1324-56768-23414', 'r987']
        for test in tests:
            self.modem.serial.responseSequence = ['{0}\r\n'.format(test), 'OK\r\n']
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
            self.assertEqual(test, self.modem.imei)
            
    def test_imsi(self):
        def writeCallbackFunc(data):
            self.assertEqual('AT+CIMI\r', data, 'Invalid data written to modem; expected "{0}", got: "{1}"'.format('AT+CIMI\r', data))
        self.modem.serial.writeCallbackFunc = writeCallbackFunc
        tests = ['987654321012345']
        for test in tests:
            self.modem.serial.responseSequence = ['{0}\r\n'.format(test), 'OK\r\n']
            self.assertEqual(test, self.modem.imsi)
    
    def test_supportedCommands(self):
        def writeCallbackFunc(data):
            self.assertEqual('AT+CLAC\r', data, 'Invalid data written to modem; expected "{0}", got: "{1}"'.format('AT+CLAC\r', data))
        self.modem.serial.writeCallbackFunc = writeCallbackFunc
        tests = (('&C,D,E,\S,+CGMM,^DTMF', ['&C', 'D', 'E', '\S', '+CGMM', '^DTMF']),
                 ('Z', ['Z']))
        for test in tests:
            self.modem.serial.responseSequence = ['+CLAC:{0}\r\n'.format(test[0]), 'OK\r\n']            
            commands = self.modem.supportedCommands
            self.assertListEqual(commands, test[1])
        # Fake a modem that does not support this command
        self.modem.serial.defaultResponse = 'ERROR\r\n'
        commands = self.modem.supportedCommands
        self.assertEqual(commands, None)


class TestGsmModemDial(unittest.TestCase):
    
    def tearDown(self):
        global FAKE_MODEM
        FAKE_MODEM = None
    
    def init_modem(self, modem):
        global FAKE_MODEM
        FAKE_MODEM = modem
        self.mockSerial = MockSerialPackage()
        gsmmodem.serial_comms.serial = self.mockSerial        
        self.modem = gsmmodem.modem.GsmModem('-- PORT IGNORED DURING TESTS --')
        self.modem.connect()
    
    def test_dial(self):
        
        tests = (['0123456789', '1', '0'],)
        
        global MODEMS
        for modem in fakemodems.createModems():
            print('Modem:', modem)
            self.init_modem(modem)
            
            for number, callId, callType in tests:                
                def writeCallbackFunc(data):
                    self.assertEqual('ATD{0};\r'.format(number), data, 'Invalid data written to modem; expected "{0}", got: "{1}". Modem: {2}'.format('ATD{0};\r'.format(number), data, modem))
                self.modem.serial.writeCallbackFunc = writeCallbackFunc                
                self.modem.serial.responseSequence = modem.getAtdResponse(number)
                self.modem.serial.responseSequence.extend(modem.getPreCallInitWaitSequence())
                # Fake call initiated notification
                self.modem.serial.responseSequence.extend(modem.getCallInitNotification(callId, callType))
                call = self.modem.dial(number)
                # Wait for the read buffer to clear
                while len(self.modem.serial._readQueue) > 0 or len(self.modem.serial.responseSequence) > 0:
                    time.sleep(0.05)                
                # Check status
                self.assertIsInstance(call, gsmmodem.modem.Call)
                self.assertIs(call.number, number)
                self.assertFalse(call.answered, 'Call state invalid: should not yet be answered. Modem: {0}'.format(modem))            
                self.assertIn(call.id, self.modem.activeCalls)
                self.assertEqual(len(self.modem.activeCalls), 1)
                # Fake an answer                
                self.modem.serial.responseSequence = modem.getRemoteAnsweredNotification(callId, callType)
                # Wait a bit for the event to be picked up
                while len(self.modem.serial._readQueue) > 0 or len(self.modem.serial.responseSequence) > 0:                    
                    time.sleep(0.05)                
                self.assertTrue(call.answered, 'Remote call answer was not detected. Modem: {0}'.format(modem))
                def hangupCallback(data):
                    self.assertEqual('ATH\r'.format(number), data, 'Invalid data written to modem; expected "{0}", got: "{1}". Modem: {2}'.format('ATH\r'.format(number), data, modem))
                self.modem.serial.writeCallbackFunc = hangupCallback
                call.hangup()
                self.assertFalse(call.answered, 'Hangup call did not change call state. Modem: {0}'.format(modem))
                self.assertNotIn(call.id, self.modem.activeCalls)
                self.assertEqual(len(self.modem.activeCalls), 0)
                # Check remote hangup detection
                self.modem.serial.writeCallbackFunc = writeCallbackFunc
                self.modem.serial.responseSequence = modem.getAtdResponse(number)
                self.modem.serial.responseSequence.extend(modem.getPreCallInitWaitSequence())
                # Fake call initiated notification
                self.modem.serial.responseSequence.extend(modem.getCallInitNotification(callId, callType))                
                call = self.modem.dial(number)
                # Wait a bit for the event to be picked up
                while len(self.modem.serial._readQueue) > 0 or len(self.modem.serial.responseSequence) > 0:
                    time.sleep(0.05)
                # Fake remote answer
                self.modem.serial.responseSequence = modem.getRemoteAnsweredNotification(callId, callType)                
                while len(self.modem.serial._readQueue) > 0 or len(self.modem.serial.responseSequence) > 0:
                    time.sleep(0.05)
                self.assertTrue(call.answered, 'Remote call answer was not detected. Modem: {0}'.format(modem))
                self.assertIn(call.id, self.modem.activeCalls)
                self.assertEqual(len(self.modem.activeCalls), 1)
                # Now fake a remote hangup
                self.modem.serial.responseSequence = modem.getRemoteHangupNotification(callId, callType)
                # Wait a bit for the event to be picked up
                while len(self.modem.serial._readQueue) > 0 or len(self.modem.serial.responseSequence) > 0:
                    time.sleep(0.05)
                self.assertFalse(call.answered, 'Remote hangup was not detected. Modem: {0}'.format(modem))
                self.assertNotIn(call.id, self.modem.activeCalls)
                self.assertEqual(len(self.modem.activeCalls), 0)
            self.modem.close()


class TestIncomingCall(unittest.TestCase):
    
    def tearDown(self):
        global FAKE_MODEM
        FAKE_MODEM = None
    
    def init_modem(self, modem, incomingCallCallbackFunc):
        global FAKE_MODEM
        FAKE_MODEM = modem
        self.mockSerial = MockSerialPackage()
        gsmmodem.serial_comms.serial = self.mockSerial        
        self.modem = gsmmodem.modem.GsmModem('-- PORT IGNORED DURING TESTS --', incomingCallCallbackFunc=incomingCallCallbackFunc)
        self.modem.connect()
    
    def test_incomingCallAnswer(self):
        
        for modem in fakemodems.createModems():
            print('Modem:', modem)
            
            callReceived = [False, 'VOICE', '']
            def incomingCallCallbackFunc(call):
                try:                    
                    self.assertIsInstance(call, gsmmodem.modem.IncomingCall)
                    self.assertIn(call.id, self.modem.activeCalls)
                    self.assertEqual(len(self.modem.activeCalls), 1)
                    self.assertEqual(call.number, callReceived[2], 'Caller ID (caller number) incorrect. Expected: "{0}", got: "{1}". Modem: {2}'.format(callReceived[2], call.number, modem))
                    self.assertFalse(call.answered, 'Call state invalid: should not yet be answered. Modem: {0}'.format(modem))
                    self.assertIsInstance(call.type, int)
                    self.assertEqual(call.type, callReceived[1], 'Invalid call type; expected "{0}", got "{1}". Modem: {2}'.format(callReceived[1], call.type, modem))
                    def writeCallbackFunc1(data):
                        self.assertEqual('ATA\r', data, 'Invalid data written to modem; expected "{0}", got: "{1}". Modem: {2}'.format('ATA\r', data, modem))
                    self.modem.serial.writeCallbackFunc = writeCallbackFunc1
                    call.answer()
                    self.assertTrue(call.answered, 'Call state invalid: should be answered. Modem: {0}'.format(modem))
                    def writeCallbackFunc2(data):
                        self.assertEqual('ATH\r', data, 'Invalid data written to modem; expected "{0}", got: "{1}". Modem: {2}'.format('ATH\r', data, modem))
                    self.modem.serial.writeCallbackFunc = writeCallbackFunc2
                    call.hangup()
                    self.assertFalse(call.answered, 'Call state invalid: hangup did not change call state. Modem: {0}'.format(modem))
                    self.assertNotIn(call.id, self.modem.activeCalls)
                    self.assertEqual(len(self.modem.activeCalls), 0)
                finally:
                    callReceived[0] = True
        
            self.init_modem(modem, incomingCallCallbackFunc)
        
            tests = (('+27820001234', 'VOICE', 0),)
        
            for number, cringParam, callType in tests:
                callReceived[0] = False
                callReceived[1] = callType
                callReceived[2] = number
                # Fake incoming voice call                
                self.modem.serial.responseSequence = modem.getIncomingCallNotification(number, cringParam)
                # Wait for the handler function to finish
                while callReceived[0] == False:
                    time.sleep(0.1)
            self.modem.close()


class TestSms(unittest.TestCase):
    """ Tests the SMS API of GsmModem class """
    
    def setUp(self):
        self.tests = (('+0123456789', 'Hello world!',                        
                       1,
                       datetime(2013, 3, 8, 15, 02, 16, tzinfo=SimpleOffsetTzInfo(2)),
                       '+2782913593',
                       '06917228195339040A9110325476980000313080512061800CC8329BFD06DDDF72363904', 29),
                      ('+9876543210', 
                       'Hallo\nhoe gaan dit?', 
                       4,
                       datetime(2013, 3, 8, 15, 02, 16, tzinfo=SimpleOffsetTzInfo(2)),
                       '+2782913593',
                       '06917228195339040A91896745230100003130805120618013C8309BFD56A0DF65D0391C7683C869FA0F', 35)
                      )
    
    
    def initModem(self, smsReceivedCallbackFunc):
        # Override the pyserial import        
        self.mockSerial = MockSerialPackage()
        gsmmodem.serial_comms.serial = self.mockSerial
        self.modem = gsmmodem.modem.GsmModem('-- PORT IGNORED DURING TESTS --', smsReceivedCallbackFunc=smsReceivedCallbackFunc)        
        self.modem.connect()

    def Xtest_sendSmsTextMode(self):
        """ Tests sending SMS messages in text mode """
        self.initModem(None)
        self.modem.smsTextMode = True # Set modem to text mode
        for number, message, index, smsTime, smsc, pdu, tpdu_length in self.tests:
            def writeCallbackFunc(data):
                def writeCallbackFunc2(data):
                    self.assertEqual('{0}{1}'.format(message, chr(26)), data, 'Invalid data written to modem; expected "{0}", got: "{1}"'.format('{0}{1}'.format(message, chr(26)), data))                
                self.assertEqual('AT+CMGS="{0}"\r'.format(number), data, 'Invalid data written to modem; expected "{0}", got: "{1}"'.format('AT+CMGS="{0}"'.format(number), data))
                self.modem.serial.writeCallbackFunc = writeCallbackFunc2
            self.modem.serial.writeCallbackFunc = writeCallbackFunc
            self.modem.sendSms(number, message)        
        self.modem.close()
        
    def Xtest_sendSmsPduMode(self):
        """ Tests sending a SMS messages in PDU mode """
        self.initModem(None)
        self.modem.smsTextMode = False # Set modem to PDU mode        
        for number, message, index, smsTime, smsc, pdu, sms_deliver_tpdu_length in self.tests:
            calcPdu, tpdu_length = gsmmodem.pdu.encodeSmsSubmitPdu(number, message)
            pduHex = str(calcPdu).encode('hex').upper()
            def writeCallbackFunc(data):
                def writeCallbackFunc2(data):
                    self.assertEqual('{0}{1}'.format(pduHex, chr(26)), data, 'Invalid data written to modem; expected "{0}", got: "{1}"'.format('{0}{1}'.format(pduHex, chr(26)), data))                
                self.assertEqual('AT+CMGS={0}\r'.format(tpdu_length), data, 'Invalid data written to modem; expected "{0}", got: "{1}"'.format('AT+CMGS={0}'.format(tpdu_length), data))
                self.modem.serial.writeCallbackFunc = writeCallbackFunc2
            self.modem.serial.writeCallbackFunc = writeCallbackFunc
            sms = self.modem.sendSms(number, message)
            self.assertIsInstance(sms, gsmmodem.modem.SentSms)
            self.assertEqual(sms.number, number, 'Sent SMS has invalid number. Expected "{0}", got "{1}"'.format(number, sms.number))
            self.assertEqual(sms.text, message, 'Sent SMS has invalid text. Expected "{0}", got "{1}"'.format(message, sms.text))
        self.modem.close()
    
    def Xtest_receiveSmsTextMode(self):
        """ Tests receiving SMS messages in text mode """
        callbackInfo = [False, '', '', -1, None, '']
        def smsReceivedCallbackFuncText(sms):
            try:
                self.assertIsInstance(sms, gsmmodem.modem.ReceivedSms)
                self.assertEqual(sms.number, callbackInfo[1], 'SMS sender number incorrect. Expected: "{0}", got: "{1}"'.format(callbackInfo[1], sms.number))
                self.assertEqual(sms.text, callbackInfo[2], 'SMS text incorrect. Expected: "{0}", got: "{1}"'.format(callbackInfo[2], sms.text))
                self.assertIsInstance(sms.time, datetime, 'SMS received time type invalid. Expected: datetime.datetime, got: {0}"'.format(type(sms.time)))
                self.assertEqual(sms.time, callbackInfo[4], 'SMS received time incorrect. Expected: "{0}", got: "{1}"'.format(callbackInfo[4], sms.time))
                self.assertEqual(sms.status, gsmmodem.modem.Sms.STATUS_RECEIVED_UNREAD)
                self.assertEqual(sms.smsc, None, 'Text-mode SMS should not have any SMSC information')
            finally:
                callbackInfo[0] = True

        self.initModem(smsReceivedCallbackFunc=smsReceivedCallbackFuncText)
        self.modem.smsTextMode = True # Set modem to text mode
        for number, message, index, smsTime, smsc, pdu, tpdu_length in self.tests:            
            # Wait for the handler function to finish
            callbackInfo[0] = False # "done" flag
            callbackInfo[1] = number
            callbackInfo[2] = message
            callbackInfo[3] = index
            callbackInfo[4] = smsTime            
            
            # Time string as returned by modem in text modem
            textModeStr = smsTime.strftime('%y/%m/%d,%H:%M:%S%z')[:-2]
            def writeCallbackFunc(data):
                """ Intercept the "read stored message" command """
                self.assertEqual('AT+CMGR={0}\r'.format(index), data, 'Invalid data written to modem; expected "{0}", got: "{1}"'.format('AT+CMGR={0}'.format(index), data))
                self.modem.serial.responseSequence = ['+CMGR: "REC UNREAD","{0}",,"{1}"\r\n'.format(number, textModeStr), '{0}\r\n'.format(message), 'OK\r\n']
                def writeCallbackFunc2(data):
                    self.assertEqual('AT+CMGD={0}\r'.format(index), data, 'Invalid data written to modem; expected "{0}", got: "{1}"'.format('AT+CMGD={0}'.format(index), data))
                self.modem.serial.writeCallbackFunc = writeCallbackFunc2
            self.modem.serial.writeCallbackFunc = writeCallbackFunc
            # Fake a "new message" notification
            self.modem.serial.responseSequence = ['+CMTI: "SM",{0}\r\n'.format(index)]
            # Wait for the handler function to finish
            while callbackInfo[0] == False:
                time.sleep(0.1)
        self.modem.close()
        
    def test_receiveSmsPduMode(self):
        """ Tests receiving SMS messages in PDU mode """
        callbackInfo = [False, '', '', -1, None, '']
        def smsReceivedCallbackFuncPdu(sms):
            try:
                self.assertIsInstance(sms, gsmmodem.modem.ReceivedSms)
                self.assertEqual(sms.number, callbackInfo[1], 'SMS sender number incorrect. Expected: "{0}", got: "{1}"'.format(callbackInfo[1], sms.number))
                self.assertEqual(sms.text, callbackInfo[2], 'SMS text incorrect. Expected: "{0}", got: "{1}"'.format(callbackInfo[2], sms.text))
                self.assertIsInstance(sms.time, datetime, 'SMS received time type invalid. Expected: datetime.datetime, got: {0}"'.format(type(sms.time)))
                self.assertEqual(sms.time, callbackInfo[4], 'SMS received time incorrect. Expected: "{0}", got: "{1}"'.format(callbackInfo[4], sms.time))
                self.assertEqual(sms.status, gsmmodem.modem.Sms.STATUS_RECEIVED_UNREAD)
                self.assertEqual(sms.smsc, callbackInfo[5], 'PDU-mode SMS SMSC number incorrect. Expected: "{0}", got: "{1}"'.format(callbackInfo[5], sms.smsc))
            finally:
                callbackInfo[0] = True

        self.initModem(smsReceivedCallbackFunc=smsReceivedCallbackFuncPdu)
        self.modem.smsTextMode = False # Set modem to PDU mode
        for number, message, index, smsTime, smsc, pdu, tpdu_length in self.tests:            
            # Wait for the handler function to finish
            callbackInfo[0] = False # "done" flag
            callbackInfo[1] = number
            callbackInfo[2] = message
            callbackInfo[3] = index
            callbackInfo[4] = smsTime
            callbackInfo[5] = smsc
            
            def writeCallbackFunc(data):
                """ Intercept the "read stored message" command """
                self.assertEqual('AT+CMGR={0}\r'.format(index), data, 'Invalid data written to modem; expected "{0}", got: "{1}"'.format('AT+CMGR={0}'.format(index), data))
                self.modem.serial.responseSequence = ['+CMGR: 0,,{0}\r\n'.format(tpdu_length), '{0}\r\n'.format(pdu), 'OK\r\n']                
                def writeCallbackFunc2(data):
                    self.assertEqual('AT+CMGD={0}\r'.format(index), data, 'Invalid data written to modem; expected "{0}", got: "{1}"'.format('AT+CMGD={0}'.format(index), data))
                self.modem.serial.writeCallbackFunc = writeCallbackFunc2
            self.modem.serial.writeCallbackFunc = writeCallbackFunc
            # Fake a "new message" notification
            self.modem.serial.responseSequence = ['+CMTI: "SM",{0}\r\n'.format(index)]
            # Wait for the handler function to finish
            while callbackInfo[0] == False:
                time.sleep(0.1)
        self.modem.close()


if __name__ == "__main__":
    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)
    unittest.main()
