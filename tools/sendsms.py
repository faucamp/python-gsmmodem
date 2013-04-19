#!/usr/bin/env python


"""\
Simple script to send an SMS message

@author: Francois Aucamp <francois.aucamp@gmail.com>
"""
from __future__ import print_function
import sys, logging

from gsmmodem.modem import GsmModem, SentSms
from gsmmodem.exceptions import TimeoutException, PinRequiredError, IncorrectPinError

def parseArgs():
    """ Argument parser for Python 2.7 and above """
    from argparse import ArgumentParser
    parser = ArgumentParser(description='Simple script for sending SMS messages')
    parser.add_argument('-i', '--port', metavar='PORT', help='port to which the GSM modem is connected; a number or a device name.')
    parser.add_argument('-b', '--baud', metavar='BAUDRATE', default=115200, help='set baud rate')
    parser.add_argument('-p', '--pin', metavar='PIN', default=None, help='SIM card PIN')
    parser.add_argument('-d', '--deliver',  action='store_true', help='wait for SMS delivery report')
    parser.add_argument('destination', metavar='DESTINATION', help='destination mobile number')    
    return parser.parse_args()
    
def parseArgsPy26():
    """ Argument parser for Python 2.6 """
    from gsmtermlib.posoptparse import PosOptionParser, Option
    parser = PosOptionParser(description='Simple script for sending SMS messages')
    parser.add_option('-i', '--port', metavar='PORT', help='port to which the GSM modem is connected; a number or a device name.')
    parser.add_option('-b', '--baud', metavar='BAUDRATE', default=115200, help='set baud rate')
    parser.add_option('-p', '--pin', metavar='PIN', default=None, help='SIM card PIN')
    parser.add_option('-d', '--deliver',  action='store_true', help='wait for SMS delivery report')
    parser.add_positional_argument(Option('--destination', metavar='DESTINATION', help='destination mobile number'))    
    options, args = parser.parse_args()
    if len(args) != 1:    
        parser.error('Incorrect number of arguments - please specify a DESTINATION to send to, e.g. {0} 012789456'.format(sys.argv[0]))
    else:
        options.destination = args[0]
        return options

def main():
    args = parseArgsPy26() if sys.version_info[0] == 2 and sys.version_info[1] < 7 else parseArgs()
    if args.port == None:
        sys.stderr.write('Error: No port specified. Please specify the port to which the GSM modem is connected using the -i argument.\n')
        sys.exit(1)
    modem = GsmModem(args.port, args.baud)    
    # Uncomment the following line to see what the modem is doing:
    #logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)
    
    print('Connecting to GSM modem on {0}...'.format(args.port))
    try:
        modem.connect(args.pin)
    except PinRequiredError:
        sys.stderr.write('Error: SIM card PIN required. Please specify a PIN with the -p argument.\n')
        sys.exit(1)
    except IncorrectPinError:
        sys.stderr.write('Error: Incorrect SIM card PIN entered.\n')
        sys.exit(1)
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
        if args.deliver:
            print ('\nSending SMS and waiting for delivery report...')
        else:
            print('\nSending SMS message...')
        try:
            sms = modem.sendSms(args.destination, text, waitForDeliveryReport=args.deliver)
        except TimeoutException:
            print('Failed to send message: the send operation timed out')
            modem.close()
            sys.exit(1)
        else:
            modem.close()
            if sms.report:
                print('Message sent{0}'.format(' and delivered OK.' if sms.status == SentSms.DELIVERED else ', but delivery failed.'))
            else:
                print('Message sent.')

if __name__ == '__main__':
    main()

