#!/usr/bin/env python

import sys, threading
from Queue import Queue

import re
import serial # pyserial: http://pyserial.sourceforge.net

from .exceptions import TimeoutException


class SerialComms(object):
    """ Wraps all low-level serial communications (actual read/write operations)     
    """
    
    # End-of-line read terminator
    RX_EOL_SEQ = '\r\n'
    # End-of-response terminator
    RESPONSE_TERM = re.compile(r'^OK|ERROR|(\+CM[ES] ERROR: \d+)$')
    # Default timeout for serial port reads (in seconds)
    timeout = 1
        
    def __init__(self, port, baudrate=9600, notifyCallbackFunc=None, *args, **kwargs):        
        self.alive = False
        self.port = port
        self.baudrate = 9600
        
        self._responseEvent = None # threading.Event()
        self._expectResponseTermSeq = None # expected response terminator sequence
        self._response = None # Buffer containing response to a written command
        self._notification = [] # Buffer containing lines from an unsolicited notification from the modem
        # Reentrant lock for managing concurrent write access to the underlying serial port
        self._txLock = threading.RLock()
        
        self.notifyCallback = notifyCallbackFunc or self._placeholderCallback        
        
    def connect(self):
        """ Connects to the device and starts the read thread """                
        self.serial = serial.Serial(port=self.port, baudrate=self.baudrate, timeout=self.timeout)
        # Start read thread
        self.alive = True 
        self.rxThread = threading.Thread(target=self._readLoop)
        self.rxThread.daemon = True
        self.rxThread.start()

    def close(self, join=False):
        """ Stops the read thread, waits for it to exit cleanly, then closes the underlying serial port """        
        self.alive = False
        self.rxThread.join()
        self.serial.close()
        
    def _handleLineRead(self, line, checkForResponseTerm=True):
        #print 'sc.hlineread:',line
        if self._responseEvent and not self._responseEvent.is_set():
            # A response event has been set up (another thread is waiting for this response)
            #print ' sc: response to event: "{0}", length: {1}'.format(line, len(line))
            self._response.append(line)
            if not checkForResponseTerm or self.RESPONSE_TERM.match(line):
                # End of response reached; notify waiting thread
                self._responseEvent.set()
        else:
            # Nothing was waiting for this - treat it as a notificaiton
            self._notification.append(line)
            if self.serial.inWaiting() == 0:
                # No more chars on the way for this notification - notify highler-level callback
                self.notifyCallback(self._notification)
                self._notification = []            

    def _placeholderCallback(self, *args, **kwargs):
        """ Placeholder callback function (does nothing) """
        
    def _readLoop(self):
        """ Read thread main loop
        
        Reads lines from the connected device
        """
        try:
            readTermSeq = list(self.RX_EOL_SEQ)
            readTermLen = len(readTermSeq)
            rxBuffer = []
            while self.alive:
                #print '...going to read'         
                data = self.serial.read(1)                
                if data != '': # check for timeout
                    #print ' RX:',data,'({})'.format(ord(data))
                    rxBuffer.append(data)
                    if rxBuffer[-readTermLen:] == readTermSeq:                        
                        # A line (or other logical segment) has been read
                        line = ''.join(rxBuffer[:-readTermLen])
                        rxBuffer = []
                        if len(line) > 0:                          
                            #print 'calling handler'                      
                            self._handleLineRead(line)
                    elif self._expectResponseTermSeq:
                        if rxBuffer[-len(self._expectResponseTermSeq):] == self._expectResponseTermSeq:
                            line = ''.join(rxBuffer) 
                            rxBuffer = []
                            self._handleLineRead(line, checkForResponseTerm=False)                                                
            #else:
                #' <RX timeout>'
        except serial.SerialException, e:
            self.alive = False
            raise        
        
    def write(self, data, waitForResponse=True, timeout=5, expectedResponseTermSeq=None):
        with self._txLock:
            self.serial.write(data)
            if waitForResponse:
                if expectedResponseTermSeq:
                    self._expectResponseTermSeq = list(expectedResponseTermSeq) 
                self._response = []
                self._responseEvent = threading.Event()
                if self._responseEvent.wait(timeout):
                    self._responseEvent = None
                    self._expectResponseTermSeq = False
                    return self._response
                else: # Response timed out
                    self._responseEvent = None
                    self._expectResponseTermSeq = False
                    raise TimeoutException()
