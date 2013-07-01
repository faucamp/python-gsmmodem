#!/usr/bin/env python

""" Test suite for gsmmodem.util """

from __future__ import print_function

import sys, time, unittest, logging, re

from . import compat # For Python 2.6 compatibility

from gsmmodem.util import allLinesMatchingPattern, lineMatching, lineStartingWith, lineMatchingPattern

class TestUtil(unittest.TestCase):
    """ Tests misc utilities from gsmmodem.util """

    def test_lineStartingWith(self):
        """ Tests function: lineStartingWith """
        lines = ['12345', 'abc', 'defghi', 'abcdef', 'efg']
        result = lineStartingWith('abc', lines)
        self.assertEqual(result, 'abc')
        result = lineStartingWith('d', lines)
        self.assertEqual(result, 'defghi')
        result = lineStartingWith('zzz', lines)
        self.assertEqual(result, None)
        
    def test_lineMatching(self):
        """ Tests function: lineMatching """
        lines = ['12345', 'abc', 'defghi', 'abcdef', 'efg']
        result = lineMatching('^abc.*$', lines)
        self.assertEqual(result.string, 'abc')
        result = lineMatching('^\d+$', lines)
        self.assertEqual(result.string, '12345')
        result = lineMatching('^ZZZ\d+$', lines)
        self.assertEqual(result, None)
        
    def test_lineMatchingPattern(self):
        """ Tests function: lineMatchingPattern """
        lines = ['12345', 'abc', 'defghi', 'abcdef', 'efg']
        result = lineMatchingPattern(re.compile('^abc.*$'), lines)
        self.assertEqual(result.string, 'abc')
        result = lineMatchingPattern(re.compile('^\d+$'), lines)
        self.assertEqual(result.string, '12345')
        result = lineMatchingPattern(re.compile('^ZZZ\d+$'), lines)
        self.assertEqual(result, None)
    
    def test_allLinesMatchingPattern(self):
        """ Tests function: lineStartingWith """
        lines = ['12345', 'abc', 'defghi', 'abcdef', 'efg']
        result = allLinesMatchingPattern(re.compile('^abc.*$'), lines)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].string, 'abc')
        self.assertEqual(result[1].string, 'abcdef')
        result = allLinesMatchingPattern(re.compile('^defghi$'), lines)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].string, 'defghi')
        result = allLinesMatchingPattern(re.compile('^\d+$'), lines)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].string, '12345')
        result = allLinesMatchingPattern(re.compile('^ZZZ\d+$'), lines)
        self.assertIsInstance(result, list)
        self.assertEqual(result, [])


if __name__ == "__main__":
    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)
    unittest.main()
