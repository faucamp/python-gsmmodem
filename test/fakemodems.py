""" Module containing fake modem descriptors, for testing """

import abc
from copy import copy

class FakeModem(object):
    """ Abstract base class for fake modem descriptors """
    __metaclass__ = abc.ABCMeta
    
    def __init__(self):
        self.responses = {}
        self.commandsNoPinRequired = []
        self._pinLock = False
        self.defaultResponse = ['OK\r\n']
        self.pinRequiredErrorResponse = ['+CME ERROR: 11\r\n']        
    
    def getResponse(self, cmd):
        if self._pinLock and not cmd.startswith('AT+CPIN'):
            if cmd in self.commandsNoPinRequired:
                if cmd in self.responses:
                    return self.responses[cmd]
                else:
                    return copy(self.defaultResponse)
            else:
                return copy(self.pinRequiredErrorResponse)
        else:
            if cmd.startswith('AT+CPIN="'):
                self.pinLock = False                
            if cmd in self.responses:
                return copy(self.responses[cmd])
            else:
                return copy(self.defaultResponse)

    @property
    def pinLock(self):
        return self._pinLock
    @pinLock.setter
    def pinLock(self, pinLock):
        self._pinLock = pinLock
        if self._pinLock == True:
            self.responses['AT+CPIN?\r'] = ['+CPIN: SIM PIN\r\n', 'OK\r\n']            
        else:
            self.responses['AT+CPIN?\r'] = ['+CPIN: READY\r\n', 'OK\r\n']

    @abc.abstractmethod
    def getAtdResponse(self, number):
        return []

    @abc.abstractmethod
    def getPreCallInitWaitSequence(self):
        return [0.1]
    
    @abc.abstractmethod
    def getCallInitNotification(self, callId, callType):
        return ['+WIND: 5,1\r\n', '+WIND: 2\r\n']
    
    @abc.abstractmethod
    def getRemoteAnsweredNotification(self, callId, callType):
        return ['OK\r\n']
    
    @abc.abstractmethod
    def getRemoteHangupNotification(self, callId, callType):
        return ['NO CARRIER\r\n', '+WIND: 6,1\r\n']
    
    @abc.abstractmethod
    def getIncomingCallNotification(self, callerNumber, callType='VOICE', ton=145):
        return ['RING\r\n']


class GenericTestModem(FakeModem):
    """ Not a "real" modem - simply used for general tests """
    
    def __init__(self):
        super(GenericTestModem, self).__init__()
        self.commandsNoPinRequired = ['ATZ\r', 'ATE0\r', 'AT+CFUN?\r', 'AT+CFUN=1\r', 'AT+CMEE=1\r']
        self.responses = {'AT+CPMS=?\r': ['+CPMS: ("ME","MT","SM","SR"),("ME","MT","SM","SR"),("ME","MT","SM","SR")\r\n', 'OK\r\n'],
                          'AT+CFUN?\r': ['+CFUN: 1\r\n', 'OK\r\n'],
                          'AT+WIND?\r': ['ERROR\r\n'],
                          'AT+CPIN?\r': ['+CPIN: READY\r\n', 'OK\r\n']} 
    
    def getAtdResponse(self, number):
        raise NotImplementedError()

    def getPreCallInitWaitSequence(self):
        raise NotImplementedError()
    
    def getCallInitNotification(self, callId, callType):
        raise NotImplementedError()
    
    def getRemoteAnsweredNotification(self, callId, callType):
        raise NotImplementedError()
    
    def getRemoteHangupNotification(self, callId, callType):
        raise NotImplementedError()

    def getIncomingCallNotification(self, callerNumber, callType='VOICE', ton=145):
        raise NotImplementedError()


class WavecomMultiband900E1800(FakeModem):

    def __init__(self):
        super(WavecomMultiband900E1800, self).__init__()
        self.responses = {'AT+CGMI\r': [' WAVECOM MODEM\r\n', 'OK\r\n'],
                 'AT+CGMM\r': [' MULTIBAND  900E  1800\r\n', 'OK\r\n'],
                 'AT+CGMR\r': ['ERROR\r\n'],
                 'AT+CIMI\r': ['111111111111111\r\n', 'OK\r\n'],
                 'AT+CGSN\r': ['111111111111111\r\n', 'OK\r\n'],
                 'AT+CFUN?\r': ['+CFUN: 1\r\n', 'OK\r\n'],
                 'AT+CLAC\r': ['ERROR\r\n'],
                 'AT+WIND?\r': ['+WIND: 0\r\n', 'OK\r\n'],
                 'AT+WIND=50\r': ['OK\r\n'],
                 'AT+CPMS="SM","SM","SR"\r': ['ERROR\r\n'],                 
                 'AT+CPMS=?\r': ['+CPMS: (("SM","BM","SR"),("SM"))\r\n', 'OK\r\n'],
                 'AT+CPMS="SM","SM"\r': ['+CPMS: 14,50,14,50\r\n', 'OK\r\n'],
                 'AT+CNMI=2,1,0,2\r': ['OK\r\n'],
                 'AT+CVHU=0\r': ['ERROR\r\n'],
                 'AT+CPIN?\r': ['+CPIN: READY\r\n', 'OK\r\n']}
        self.commandsNoPinRequired = ['ATZ\r', 'ATE0\r', 'AT+CFUN?\r', 'AT+CFUN=1\r', 'AT+CMEE=1\r']
        
    def getAtdResponse(self, number):
        return []
    
    def getPreCallInitWaitSequence(self):
        return [0.1]
        
    def getCallInitNotification(self, callId, callType):
        # +WIND: 5 == indication of call
        # +WIND: 2 == remote party is ringing
        return ['+WIND: 5,1\r\n', '+WIND: 2\r\n']
        
    def getRemoteAnsweredNotification(self, callId, callType):
        return ['OK\r\n']
        
    def getRemoteHangupNotification(self, callId, callType):
        return ['NO CARRIER\r\n', '+WIND: 6,1\r\n']
    
    def getIncomingCallNotification(self, callerNumber, callType='VOICE', ton=145):
        return ['+CRING: {0}\r\n'.format(callType), '+CLIP: "{1}",{2}\r\n'.format(callType, callerNumber, ton)]
    
    def __str__(self):
        return 'WAVECOM MODEM MULTIBAND 900E 1800'    


class HuaweiK3715(FakeModem):
    def __init__(self):
        super(HuaweiK3715, self).__init__()
        self.responses = {'AT+CGMI\r': ['huawei\r\n', 'OK\r\n'],
                 'AT+CGMM\r': ['K3715\r\n', 'OK\r\n'],
                 'AT+CGMR\r': ['11.104.05.00.00\r\n', 'OK\r\n'],
                 'AT+CIMI\r': ['111111111111111\r\n', 'OK\r\n'],
                 'AT+CGSN\r': ['111111111111111\r\n', 'OK\r\n'],
                 'AT+CFUN?\r': ['+CFUN: 1\r\n', 'OK\r\n'],
                 'AT+CPMS=?\r': ['+CPMS: ("ME","MT","SM","SR"),("ME","MT","SM","SR"),("ME","MT","SM","SR")\r\n', 'OK\r\n'],
                 'AT+WIND?\r': ['ERROR\r\n'],
                 'AT+WIND=50\r': ['ERROR\r\n'],
                 'AT+CLAC\r': ['+CLAC:&C,&D,&E,&F,&S,&V,&W,E,I,L,M,Q,V,X,Z,T,P,\S,\V,\
%V,D,A,H,O,S0,S2,S3,S4,S5,S6,S7,S8,S9,S10,S11,S30,S103,S104,+FCLASS,+ICF,+IFC,+IPR,+GMI,\
+GMM,+GMR,+GCAP,+GSN,+DR,+DS,+WS46,+CLAC,+CCLK,+CBST,+CRLP,+CV120,+CHSN,+CSSN,+CREG,+CGREG,\
+CFUN,+GCAP,+CSCS,+CSTA,+CR,+CEER,+CRC,+CMEE,+CGDCONT,+CGDSCONT,+CGTFT,+CGEQREQ,+CGEQMIN,\
+CGQREQ,+CGQMIN,+CGEQNEG,+CGEREP,+CGPADDR,+CGCLASS,+CGSMS,+CSMS,+CMGF,+CSAS,+CRES,+CSCA,\
+CSMP,+CSDH,+CSCB,+FDD,+FAR,+FCL,+FIT,+ES,+ESA,+CMOD,+CVHU,+CGDATA,+CSQ,+CBC,+CPAS,+CPIN,\
+CMEC,+CGATT,+CGACT,+CGCMOD,+CPBS,+CPBR,+CPBF,+CPBW,+CPMS,+CNMI,+CMGL,+CMGR,+CMGS,+CMSS,\
+CMGW,+CMGD,+CMGC,+CNMA,+CMMS,+FTS,+FRS,+FTH,+FRH,+FTM,+FRM,+CHUP,+CCFC,+CCUG,+COPS,+CLCK,\
+CPWD,+CUSD,+CAOC,+CACM,+CAMM,+CPUC,+CCWA,+CHLD,+CIMI,+CGMI,+CGMM,+CGMR,+CGSN,+CNUM,+CSIM,\
+CRSM,+CCLK,+CLVL,+CMUT,+CLCC,+COPN,+CPOL,+CPLS,+CTZR,+CTZU,+CLAC,+CLIP,+COLP,+CDIP,+CTFR,\
+CLIR,$QCSIMSTAT,$QCCNMI,$QCCLR,$QCDMG,$QCDMR,$QCDNSP,$QCDNSS,$QCTER,$QCSLOT,$QCPINSTAT,$QCPDPP,\
$QCPDPLT,$QCPWRDN,$QCDGEN,$BREW,$QCSYSMODE,^CVOICE,^DDSETEX,^pcmrecord,^SYSINFO,^SYSCFG,^IMSICHG,\
^HS,^DTMF,^EARST,^CDUR,^LIGHT,^CPBR,^CPBW,^HWVER,^HVER,^DSFLOWCLR,^DSFLOWQRY,^DSFLOWRPT,^SPN,\
^PORTSEL,^CPIN,^PNN,^OPL,^CPNN,^SN,^CARDLOCK,^BOOT,^FHVER,^CURC,^FREQLOCK,^HSDPA,^HSUPA,^CARDMODE,\
^U2DIAG,^CELLMODE,^HSPA,^SCSIOVERTIME,^SETPID,^ADCTEMP,^OPWORD,^CPWORD,^DISLOG,^ANQUERY,^RSCPCFG,^ECIOCFG,\r\n', 'OK\r\n'],
                 'AT+CPIN?\r': ['+CPIN: READY\r\n', 'OK\r\n']}
        self.commandsNoPinRequired = ['ATZ\r', 'ATE0\r', 'AT+CFUN?\r', 'AT+CFUN=1\r', 'AT+CMEE=1\r']
    
    def getAtdResponse(self, number):
        return ['OK\r\n']
    
    def getPreCallInitWaitSequence(self):
        return [0.1]
    
    def getCallInitNotification(self, callId, callType):
        return ['^ORIG:{0},{1}\r\n'.format(callId, callType), 0.2, '^CONF:{0}\r\n'.format(callId)]
    
    def getRemoteAnsweredNotification(self, callId, callType):
        return ['^CONN:{0},{1}\r\n'.format(callId, callType)]
    
    def getRemoteHangupNotification(self, callId, callType):
            return ['^CEND:{0},5,29,16\r\n'.format(callId)]
        
    def getIncomingCallNotification(self, callerNumber, callType='VOICE', ton=145):
        return ['+CRING: {0}\r\n'.format(callType), '+CLIP: "{1}",{2},,,,0\r\n'.format(callType, callerNumber, ton)]
        
    def __str__(self):
        return 'Huawei K3715'


class QualcommM6280(FakeModem):

    def __init__(self):
        super(QualcommM6280, self).__init__()
        self.commandsNoPinRequired = [] # This modem requires the CPIN command to be issued first
        self.responses = {'AT+CGMI\r': ['QUALCOMM INCORPORATED\r\n', 'OK\r\n'],
                 'AT+CGMM\r': ['M6280\r\n', 'OK\r\n'],
                 'AT+CGMR\r': ['M6280_V1.0.0 M6280_V1.0.0 1 [Sep 4 2008 12:00:00]\r\n', 'OK\r\n'],
                 'AT+CIMI\r': ['111111111111111\r\n', 'OK\r\n'],
                 'AT+CGSN\r': ['111111111111111\r\n', 'OK\r\n'],
                 'AT+CFUN?\r': ['+CFUN: 1\r\n', 'OK\r\n'],
                 'AT+CLAC\r': ['ERROR\r\n'],
                 'AT+WIND?\r': ['ERROR\r\n'],
                 'AT+WIND=50\r': ['ERROR\r\n'],
                 'AT+CPMS=?\r': ['+CPMS: ("ME","MT","SM","SR"),("ME","MT","SM","SR"),("ME","MT","SM","SR")\r\n', 'OK\r\n'],
                 'AT+CVHU=0\r': ['+CVHU: (0-1)\r\n', 'OK\r\n'],
                 'AT+CPIN?\r': ['+CPIN: READY\r\n', 'OK\r\n']}
        
    def getAtdResponse(self, number):
        return ['OK\r\n']
    
    def getPreCallInitWaitSequence(self):
        return [0.1]
    
    def getCallInitNotification(self, callId, callType):
        return ['^ORIG:{0},{1}\r\n'.format(callId, callType), 0.2, '^CONF:{0}\r\n'.format(callId)]
    
    def getRemoteAnsweredNotification(self, callId, callType):
        return ['^CONN:{0},{1}\r\n'.format(callId, callType)]
    
    def getRemoteHangupNotification(self, callId, callType):
            return ['^CEND:{0},5,29,16\r\n'.format(callId)]
        
    def getIncomingCallNotification(self, callerNumber, callType='VOICE', ton=145):
        return ['+CRING: {0}\r\n'.format(callType), '+CLIP: "{1}",{2},,,,0\r\n'.format(callType, callerNumber, ton)]
    
    def __str__(self):
        return 'QUALCOMM INCORPORATED'


modemClasses = [HuaweiK3715, WavecomMultiband900E1800, QualcommM6280]

def createModems():
    return [modem() for modem in modemClasses]
