#!/usr/bin/env python

""" python-gsmmodem installation script """

from distutils.core import setup

setup(name='python-gsmmodem',
      version='0.1',
      description='Control an attached GSM modem: send/receive SMS messages, handle calls, etc',      
      license='LGPLv3+',
      author='Francois Aucamp',
      author_email='francois.aucamp@gmail.com',
      
      url='https://github.com/faucamp/python-gsmmodem',
      download_url='https://github.com/faucamp/python-gsmmodem/archive/master.zip',
      
      long_description="""\
python-gsmmodem is a module that allows easy control of a GSM modem attached
to the system. It also includes a couple of useful commandline utilities for
interacting with a GSM modem.

Its features include:
- simple methods for sending SMS messages, checking signal level, etc
- handling incoming phone calls and received SMS messages via callback methods
- wraps AT command errors into Python exceptions by default
- modular design; you easily issue your own AT commands to the modem with error
  (with error checking), or read/write directly from/to the modem if you prefer

Bundled utilities:
- GSMTerm: an easy-to-use serial terminal for communicating with an attached GSM
  modem. It features command completion, built-in help for many AT commands,
  history, context-aware prompt, etc.
- sensms.py: a simple command line script to send SMS messages
""",

      classifiers=['Development Status :: 4 - Beta',
                   'Environment :: Console',          
                   'Intended Audience :: Developers',
                   'Intended Audience :: Telecommunications Industry',
                   'License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)',
                   'Operating System :: OS Independent',
                   'Programming Language :: Python :: 2.7',
                   'Programming Language :: Python :: 3',
                   'Topic :: Communications :: Telephony',
                   'Topic :: Home Automation',
                   'Topic :: Software Development :: Libraries :: Python Modules',
                   'Topic :: System :: Hardware',
                   'Topic :: Terminals :: Serial',
                   'Topic :: Utilities'],
      keywords = ['gsm', 'sms', 'modem', 'mobile', 'phone', 'usb', 'serial'],
      
      packages=['gsmmodem', 'gsmterm'],      
      package_dir = {'gsmterm': 'tools/gsmterm'},
      scripts=['tools/gsmterm.py', 'tools/sendsms.py'])