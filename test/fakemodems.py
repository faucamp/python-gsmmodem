""" Module containing fake modem descriptors, for testing """

import abc
from copy import copy

class FakeModem(object):
    """ Abstract base class for fake modem descriptors """
    __metaclass__ = abc.ABCMeta
    
    def __init__(self):
        self.responses = {}
        self.commandsNoPinRequired = []
        self.commandsSimBusy = [] # Commands that may trigger "SIM busy" errors
        self.pinLock = False
        self.defaultResponse = ['OK\r\n']
        self.pinRequiredErrorResponse = ['+CME ERROR: 11\r\n']
        self.smscNumber = None
        self.simBusyErrorCounter = 0 # Number of times to issue a "SIM busy" error
        self.deviceBusyErrorCounter = 0 # Number of times to issue a "Device busy" error
        self.cfun = 1 # +CFUN value to report back
        self.dtmfCommandBase = '+VTS='
    
    def getResponse(self, cmd):
        if self.deviceBusyErrorCounter > 0:
            self.deviceBusyErrorCounter -= 1
            return ['+CME ERROR: 515\r\n']
        if self._pinLock and not cmd.startswith('AT+CPIN'):
            if cmd not in self.commandsNoPinRequired:                
                return copy(self.pinRequiredErrorResponse)

        if cmd.startswith('AT+CPIN="'):
            self.pinLock = False
        elif self.simBusyErrorCounter > 0 and cmd in self.commandsSimBusy:
            self.simBusyErrorCounter -= 1
            return ['+CME ERROR: 14\r\n']
        if cmd == 'AT+CFUN?\r' and self.cfun != -1:
            return ['+CFUN: {0}\r\n'.format(self.cfun), 'OK\r\n']
        elif cmd == 'AT+CSCA?\r':                
            if self.smscNumber != None:
                return ['+CSCA: "{0}",145\r\n'.format(self.smscNumber), 'OK\r\n']
            else:
                return ['OK\r\n']
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

    def getRemoteRejectCallNotification(self, callId, callType):
        # For a lot of modems, this is the same as a hangup notification - override this if necessary!
        return self.getRemoteHangupNotification(callId, callType)
    
    @abc.abstractmethod
    def getIncomingCallNotification(self, callerNumber, callType='VOICE', ton=145):
        return ['RING\r\n']


class GenericTestModem(FakeModem):
    """ Not based on a real modem - simply used for general tests. Uses polling for call status updates """
    
    def __init__(self):
        super(GenericTestModem, self).__init__()
        self._callState = 2
        self._callNumber = None
        self._callId = None
        self.commandsNoPinRequired = ['ATZ\r', 'ATE0\r', 'AT+CFUN?\r', 'AT+CFUN=1\r', 'AT+CMEE=1\r']
        self.responses = {'AT+CPMS=?\r': ['+CPMS: ("ME","MT","SM","SR"),("ME","MT","SM","SR"),("ME","MT","SM","SR")\r\n', 'OK\r\n'],
                          'AT+CLAC\r': ['ERROR\r\n'],
                          'AT+WIND?\r': ['ERROR\r\n'],
                          'AT+WIND=50\r': ['ERROR\r\n'],
                          'AT+ZPAS?\r': ['ERROR\r\n'],
                          'AT+CPIN?\r': ['+CPIN: READY\r\n', 'OK\r\n']} 

    def getResponse(self, cmd):
        if not self._pinLock and cmd == 'AT+CLCC\r':
            if self._callNumber:
                if self._callState == 0:
                    return ['+CLCC: 1,0,2,0,0,"{0}",129\r\n'.format(self._callNumber), 'OK\r\n']
                elif self._callState == 1:
                    return ['+CLCC: 1,0,0,0,0,"{0}",129\r\n'.format(self._callNumber), 'OK\r\n']
                else:
                    return ['OK\r\n']
            else:
                return super(GenericTestModem, self).getResponse(cmd)
        else:
            return super(GenericTestModem, self).getResponse(cmd)

    def getAtdResponse(self, number):
        self._callNumber = number
        self._callState = 0
        return ['OK\r\n']

    def getPreCallInitWaitSequence(self):
        return [0.1]

    def getCallInitNotification(self, callId, callType):
        return []

    def getRemoteAnsweredNotification(self, callId, callType):
        self._callState = 1
        return []

    def getRemoteHangupNotification(self, callId, callType):
        self._callState = 2
        self._callNumber = None
        return []

    def getIncomingCallNotification(self, callerNumber, callType='VOICE', ton=145):
        return ['+CRING: {0}\r\n'.format(callType), '+CLIP: "{1}",{2},,,,0\r\n'.format(callType, callerNumber, ton)]


class WavecomMultiband900E1800(FakeModem):
    """ Family of old Wavecom serial modems
    
    User franciumlin also submitted the following improvements to this profile:
      +CPIN replies are not ended with "OK"
    """

    def __init__(self):
        super(WavecomMultiband900E1800, self).__init__()
        self.responses = {'AT+CGMI\r': [' WAVECOM MODEM\r\n', 'OK\r\n'],
                 'AT+CGMM\r': [' MULTIBAND  900E  1800\r\n', 'OK\r\n'],
                 'AT+CGMR\r': ['ERROR\r\n'],
                 'AT+CIMI\r': ['111111111111111\r\n', 'OK\r\n'],
                 'AT+CGSN\r': ['111111111111111\r\n', 'OK\r\n'],                 
                 'AT+CLAC\r': ['ERROR\r\n'],
                 'AT+WIND?\r': ['+WIND: 0\r\n', 'OK\r\n'],
                 'AT+WIND=50\r': ['OK\r\n'],
                 'AT+ZPAS?\r': ['ERROR\r\n'],
                 'AT+CPMS="SM","SM","SR"\r': ['ERROR\r\n'],                 
                 'AT+CPMS=?\r': ['+CPMS: (("SM","BM","SR"),("SM"))\r\n', 'OK\r\n'],
                 'AT+CPMS="SM","SM"\r': ['+CPMS: 14,50,14,50\r\n', 'OK\r\n'],
                 'AT+CNMI=2,1,0,2\r': ['OK\r\n'],
                 'AT+CVHU=0\r': ['ERROR\r\n'],
                 'AT+CPIN?\r': ['+CPIN: READY\r\n']} # <---- note: missing 'OK\r\n'
        self.commandsNoPinRequired = ['ATZ\r', 'ATE0\r', 'AT+CFUN?\r', 'AT+CFUN=1\r', 'AT+CMEE=1\r']
    
    def getResponse(self, cmd):
        if cmd == 'AT+CFUN=1\r':
            self.deviceBusyErrorCounter = 2 # This modem takes quite a while to recover from this
            return ['OK\r\n']
        return super(WavecomMultiband900E1800, self).getResponse(cmd)
    
    @property
    def pinLock(self):
        return self._pinLock
    @pinLock.setter
    def pinLock(self, pinLock):
        self._pinLock = pinLock
        if self._pinLock == True:
            self.responses['AT+CPIN?\r'] = ['+CPIN: SIM PIN\r\n']  # missing OK
        else:
            self.responses['AT+CPIN?\r'] = ['+CPIN: READY\r\n'] # missing OK
    
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
    """ Huawei K3715 modem (commonly used by Vodafone) """

    def __init__(self):
        super(HuaweiK3715, self).__init__()
        self.responses = {'AT+CGMI\r': ['huawei\r\n', 'OK\r\n'],
                 'AT+CGMM\r': ['K3715\r\n', 'OK\r\n'],
                 'AT+CGMR\r': ['11.104.05.00.00\r\n', 'OK\r\n'],
                 'AT+CIMI\r': ['111111111111111\r\n', 'OK\r\n'],
                 'AT+CGSN\r': ['111111111111111\r\n', 'OK\r\n'],                 
                 'AT+CPMS=?\r': ['+CPMS: ("ME","MT","SM","SR"),("ME","MT","SM","SR"),("ME","MT","SM","SR")\r\n', 'OK\r\n'],
                 'AT+WIND?\r': ['ERROR\r\n'],
                 'AT+WIND=50\r': ['ERROR\r\n'],
                 'AT+ZPAS?\r': ['ERROR\r\n'],
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
        self.dtmfCommandBase = '^DTMF={cid},'
    
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


class HuaweiE1752(FakeModem):
    """ Huawei E1752 modem (used by Cell C in South Africa)
    This modem issues "COMMAND NOT SUPPORT" non-standard error messages
    """

    def __init__(self):
        super(HuaweiE1752, self).__init__()
        # This modem uses AT^USSDMODE to control text/PDU mode USSD
        self._ussdMode = 1
        self.responses = {'AT+CGMI\r': ['huawei\r\n', 'OK\r\n'],
                 'AT+CGMM\r': ['E1752\r\n', 'OK\r\n'],
                 'AT+CGMR\r': ['11.126.13.00.00\r\n', 'OK\r\n'],
                 'AT+CIMI\r': ['111111111111111\r\n', 'OK\r\n'],
                 'AT+CGSN\r': ['111111111111111\r\n', 'OK\r\n'],
                 'AT+CPMS=?\r': ['+CPMS: ("ME","MT","SM","SR"),("ME","MT","SM","SR"),("ME","MT","SM","SR")\r\n', 'OK\r\n'],
                 # Note the non-standard "COMMAND NOT SUPPORT" error message
                 'AT+WIND?\r': ['COMMAND NOT SUPPORT\r\n'],
                 'AT+WIND=50\r': ['COMMAND NOT SUPPORT\r\n'],
                 'AT+ZPAS?\r': ['COMMAND NOT SUPPORT\r\n'],
                 # Modem has non-standard +CLAC response (does not start with +CLAC:, and extra \r added to each line (i.e. as part of the command name)
                 'AT+CLAC\r': ['&C\r\r\n', '&D\r\r\n', '&F\r\r\n', '&V\r\r\n', 'E\r\r\n', 'I\r\r\n', 'L\r\r\n', 'M\r\r\n',
                               'Q\r\r\n', 'V\r\r\n', 'X\r\r\n', 'Z\r\r\n', 'T\r\r\n', 'P\r\r\n', 'D\r\r\n', 'A\r\r\n',
                               'H\r\r\n', 'O\r\r\n', 'S0\r\r\n', 'S2\r\r\n', 'S3\r\r\n', 'S4\r\r\n', 'S5\r\r\n', 'S6\r\r\n',
                               'S7\r\r\n', 'S8\r\r\n', 'S9\r\r\n', 'S10\r\r\n', 'S11\r\r\n', 'S30\r\r\n', 'S103\r\r\n',
                               'S104\r\r\n', '+FCLASS\r\r\n', '+ICF\r\r\n', '+IFC\r\r\n', '+IPR\r\r\n', '+GMI\r\r\n',
                               '+GMM\r\r\n', '+GMR\r\r\n', '+GCAP\r\r\n', '+GSN\r\r\n', '+DR\r\r\n', '+DS\r\r\n',
                               '+WS46\r\r\n', '+CLAC\r\r\n', '+CCLK\r\r\n', '+CBST\r\r\n', '+CRLP\r\r\n', '+CV120\r\r\n',
                               '+CHSN\r\r\n', '+CSSN\r\r\n', '+CREG\r\r\n', '+CGREG\r\r\n', '+CFUN\r\r\n', '+GCAP\r\r\n',
                               '+CSCS\r\r\n', '+CSTA\r\r\n', '+CR\r\r\n', '+CEER\r\r\n', '+CRC\r\r\n', '+CMEE\r\r\n',
                               '+CGDCONT\r\r\n', '+CGDSCONT\r\r\n', '+CGTFT\r\r\n', '+CGEQREQ\r\r\n', '+CGEQMIN\r\r\n',
                               '+CGQREQ\r\r\n', '+CGQMIN\r\r\n', '+CGEQNEG\r\r\n', '+CGEREP\r\r\n', '+CGPADDR\r\r\n',
                               '+CGCLASS\r\r\n', '+CGSMS\r\r\n', '+CSMS\r\r\n', '+CMGF\r\r\n', '+CSAS\r\r\n', '+CRES\r\r\n',
                               '+CSCA\r\r\n', '+CSMP\r\r\n', '+CSDH\r\r\n', '+CSCB\r\r\n', '+FDD\r\r\n', '+FAR\r\r\n',
                               '+FCL\r\r\n', '+FIT\r\r\n', '+ES\r\r\n', '+ESA\r\r\n', '+CMOD\r\r\n', '+CVHU\r\r\n',
                               '+CGDATA\r\r\n', '+CSQ\r\r\n', '+CBC\r\r\n', '+CPAS\r\r\n', '+CPIN\r\r\n', '+CMEC\r\r\n',
                               '+CKPD\r\r\n', '+CIND\r\r\n', '+CMER\r\r\n', '+CGATT\r\r\n', '+CGACT\r\r\n', '+CGCMOD\r\r\n',
                               '+CPBS\r\r\n', '+CPBR\r\r\n', '+CPBF\r\r\n', '+CPBW\r\r\n', '+CPMS\r\r\n', '+CNMI\r\r\n',
                               '+CMGL\r\r\n', '+CMGR\r\r\n', '+CMGS\r\r\n', '+CMSS\r\r\n', '+CMGW\r\r\n', '+CMGD\r\r\n',
                               '+CMGC\r\r\n', '+CNMA\r\r\n', '+CMMS\r\r\n', '+FTS\r\r\n', '+FRS\r\r\n', '+FTH\r\r\n',
                               '+FRH\r\r\n', '+FTM\r\r\n', '+FRM\r\r\n', '+CHUP\r\r\n', '+CCFC\r\r\n', '+CCUG\r\r\n',
                               '+COPS\r\r\n', '+CLCK\r\r\n', '+CPWD\r\r\n', '+CUSD\r\r\n', '+CAOC\r\r\n', '+CACM\r\r\n',
                               '+CAMM\r\r\n', '+CPUC\r\r\n', '+CCWA\r\r\n', '+CHLD\r\r\n', '+CIMI\r\r\n', '+CGMI\r\r\n',
                               '+CGMM\r\r\n', '+CGMR\r\r\n', '+CGSN\r\r\n', '+CNUM\r\r\n', '+CSIM\r\r\n', '+CRSM\r\r\n',
                               '+CCLK\r\r\n', '+CLVL\r\r\n', '+CMUT\r\r\n', '+CLCC\r\r\n', '+COPN\r\r\n', '+CPOL\r\r\n',
                               '+CPLS\r\r\n', '+CTZR\r\r\n', '+CTZU\r\r\n', '+CLAC\r\r\n', '+CLIP\r\r\n', '+COLP\r\r\n',
                               '+CDIP\r\r\n', '+CTFR\r\r\n', '+CLIR\r\r\n', '$QCSIMSTAT\r\r\n', '$QCCNMI\r\r\n',
                               '$QCCLR\r\r\n', '$QCDMG\r\r\n', '$QCDMR\r\r\n', '$QCDNSP\r\r\n', '$QCDNSS\r\r\n',
                               '$QCTER\r\r\n', '$QCSLOT\r\r\n', '$QCPINSTAT\r\r\n', '$QCPDPP\r\r\n', '$QCPDPLT\r\r\n',
                               '$QCPWRDN\r\r\n', '$QCDGEN\r\r\n', '$BREW\r\r\n', '$QCSYSMODE\r\r\n', '$QCCTM\r\r\n',
                               '^RFSWITCH\r\r\n', '^SOFTSWITCH\r\r\n', '^FLIGHTMODESAVE\r\r\n', '^IMSICHG\r\r\n',
                               '^STSF\r\r\n', '^STGI\r\r\n', '^STGR\r\r\n', '^CELLMODE\r\r\n', '^SYSINFO\r\r\n',
                               '^DIALMODE\r\r\n', '^SYSCFG\r\r\n', '^SYSCONFIG\r\r\n', '^HS\r\r\n', '^DTMF\r\r\n',
                               '^CPBR\r\r\n', '^CPBW\r\r\n', '^HWVER\r\r\n', '^HVER\r\r\n', '^DSFLOWCLR\r\r\n',
                               '^DSFLOWQRY\r\r\n', '^DSFLOWRPT\r\r\n', '^SPN\r\r\n', '^PORTSEL\r\r\n', '^CPIN\r\r\n',
                               '^SN\r\r\n', '^EARST\r\r\n', '^CARDLOCK\r\r\n', '^CARDUNLOCK\r\r\n', '^ATRECORD\r\r\n',
                               '^CDUR\r\r\n', '^BOOT\r\r\n', '^FHVER\r\r\n', '^CURC\r\r\n', '^FREQLOCK\r\r\n',
                               '^FREQPREF\r\r\n', '^HSPA\r\r\n', '^HSUPA\r\r\n', '^GPSTYPE\r\r\n', '^HSDPA\r\r\n',
                               '^GLASTERR\r\r\n', '^CARDMODE\r\r\n', '^U2DIAG\r\r\n', '^RSTRIGGER\r\r\n', '^SETPID\r\r\n',
                               '^SCSITIMEOUT\r\r\n', '^CQI\r\r\n', '^GETPORTMODE\r\r\n', '^CVOICE\r\r\n', '^DDSETEX\r\r\n',
                               '^pcmrecord\r\r\n', '^CSNR\r\r\n', '^CMSR\r\r\n', '^CMMT\r\r\n', '^CMGI\r\r\n', '^RDCUST\r\r\n',
                               '^OPWORD\r\r\n', '^CPWORD\r\r\n', '^DISLOG\r\r\n', '^FPLMN\r\r\n', '^FPLMNCTRL\r\r\n',
                               '^ANQUERY\r\r\n', '^RSCPCFG\r\r\n', '^ECIOCFG\r\r\n', '^IMSICHECK\r\r\n', '^USSDMODE\r\r\n',
                               '^SLOTCFG\r\r\n', '^YJCX\r\r\n', '^NDISDUP\r\r\n', '^DHCP\r\r\n', '^AUTHDATA\r\r\n',
                               '^CRPN\r\r\n', '^ICCID\r\r\n', '^NVMBN\r\r\n', '^RXDIV\r\r\n', '^DNSP\r\r\n', '^DNSS\r\r\n',
                               '^WPDST\r\r\n', '^WPDOM\r\r\n', '^WPDFR\r\r\n', '^WPQOS\r\r\n', '^WPDSC\r\r\n', '^WPDGP\r\r\n',
                               '^WPEND\r\r\n', '^WNICT\r\r\n', '^SOCKETCONT\r\r\n', '^WPURL\r\r\n', '^WMOLR\r\r\n',
                               '^SECTIME\r\r\n', '^WPDNP\r\r\n', '^WPDDL\r\r\n', '^WPDCP\r\r\n', 'OK\r\n'],
                 'AT+CPIN?\r': ['+CPIN: READY\r\n', 'OK\r\n']}
        self.commandsNoPinRequired = ['ATZ\r', 'ATE0\r', 'AT+CFUN?\r', 'AT+CFUN=1\r', 'AT+CMEE=1\r']
        self.dtmfCommandBase = '^DTMF={cid},'
        
    def getResponse(self, cmd):
        # Device defaults to ^USSDMODE == 1
        if cmd.startswith('AT+CUSD=1') and self._ussdMode == 1: 
            return ['ERROR\r\n']
        elif cmd.startswith('AT^USSDMODE='):
            self._ussdMode = int(cmd[12])
            return super(HuaweiE1752, self).getResponse(cmd)
        else:
            return super(HuaweiE1752, self).getResponse(cmd)

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
        return 'Huawei E1752'


class QualcommM6280(FakeModem):
    """ Qualcomm/ZTE modem information provided by davidphiliplee on github """

    def __init__(self):
        super(QualcommM6280, self).__init__()
        self._callState = 2
        self._callNumber = None
        self._callId = None
        self.commandsNoPinRequired = [] # This modem requires the CPIN command to be issued first
        self.commandsSimBusy = ['AT+CSCA?\r'] # Issue #10 on github
        self.responses = {'AT+CGMI\r': ['QUALCOMM INCORPORATED\r\n', 'OK\r\n'],
                 'AT+CGMM\r': ['M6280\r\n', 'OK\r\n'],
                 'AT+CGMR\r': ['M6280_V1.0.0 M6280_V1.0.0 1 [Sep 4 2008 12:00:00]\r\n', 'OK\r\n'],
                 'AT+CIMI\r': ['111111111111111\r\n', 'OK\r\n'],
                 'AT+CGSN\r': ['111111111111111\r\n', 'OK\r\n'],
                 'AT+CLAC\r': ['ERROR\r\n'],
                 'AT+WIND?\r': ['ERROR\r\n'],
                 'AT+WIND=50\r': ['ERROR\r\n'],
                 'AT+ZPAS?\r':  ['+BEARTYPE: "UMTS","CS_PS"\r\n', 'OK\r\n'],
                 'AT+CPMS=?\r': ['+CPMS: ("ME","MT","SM","SR"),("ME","MT","SM","SR"),("ME","MT","SM","SR")\r\n', 'OK\r\n'],
                 'AT+CVHU=0\r': ['+CVHU: (0-1)\r\n', 'OK\r\n'],
                 'AT+CPIN?\r': ['+CPIN: READY\r\n', 'OK\r\n']}

    def getResponse(self, cmd):
        if not self._pinLock:
            if cmd.startswith('AT+CSMP='):
                # Clear the SMSC number (this behaviour was reported in issue #8 on github)
                self.smscNumber = None
            elif cmd == 'AT+CLCC\r':
                if self._callNumber:
                    if self._callState == 0:
                        return ['+CLCC: 1,0,2,0,0,"{0}",129\r\n'.format(self._callNumber), 'OK\r\n']
                    elif self._callState == 1:
                        return ['+CLCC: 1,0,0,0,0,"{0}",129\r\n'.format(self._callNumber), 'OK\r\n']
                    else:
                        return ['OK\r\n']
            return super(QualcommM6280, self).getResponse(cmd)
        else:
            return super(QualcommM6280, self).getResponse(cmd)

    def getAtdResponse(self, number):
        self._callNumber = number
        self._callState = 0
        return []
    
    def getPreCallInitWaitSequence(self):
        return [0.1]
    
    def getCallInitNotification(self, callId, callType):
        return []
    
    def getRemoteAnsweredNotification(self, callId, callType):
        return ['CONNECT\r\n']
    
    def getRemoteHangupNotification(self, callId, callType):
        self._callState = 2
        self._callNumber = None
        return ['HANGUP: {0}\r\n'.format(callId)]

    def getIncomingCallNotification(self, callerNumber, callType='VOICE', ton=145):
        return ['+CRING: {0}\r\n'.format(callType), '+CLIP: "{1}",{2},,,,0\r\n'.format(callType, callerNumber, ton)]
    
    def __str__(self):
        return 'QUALCOMM M6280 (ZTE modem)'


class ZteK3565Z(FakeModem):
    """ ZTE K3565-Z (Vodafone branded) """

    def __init__(self):
        super(ZteK3565Z, self).__init__()
        self._callState = 2
        self._callNumber = None
        self._callId = None
        self.commandsNoPinRequired = [] # This modem requires the CPIN command to be issued first
        self.responses = {'AT+CGMI\r': ['ZTE INCORPORATED\r\n', 'OK\r\n'],
                 'AT+CGMM\r': ['K3565-Z\r\n', 'OK\r\n'],
                 'AT+CGMR\r': ['BD_P673A2V1.0.0B09\r\n', 'OK\r\n'],
                 'AT+CFUN?\r': ['+CFUN: (0-1,4-7),(0-1)\r\n', 'OK\r\n'],
                 'AT+CIMI\r': ['111111111111111\r\n', 'OK\r\n'],
                 'AT+CGSN\r': ['111111111111111\r\n', 'OK\r\n'],
                 # Note that AT+CLAC does NOT respond in the standard "+CLAC:" format
                 'AT+CLAC\r': ['&C\r\n', '&D\r\n', '&E\r\n', '&F\r\n', '&S\r\n', '&V\r\n', '&W\r\n', 'E\r\n', 'I\r\n',
                               'L\r\n', 'M\r\n', 'Q\r\n', 'V\r\n', 'X\r\n', 'Z\r\n', 'T\r\n', 'P\r\n', '\\Q\r\n', '\\S\r\n',
                               '\\V\r\n', '%V\r\n', 'D\r\n', 'A\r\n', 'H\r\n', 'O\r\n', 'S0\r\n', 'S2\r\n', 'S3\r\n', 'S4\r\n',
                               'S5\r\n', 'S6\r\n', 'S7\r\n', 'S8\r\n', 'S9\r\n', 'S10\r\n', 'S11\r\n', 'S30\r\n', 'S103\r\n',
                               'S104\r\n', '+FCLASS\r\n', '+ICF\r\n', '+IFC\r\n', '+IPR\r\n', '+GMI\r\n', '+GMM\r\n',
                               '+GMR\r\n', '+GCAP\r\n', '+GSN\r\n', '+DR\r\n', '+DS\r\n', '+WS46\r\n', '+CBST\r\n', '+CRLP\r\n',
                               '+CV120\r\n', '+CHSN\r\n', '+CSSN\r\n', '+CREG\r\n', '+CGREG\r\n', '+CFUN\r\n', '+GCAP\r\n',
                               '+CSCS\r\n', '+CSTA\r\n', '+CR\r\n', '+CEER\r\n', '+CRC\r\n', '+CMEE\r\n', '+CGDCONT\r\n',
                               '+CGDSCONT\r\n', '+CGTFT\r\n', '+CGEQREQ\r\n', '+CGEQMIN\r\n', '+CGQREQ\r\n', '+CGQMIN\r\n',
                               '+CGEREP\r\n', '+CGPADDR\r\n', '+CGDATA\r\n', '+CGCLASS\r\n', '+CGSMS\r\n', '+CSMS\r\n',
                               '+CMGF\r\n', '+CSAS\r\n', '+CRES\r\n', '+CSCA\r\n', '+CSMP\r\n', '+CSDH\r\n', '+CSCB\r\n',
                               '+FDD\r\n', '+FAR\r\n', '+FCL\r\n', '+FIT\r\n', '+ES\r\n', '+ESA\r\n', '+CMOD\r\n', '+CVHU\r\n',
                               '+CSQ\r\n', '+ZRSSI\r\n', '+CBC\r\n', '+CPAS\r\n', '+CPIN\r\n', '+CMEC\r\n', '+CKPD\r\n',
                               '+CGATT\r\n', '+CGACT\r\n', '+CGCMOD\r\n', '+CPBS\r\n', '+CPBR\r\n', '+ZCPBR\r\n',
                               '+ZUSIM\r\n', '+CPBF\r\n', '+CPBW\r\n', '+ZCPBW\r\n', '+CPMS\r\n', '+CNMI\r\n',
                               '+CMGL\r\n', '+CMGR\r\n', '+CMGS\r\n', '+CMSS\r\n', '+CMGW\r\n', '+CMGD\r\n', '+CMGC\r\n',
                               '+CNMA\r\n', '+CMMS\r\n', '+CHUP\r\n', '+CCFC\r\n', '+CCUG\r\n', '+COPS\r\n', '+CLCK\r\n',
                               '+CPWD\r\n', '+CUSD\r\n', '+CAOC\r\n', '+CACM\r\n', '+CAMM\r\n', '+CPUC\r\n', '+CCWA\r\n',
                               '+CHLD\r\n', '+CIMI\r\n', '+CGMI\r\n', '+CGMM\r\n', '+CGMR\r\n', '+CGSN\r\n', '+CNUM\r\n',
                               '+CSIM\r\n', '+CRSM\r\n', '+CCLK\r\n', '+CLVL\r\n', '+CMUT\r\n', '+CLCC\r\n', '+COPN\r\n',
                               '+CPOL\r\n', '+CPLS\r\n', '+CTZR\r\n', '+CTZU\r\n', '+CLAC\r\n', '+CLIP\r\n', '+COLP\r\n',
                               '+CDIP\r\n', '+CTFR\r\n', '+CLIR\r\n', '$QCSIMSTAT\r\n', '$QCCNMI\r\n', '$QCCLR\r\n',
                               '$QCDMG\r\n', '$QCDMR\r\n', '$QCDNSP\r\n', '$QCDNSS\r\n', '$QCTER\r\n', '$QCSLOT\r\n',
                               '$QCPINSTAT\r\n', '$QCPDPP\r\n', '$QCPDPLT\r\n', '$QCPWRDN\r\n', '$QCDGEN\r\n',
                               '$BREW\r\n', '$QCSYSMODE\r\n', 'OK\r\n'],
                 'AT+WIND?\r': ['ERROR\r\n'],
                 'AT+WIND=50\r': ['ERROR\r\n'],
                 'AT+ZPAS?\r':  ['+BEARTYPE: "UMTS","CS_PS"\r\n', 'OK\r\n'],
                 'AT+CPMS=?\r': ['+CPMS: ("ME","MT","SM","SR"),("ME","MT","SM","SR"),("ME","MT","SM","SR")\r\n', 'OK\r\n'],
                 'AT+CVHU=0\r': ['+CVHU: (0-1)\r\n', 'OK\r\n'],
                 'AT+CPIN?\r': ['+CPIN: READY\r\n', 'OK\r\n']}

    def getResponse(self, cmd):
        if not self._pinLock:
            if cmd.startswith('AT+CSMP='):
                # Clear the SMSC number (this behaviour was reported in issue #8 on github)
                self.smscNumber = None
            elif cmd == 'AT+CLCC\r':
                if self._callNumber:
                    if self._callState == 0:
                        return ['+CLCC: 1,0,2,0,0,"{0}",129\r\n'.format(self._callNumber), 'OK\r\n']
                    elif self._callState == 1:
                        return ['+CLCC: 1,0,0,0,0,"{0}",129\r\n'.format(self._callNumber), 'OK\r\n']
                    else:
                        return ['OK\r\n']
            return super(ZteK3565Z, self).getResponse(cmd)
        else:
            return super(ZteK3565Z, self).getResponse(cmd)

    def getAtdResponse(self, number):
        self._callNumber = number
        self._callState = 0
        return []

    def getPreCallInitWaitSequence(self):
        return [0.1]

    def getCallInitNotification(self, callId, callType):
        return []

    def getRemoteAnsweredNotification(self, callId, callType):
        return ['CONNECT\r\n']

    def getRemoteHangupNotification(self, callId, callType):
        self._callState = 2
        self._callNumber = None
        return ['HANGUP: {0}\r\n'.format(callId)]

    def getRemoteRejectCallNotification(self, callId, callType):
        self._callState = 2
        self._callNumber = None
        return ["OK\r\n"]

    def getIncomingCallNotification(self, callerNumber, callType='VOICE', ton=145):
        return ['+CRING: {0}\r\n'.format(callType), '+CLIP: "{1}",{2},,,,0\r\n'.format(callType, callerNumber, ton)]

    def __str__(self):
        return 'ZTE K3565-Z'


class NokiaN79(GenericTestModem):
    """ Nokia Symbian S60-based modem (details taken from a Nokia N79) and
    also from issue 15: https://github.com/faucamp/python-gsmmodem/issues/15 (Nokia N95)
    
    SMS reading is not supported on these devices via AT commands; thus
    commands like AT+CNMI are not supported.
    """

    def __init__(self):
        super(NokiaN79, self).__init__()
        self.responses = {'AT+CGMI\r': ['Nokia\r\n', 'OK\r\n'],
                 'AT+CGMM\r': ['Nokia N79\r\n', 'OK\r\n'],
                 'AT+CGMR\r': ['V ICPR72_08w44.1\r\n', '24-11-08\r\n', 'RM-348\r\n', '(c) Nokia\r\n', '11.049\r\n', 'OK\r\n'],
                 'AT+CIMI\r': ['111111111111111\r\n', 'OK\r\n'],
                 'AT+CGSN\r': ['111111111111111\r\n', 'OK\r\n'],
                 'AT+CNMI=2,1,0,2\r': ['ERROR\r\n'], # SMS reading and notifications not supported
                 'AT+CLAC\r': ['ERROR\r\n'],
                 'AT+WIND?\r': ['ERROR\r\n'],
                 'AT+WIND=50\r': ['ERROR\r\n'],
                 'AT+ZPAS?\r': ['ERROR\r\n'],
                 'AT+CPMS="SM","SM","SR"\r': ['ERROR\r\n'],                 
                 'AT+CPMS=?\r': ['+CPMS: (),(),()\r\n', 'OK\r\n'], # not supported
                 'AT+CPMS?\r': ['+CPMS: ,,,,,,,,\r\n', 'OK\r\n'], # not supported
                 'AT+CPMS=,,\r': ['ERROR\r\n'],
                 'AT+CPMS="SM","SM"\r': ['ERROR\r\n'], # not supported
                 'AT+CSMP?\r': ['+CSMP: 49,167,0,0\r\n', 'OK\r\n'],
                 'AT+GCAP\r': ['+GCAP: +CGSM,+DS,+W\r\n', 'OK\r\n'],
                 'AT+CNMI=2,1,0,2\r': ['ERROR\r\n'], # not supported
                 'AT+CVHU=0\r': ['OK\r\n'],
                 'AT+CPIN?\r': ['+CPIN: READY\r\n', 'OK\r\n']}
        self.commandsNoPinRequired = ['ATZ\r', 'ATE0\r', 'AT+CFUN?\r', 'AT+CFUN=1\r', 'AT+CMEE=1\r']    
    
    def __str__(self):
        return 'Nokia N79'  


modemClasses = [HuaweiK3715, HuaweiE1752, WavecomMultiband900E1800, QualcommM6280, ZteK3565Z, NokiaN79]


def createModems():
    return [modem() for modem in modemClasses]
