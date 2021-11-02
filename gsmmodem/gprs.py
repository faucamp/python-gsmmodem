# -*- coding: utf8 -*-

""" GPRS/Data-specific classes 

BRANCH: mms

PLEASE NOTE: *Everything* in this file (PdpContext, GprsModem class, etc) is experimental.
This is NOT meant to be used in production in any way; the API is completely unstable,
no unit tests will be written for this in the forseeable future, and stuff may generally
break and cause riots. Please do not file bug reports against this branch unless you
have a patch to go along with it, but even then: remember that this entire "mms" branch
is exploratory; I simply want to see what the possibilities are with it.

Use the "main" branch, and the GsmModem class if you want to build normal applications.
"""

import re

from .util import allLinesMatchingPattern
from .modem import GsmModem

class PdpContext(object):
    """ Packet Data Protocol (PDP) context parameter values """
    def __init__(self, cid, pdpType, apn, pdpAddress=None, dataCompression=0, headerCompression=0):
        """ Construct a new Packet Data Protocol context
        
        @param cid: PDP Context Identifier - specifies a particular PDP context definition
        @type cid: int
        @param pdpType: the type of packet data protocol (IP, PPP, IPV6, etc)
        @type pdpType: str
        @param apn: Access Point Name; logical name used to select the GGSN or external packet data network
        @type apn: str
        @param pdpAddress: identifies the MT in the address space applicable to the PDP. If None, a dynamic address may be requested.
        @type pdpAddress: str
        @param dataCompression: PDP data compression; 0 == off, 1 == on
        @type dataCompression: int
        @param headerCompression: PDP header compression; 0 == off, 1 == on
        @type headerCompression: int
        """
        self.cid = cid
        self.pdpType = pdpType
        self.apn = apn
        self.pdpAddress = pdpAddress
        self.dataCompression = dataCompression
        self.headerCompression = headerCompression


class GprsModem(GsmModem):
    """ EXPERIMENTAL: Specialized version of GsmModem that includes GPRS/data-specific commands """
    
    @property
    def pdpContexts(self):
        """ Currently-defined Packet Data Protocol (PDP) context list
        
        PDP paramter values returned include PDP type (IP, IPV6, PPP, X.25 etc), APN, 
        data compression, header compression, etc.
        
        @return: a list of currently-defined PDP contexts
        """
        result = []
        cgdContResult = self.write('AT+CGDCONT?')
        matches = allLinesMatchingPattern(re.compile(r'^\+CGDCONT:\s*(\d+),"([^"]+)","([^"]+)","([^"]+)",(\d+),(\d+)'), cgdContResult)
        for cgdContMatch in matches:
            cid, pdpType, apn, pdpAddress, dataCompression, headerCompression = cgdContMatch.groups()
            pdpContext = PdpContext(cid, pdpType, apn, pdpAddress, dataCompression, headerCompression)
            result.append(pdpContext)
        return result
    
    @property
    def defaultPdpContext(self):
        """ @return: the default PDP context, or None if not defined """
        pdpContexts = self.pdpContexts
        return pdpContexts[0] if len(pdpContexts) > 0 else None
    @defaultPdpContext.setter
    def defaultPdpContext(self, pdpContext):
        """ Set the default PDP context (or clear it by setting it to None) """
        self.write('AT+CGDCONT=,"{0}","{1}","{2}",{3},{4}'.format(pdpContext.pdpType, pdpContext.apn, pdpContext.pdpAddress or '', pdpContext.dataCompression, pdpContext.headerCompression))
    
    def definePdpContext(self, pdpContext):
        """ Define a new Packet Data Protocol context, or overwrite an existing one
        
        @param pdpContext: The PDP context to define
        @type pdpContext: gsmmodem.gprs.PdpContext
        """
        self.write('AT+CGDCONT={0},"{1}","{2}","{3}",{4},{5}'.format(pdpContext.cid or '', pdpContext.pdpType, pdpContext.apn, pdpContext.pdpAddress or '', pdpContext.dataCompression, pdpContext.headerCompression))

    def initDataConnection(self, pdpCid=1):
        """ Initializes a packet data (GPRS) connection using the specified PDP Context ID """
        # From this point on, we don't want the read thread interfering
        #self.log.debug('Stopping read thread')
        #self.alive = False
        #self.rxThread.join()
        self.log.debug('Init data connection')
        self.write('ATD*99#', expectedResponseTermSeq="CONNECT\r")
        self.log.debug('Data connection open; ready for PPP comms')
        # From here on we use PPP to communicate with the network
