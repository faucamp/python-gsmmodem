#!/usr/bin/env python


"""\
Simple script to assist with identifying a GSM modem
The debug information obtained by this script (when using -d) can be used
to aid test cases (since I don't have access to every modem in the world ;-) )

@author: Francois Aucamp <francois.aucamp@gmail.com>
"""
from __future__ import print_function
import sys

from gsmmodem.modem import GsmModem
from gsmmodem.exceptions import TimeoutException

def parseArgs():
    """ Argument parser for Python 2.7 and above """
    from argparse import ArgumentParser
    parser = ArgumentParser(description='Identify and debug attached GSM modem')    
    parser.add_argument('port', metavar='PORT', help='port to which the GSM modem is connected; a number or a device name.')
    parser.add_argument('-b', '--baud', metavar='BAUDRATE', default=115200, help='set baud rate')
    parser.add_argument('-d', '--debug',  action='store_true', help='dump modem debug information (for python-gsmmodem development)')    
    return parser.parse_args()

def parseArgsPy26():
    """ Argument parser for Python 2.6 """
    from gsmtermlib.posoptparse import PosOptionParser, Option    
    parser = PosOptionParser(description='Identify and debug attached GSM modem')        
    parser.add_positional_argument(Option('--port', metavar='PORT', help='port to which the GSM modem is connected; a number or a device name.'))
    parser.add_option('-b', '--baud', metavar='BAUDRATE', default=115200, help='set baud rate')
    parser.add_option('-d', '--debug',  action='store_true', help='dump modem debug information (for python-gsmmodem development)')    
    options, args = parser.parse_args()
    if len(args) != 1:    
        parser.error('Incorrect number of arguments - please specify a PORT to connect to, e.g. {0} /dev/ttyUSB0'.format(sys.argv[0]))
    else:
        options.port = args[0]
        return options

def main():
    args = parseArgsPy26() if sys.version_info[0] == 2 and sys.version_info[1] < 7 else parseArgs()
    modem = GsmModem(args.port)    
    
    print('Connecting to GSM modem on {0}...'.format(args.port))            
    modem.connect()
    if args.debug:
        pass
    else:
        # Print basic info
        print('\n== MODEM INFORMATION ==\n')
        print('Manufacturer:', modem.manufacturer)
        print('Model:', modem.model)
        print('Revision:', modem.revision if modem.revision != None else 'N/A')
        print('\nIMEI:', modem.imei if modem.imei != None else 'N/A')
        print('IMSI:', modem.imsi if modem.imsi != None else 'N/A')
        print('\nNetwork:', modem.networkName)
        print('\nSignal strength:', modem.signalStrength)

if __name__ == '__main__':
    main()

