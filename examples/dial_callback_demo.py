#!/usr/bin/env python

"""\
Demo: dial a number (using callbacks to track call status)

Simple demo app that makes a voice call and plays sone DTMF tones (if supported by modem)
when the call is answered, and hangs up the call.
It uses the dial() methods callback mechanism to be informed when the call is answered and ended.

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

waitForCallback = True

def callStatusCallback(call):
    global waitForCallback
    print('Call status update callback function called')
    if call.answered:
        print('Call has been answered; waiting a while...')
        # Wait for a bit - some older modems struggle to send DTMF tone immediately after answering a call
        time.sleep(3.0)
        print('Playing DTMF tones...')
        try:
            if call.active: # Call could have been ended by remote party while we waited in the time.sleep() call
                call.sendDtmfTone('9515999955951')
        except InterruptedException as e:
            # Call was ended during playback
            print('DTMF playback interrupted: {0} ({1} Error {2})'.format(e, e.cause.type, e.cause.code))
        except CommandError as e:
            print('DTMF playback failed: {0}'.format(e))
        finally:
            if call.active: # Call is still active
                print('Hanging up call...')
                call.hangup()
            waitForCallback = False
    else:
        # Call is no longer active (remote party ended it)
        print('Call has been ended by remote party')
        waitForCallback = False

def main():
    if NUMBER == None or NUMBER == '00000':
        print('Error: Please change the NUMBER variable\'s value before running this example.')
        sys.exit(1)
    print('Initializing modem...')
    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)
    modem = GsmModem(PORT, BAUDRATE)
    modem.connect(PIN)
    print('Waiting for network coverage...')
    modem.waitForNetworkCoverage(30)
    print('Dialing number: {0}'.format(NUMBER))
    call = modem.dial(NUMBER, callStatusUpdateCallbackFunc=callStatusCallback)
    global waitForCallback
    while waitForCallback:
        time.sleep(0.1)
    print('Done')

if __name__ == '__main__':
    main()
