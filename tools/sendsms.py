#!/usr/bin/env python


"""\
Simple script to send an SMS message

@author: Francois Aucamp <francois.aucamp@gmail.com>
"""
from __future__ import print_function
import sys, argparse
try:
    import readline
except ImportError:
    pass

from gsmmodem.modem import GsmModem
from gsmmodem.exceptions import TimeoutException

def main():
    parser = argparse.ArgumentParser(description='Simple script for sending SMS messages')
    parser.add_argument('-p', '--port', metavar='PORT', help='port to which the GSM modem is connected; a number or a device name.')
    parser.add_argument('-b', '--baud', metavar='BAUDRATE', default=9600, help='set baud rate')
    parser.add_argument('-d', '--deliver',  action='store_true', help='wait for SMS delivery report')
    parser.add_argument('destination', metavar='DESTINATION', help='destination mobile number')    
    args = parser.parse_args()

    modem = GsmModem(args.port)
    
    
    print('Connecting to GSM modem on {}...'.format(args.port))            
    modem.connect()
    print('Checking for network coverage...')
    try:
        modem.waitForNetworkCoverage(5)
    except TimeoutException:
        print('Network signal strength is not sufficient, please adjust modem position/antenna and try again.')
        modem.close()
        sys.exit(1)
    else:
        print('\nPlease type your message and press enter to send it:')
        text = raw_input('> ')        
        print('\nSending SMS message...')
        try:
            modem.sendSms(args.destination, text, waitForDelivery=True)
        except TimeoutException:
            print('Failed to send message: the send operation timed out')
            modem.close()
            sys.exit(1)
        else:
            modem.close()
            print('Message sent.')

if __name__ == '__main__':
    main()

