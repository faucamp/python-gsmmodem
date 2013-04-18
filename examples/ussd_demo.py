#!/usr/bin/env python

"""\
Demo: Simple USSD example

Simple demo app that initiates a USSD session, reads the string response and closes the session
(if it wasn't closed by the network)

Note: for this to work, a valid USSD string for your network must be used.
"""

from __future__ import print_function

import logging

PORT = '/dev/ttyUSB2'
BAUDRATE = 115200
USSD_STRING = '*101#'
PIN = None # SIM card PIN (if any)

from gsmmodem.modem import GsmModem

def main():
    print('Initializing modem...')
    #logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)
    modem = GsmModem(PORT, BAUDRATE)
    modem.connect(PIN)
    modem.waitForNetworkCoverage(10)
    print('Sending USSD string: {0}'.format(USSD_STRING))
    response = modem.sendUssd(USSD_STRING) # response type: gsmmodem.modem.Ussd
    print('USSD reply received: {0}'.format(response.message))
    if response.sessionActive:
        print('Closing USSD session.')
        # At this point, you could also reply to the USSD message by using response.reply()
        response.cancel()
    else:
        print('USSD session was ended by network.')
    modem.close()

if __name__ == '__main__':
    main()
