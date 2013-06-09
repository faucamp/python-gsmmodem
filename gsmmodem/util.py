#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Some common utility classes used by tests """

from datetime import timedelta, tzinfo
import re

class SimpleOffsetTzInfo(tzinfo):    
    """ Very simple implementation of datetime.tzinfo offering set timezone offset for datetime instances """
    
    def __init__(self, offsetInHours=None):
        if offsetInHours != None: #pragma: no cover
            self.offsetInHours = offsetInHours        
    
    def utcoffset(self, dt):
        return timedelta(hours=self.offsetInHours)
    
    def dst(self, dt):
        return timedelta(0)

def lineStartingWith(string, lines):
    """ Searches through the specified list of strings and returns the 
    first line starting with the specified search string, or None if not found
    """
    for line in lines:
        if line.startswith(string):
            return line
    else:
        return None

def lineMatching(regexStr, lines):
    """ Searches through the specified list of strings and returns the regular expression 
    match for the first line that matches the specified regex string, or None if no match was found

    Note: if you have a pre-compiled regex pattern, use lineMatchingPattern() instead

    @type regexStr: Regular expression string to use
    @type lines: List of lines to search

    @return: the regular expression match for the first line that matches the specified regex, or None if no match was found
    @rtype: re.Match
    """
    regex = re.compile(regexStr)
    for line in lines:
        m = regex.match(line)
        if m:
            return m
    else:
        return None

def lineMatchingPattern(pattern, lines):
    """ Searches through the specified list of strings and returns the regular expression 
    match for the first line that matches the specified pre-compiled regex pattern, or None if no match was found

    Note: if you are using a regex pattern string (i.e. not already compiled), use lineMatching() instead

    @type pattern: Compiled regular expression pattern to use
    @type lines: List of lines to search

    @return: the regular expression match for the first line that matches the specified regex, or None if no match was found
    @rtype: re.Match
    """
    for line in lines:
        m = pattern.match(line)
        if m:
            return m
    else:
        return None