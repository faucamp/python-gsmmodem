#!/usr/bin/env python

from .serial_comms import SerialComms

class GsmModem(SerialComms):
        
    def __init__(self, port, baudrate=9600, incomingCallCallbackFunc=None, smsReceivedCallbackFunc=None):
        super(GsmModem, self).__init__(port, baudrate, notifyCallbackFunc=self._handleModemNotification)
        self.incomingCallCallback = incomingCallCallbackFunc or self._placeholderCallback
        self.smsReceivedCallback = smsReceivedCallbackFunc or self._placeholderCallback
        
    
    def _handleModemNotification(self, line):
        """ @param line The line that was read """
        print 'GSM Modem class. NOTIFICATION line read:\n"{0}"'.format(line)
    