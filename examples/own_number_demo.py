#!/usr/bin/env python

"""\
Demo: read own phone number
"""

from __future__ import print_function

import logging

PORT = '/dev/vmodem0'
BAUDRATE = 115200
PIN = None # SIM card PIN (if any)

from gsmmodem.modem import GsmModem

def main():
    print('Initializing modem...')
    # Uncomment the following line to see what the modem is doing:
    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)
    modem = GsmModem(PORT, BAUDRATE)
    modem.connect(PIN)

    number = modem.ownNumber
    print("The SIM card phone number is:")
    print(number)

    # Uncomment the following block to change your own number.
    # modem.ownNumber = "+000123456789" # lease empty for removing the phone entry altogether

    # number = modem.ownNumber
    # print("A new phone number is:")
    # print(number)

    # modem.close();

if __name__ == '__main__':
    main()
