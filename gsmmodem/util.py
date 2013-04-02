#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Some common utility classes used by tests """

from datetime import timedelta, tzinfo

class SimpleOffsetTzInfo(tzinfo):    
    """ Very simple implementation of datetime.tzinfo offering set timezone offset for datetime instances """
    
    def __init__(self, offsetInHours=None):
        if offsetInHours != None:
            self.offsetInHours = offsetInHours        
    
    def utcoffset(self, dt):
        return timedelta(hours=self.offsetInHours)
    
    def dst(self, dt):        
        return timedelta(0)
