#!/usr/bin/env python

"""\
Demo: dial a number

Simple demo app that makes a voice call and plays sone DTMF tones (if supported by modem)
when the call is answered, and hangs up the call.

Note: you need to modify the NUMBER variable for this to work
"""

from __future__ import print_function

import sys, time, logging

PORT = '/dev/ttyUSB2'
BAUDRATE = 115200
NUMBER = '00000' # Number to dial - CHANGE THIS TO A REAL NUMBER
PIN = None # SIM card PIN (if any)

from gsmmodem.modem import GsmModem
from gsmmodem.exceptions import InterruptedException, CommandError

def main():
    if NUMBER == None or NUMBER == '00000':
        print('Error: Please change the NUMBER variable\'s value before running this example.')
        sys.exit(1)
    print('Initializing modem...')
    #logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)
    modem = GsmModem(PORT, BAUDRATE, incomingCallCallbackFunc=handleIncomingCall)
    modem.connect(PIN)
    print('Waiting for network coverage...')
    modem.waitForNetworkCoverage(30)
    print('Dialing number: {0}'.format(NUMBER))
    call = modem.dial(NUMBER)
    print('Waiting for call to be answered/rejected')
    wasAnswered = False
    while call.active:
        if call.answered:
            wasAnswered = True
            print('Call has been answered. Playing DTMF tones...')
            # Wait for a bit - some older modems struggle to send DTMF tone immediately after answering a call
            time.sleep(2.0)
            try:
                call.sendDtmfTone('9515999955951')
            except InterruptedException as e:
                # Call was ended during playback
                print('DTMF playback interrupted: {0} ({1} Error {2})'.format(e, e.cause.type, e.cause.code))
            except CommandError as e:
                print('DTMF playback failed: {0} ({1} Error {2})'.format(e, e.cause.type, e.cause.code))
            finally:
                if call.active: # Call is still active
                    print('Hanging up call...')
                    call.hangup()
                else: # Call is no longer active (remote party ended it)
                    print('Call has been ended by remote party')
        else:
            # Wait a bit and check again
            time.sleep(0.5)
    if not wasAnswered:
        print('Call was not answered by remote party')
    print('Done.')
    modem.close()

if __name__ == '__main__':
    main()
