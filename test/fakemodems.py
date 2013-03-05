""" Module containing fake modem descriptors, for testing """

import abc

class FakeModem(object):
    """ Abstract base class for fake modem descriptors """
    __metaclass__ = abc.ABCMeta

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

class WavecomMultiband900E1800(FakeModem):

    def __init__(self):        
        self.responses = {'AT+CGMI\r': [' WAVECOM MODEM\r\n', 'OK\r\n'],
                 'AT+CGMM\r': [' MULTIBAND  900E  1800\r\n', 'OK\r\n'],
                 'AT+CGMR\r': ['ERROR\r\n'],
                 'AT+CIMI\r': ['111111111111111\r\n', 'OK\r\n'],
                 'AT+CGSN\r': ['111111111111111\r\n', 'OK\r\n'],
                 'AT+CLAC\r': ['ERROR\r\n'],
                 'AT+WIND=63\r': ['OK\r\n'],
                 'AT+CPMS="SM","SM","SR"\r': ['ERROR\r\n'],                 
                 'AT+CPMS=?\r': ['+CPMS: (("SM","BM","SR"),("SM"))\r\n', 'OK\r\n'],
                 'AT+CPMS="SM","SM"\r': ['+CPMS: 14,50,14,50\r\n', 'OK\r\n'],
                 'AT+CNMI=2,1,0,2\r': ['OK\r\n'],
                 'AT+WIND?\r': ['+WIND=0\r\n'],
                 'AT+WIND=50\r': ['OK\r\n'],}
        
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
    
    def __str__(self):
        return 'WAVECOM MODEM MULTIBAND 900E 1800'
        
        
class HuaweiK3715(FakeModem):
    def __init__(self):
        self.responses = {'AT+CGMI\r': ['huawei\r\n', 'OK\r\n'],
                 'AT+CGMM\r': ['K3715\r\n', 'OK\r\n'],
                 'AT+CPMS=?\r': ['+CPMS: ("ME","MT","SM","SR"),("ME","MT","SM","SR"),("ME","MT","SM","SR")\r\n', 'OK\r\n'],
                 'AT+WIND=63\r': ['ERROR\r\n'],
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
^U2DIAG,^CELLMODE,^HSPA,^SCSIOVERTIME,^SETPID,^ADCTEMP,^OPWORD,^CPWORD,^DISLOG,^ANQUERY,^RSCPCFG,^ECIOCFG,\r\n', 'OK\r\n']}
    
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
        
    def __str__(self):
        return 'Huawei K3715'

modems = [HuaweiK3715(), WavecomMultiband900E1800()]
