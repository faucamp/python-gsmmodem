#!/usr/bin/env python

"""\
Demo: handle incoming calls

Simple demo app that listens for incoming calls, displays the caller ID,
optionally answers the call and plays sone DTMF tones (if supported by modem), 
and hangs up the call.
"""

from __future__ import print_function

PORT = '/dev/ttyUSB2'
BAUDRATE = 9600

from gsmmodem.modem import GsmModem

def handleIncomingCall(call):
    if call.ringCount == 1:
        print('Incoming call from:', call.number)
    elif call.ringCount >= 2:
        if call.dtmfSupport:
            print('Answering call and playing some DTMF tones...')
            call.answer()
            call.sendDtmfTone('9515999955951')
            print('Hanging up call.')
            call.hangup()
        else:            
            print('Modem has no DTMF support - hanging up call.')
        call.hangup()
    else:
        print(' Call from {0} is still ringing...'.format(call.number))
    
def main():
    modem = GsmModem(PORT, BAUDRATE, incomingCallCallbackFunc=handleIncomingCall)
    modem.connect()
    print('Waiting for incoming calls...')    
    modem.rxThread.join(2**31) # Specify a (huge) timeout so that it essentially blocks indefinitely, but still receives CTRL+C interrupt signal

if __name__ == '__main__':
    main()