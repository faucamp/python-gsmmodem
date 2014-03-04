#!/usr/bin/env python

""" python-gsmmodem installation script """

import sys
from distutils.core import Command
try:
    from setuptools import setup    
except ImportError:   
    from distutils.core import setup    

with open('requirements.txt') as f:
    requires = f.readlines() 
if sys.version_info[0] == 2 and sys.version_info[1] <= 6:
    tests_require = ['unittest2']
    test_command = ['unit2', 'discover']
    coverage_command = ['coverage', 'run', '-m', 'unittest2', 'discover']
else:
    tests_require = []
    test_command = [sys.executable, '-m', 'unittest', 'discover']
    coverage_command = ['coverage', 'run', '-m', 'unittest', 'discover']

VERSION = 0.9

class RunUnitTests(Command):
    """ run unit tests """
    
    user_options = []
    description = __doc__[1:]

    def initialize_options(self):
        pass
    
    def finalize_options(self):
        pass
        
    def run(self):
        import subprocess
        errno = subprocess.call(test_command)
        raise SystemExit(errno)
    
class RunUnitTestsCoverage(Command):
    """ run unit tests and report on code coverage using the 'coverage' tool """
    
    user_options = []
    description = __doc__[1:]

    def initialize_options(self):
        pass
    
    def finalize_options(self):
        pass
        
    def run(self):
        import subprocess
        errno = subprocess.call(coverage_command)
        if errno == 0:
            subprocess.call(['coverage', 'report'])
        raise SystemExit(errno)

setup(name='python-gsmmodem',
      version='{0}'.format(VERSION),
      description='Control an attached GSM modem: send/receive SMS messages, handle calls, etc',      
      license='LGPLv3+',
      author='Francois Aucamp',
      author_email='francois.aucamp@gmail.com',
      
      url='https://github.com/faucamp/python-gsmmodem',
      download_url='https://github.com/faucamp/python-gsmmodem/archive/{0}.tar.gz'.format(VERSION),
 
      long_description="""\
python-gsmmodem is a module that allows easy control of a GSM modem attached
to the system. It also includes a couple of useful commandline utilities for
interacting with a GSM modem.

Its features include:
- simple methods for sending SMS messages, checking signal level, etc
- easy-to-use API for starting and responding to USSD sessions and making voice calls
- handling incoming phone calls and received SMS messages via callback methods
- support for SMS PDU and text mode
- support for tracking SMS status reports
- wraps AT command errors into Python exceptions by default
- modular design; you easily issue your own AT commands to the modem with error
  (with error checking), or read/write directly from/to the modem if you prefer
- comprehensive test suite

Bundled utilities:
- GSMTerm: an easy-to-use serial terminal for communicating with an attached GSM
  modem. It features command completion, built-in help for many AT commands,
  history, context-aware prompt, etc.
- sendsms.py: a simple command line script to send SMS messages
- identify-modem.py: simple utility to identify attached modem. Can also be used to
  provide debug information used for development of python-gsmmodem.
""",

      classifiers=['Development Status :: 4 - Beta',
                   'Environment :: Console',          
                   'Intended Audience :: Developers',
                   'Intended Audience :: Telecommunications Industry',
                   'License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)',
                   'Operating System :: OS Independent',
                   'Programming Language :: Python :: 2.6',
                   'Programming Language :: Python :: 2.7',
                   'Programming Language :: Python :: 3',
                   'Topic :: Communications :: Telephony',
                   'Topic :: Home Automation',
                   'Topic :: Software Development :: Libraries :: Python Modules',
                   'Topic :: System :: Hardware',
                   'Topic :: Terminals :: Serial',
                   'Topic :: Utilities'],
      keywords = ['gsm', 'sms', 'modem', 'mobile', 'phone', 'usb', 'serial'],
      
      packages=['gsmmodem', 'gsmtermlib'],
      package_dir = {'gsmtermlib': 'tools/gsmtermlib'},
      scripts=['tools/gsmterm.py', 'tools/sendsms.py', 'tools/identify-modem.py'],
      install_requires=requires,
      tests_require=tests_require,
      extras_require={'docs': ['sphinx']},
      cmdclass = {'test': RunUnitTests,
                  'coverage': RunUnitTestsCoverage})
