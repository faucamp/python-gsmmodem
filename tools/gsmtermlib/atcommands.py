
CATEGORIES = ('General', 'Call Control', 'Network Service', 'Security', 'Phonebook', 'SMS', 'Supplementary Services', 'Data', 'Fax', 'Fax Class 2', 'V24-V25', 'Specific')

c = CATEGORIES

# Format: (COMMAND, (CATEGORY, NAME, VALUES, DEFAULT, DESCRIPTION))
ATCOMMANDS = (
# General
('AT+CGMI', (c[0], 'Manufacturer Identification', None, None, 'Displays the manufacturer identification.')),
('AT+CGMM', (c[0], 'Request Model Identification', None, None, 'Displays the supported frequency bands. With multi-band products the response may be a combination of different bands.')),
('AT+CGMR', (c[0], 'Request Revision Identification', None, None, 'Displays the revised software version.')),
('AT+CGSN', (c[0], 'Product Serial Number', None, None, 'Allows the user application to get the IMEI (International Mobile Equipment Identity, 15-digit number) of the product.')),
('AT+CSCS', (c[0], 'Select TE Character Set', (('<Character Set>', """GSM - GSM default alphabet (default value).
PCCP437 - PC character set code page 437.
CUSTOM - User defined character set (cf. +WCCS command).
HEX - Hexadecimal mode. No character set used; the user can read or write hexadecimal values."""),), None, 'Informs the ME which character set is used by the TE. The ME can convert each character of \
entered or displayed strings. This is used to send, read or write short messages. See also +WPCS for the phonebooks\' character sets.')),
('AT+WPCS', (c[0], 'Phonebook Character Set', (('<Character Set>', """TRANSPARENT - Transparent mode. The strings are displayed and entered as they are stored in SIM or in ME.
CUSTOM - User defined character set (cf. +WCCS command).
HEX - Hexadecimal mode. No character set used; the user can read or write hexadecimal values."""),), None, 'Informs the ME which character set is used by the TE for the phonebooks. The ME can convert\
each character of entered or displayed strings. This is used to read or write phonebook entries.\
See also +CSCS for the short messages character sets.')),
('AT+CIMI', (c[0], 'Request IMSI', None, None,  'Reads and identifies the IMSI (International Mobile Subscriber Identity) of the SIM card. The PIN may need to be entered before reading the IMSI')),
('AT+CCID', (c[0], 'Card Identification', None, None,  'Orders the product to read the EF-CCID file on the SIM card.')),
('AT+GCAP', (c[0], 'Capabilities List', None, None,  'Displays the complete list of capabilities.')),
('A/', (c[0], 'Repeat Last Command', None, None,  'Repeats the previous command. Only the A/ command itself cannot be repeated.')),
('AT+CPOF', (c[0], 'Power Off', None, None,  'Stops the GSM software stack as well as the hardware layer. The AT+CFUN=0 command is equivalent to +CPOF.')),
('AT+CFUN', (c[0], 'Set Phone Functionality', (('<functionality level>', """0: Set minimum functionality; IMSI detach procedure
1: Set the full functionality mode with a complete software reset"""),), None,  "Selects the mobile station's level of functionality. When the application wants to stop the \
product with a power off, or if the application wants to force the product to execute an IMSI \
DETACH procedure, then it must send: AT+CFUN=0 (equivalent to AT+CPOF). This command \
executes an IMSI DETACH and makes a backup copy of some internal parameters in SIM and \
in EEPROM. The SIM card cannot then be accessed. If the mobile equipment is not powered \
off by the application after this command has been sent, a re-start command (AT+CFUN=1) will \
have to issued to restart the whole GSM registration process. If the mobile equipment is turned \
off after this command, then a power on will automatically restart the whole GSM process. The \
AT+CFUN=1 command restarts the entire GSM stack and GSM functionality: a complete \
software reset is performed. All parameters are reset to their previous values if AT&W was not \
used. If you write entries in the phonebook (+CPBW) and then reset the product directly \
(AT+CFUN=1, with no previous AT+CFUN=0 command), some entries may not be written (the \
SIM task does not have enough time to write entries in the SIM card). In addition, the OK \
response will be sent at the last baud rate defined by the +IPR command. With the \
autobauding mode the response can be at a different baud rate, it is therefore preferable to \
save the defined baud rate with AT&W before directly sending the AT+CFUN=1 command.")),
('AT+CPAS', (c[0], 'Phone Activity Status', None, None,  """Returns the activity status of the mobile equipment.
Response is: +CPAS: <pas>
where <pas> is:
 0 ready (allow commands from TA/TE)
 1 unavailable (does not allow commands)
 2 unknown
 3 ringing (ringer is active)
 4 call in progress
 5 asleep (low functionality)""")),
('AT+CMEE', (c[0], 'Report Mobile Equipment Errors', (('<error reporting flag>', """0: Disable ME error reports; use only ERROR
1: Enable +CME ERROR: <xxx> or +CMS ERROR: <xxx>
2: Enable error result codes with verbose (string) values"""),), None,  'Disables or enables the use of the "+CME ERROR: <xxx>" or "+CMS ERROR:<xxx>" result code instead of simply "ERROR".')),
('AT+CKPD', (c[0], 'Keypad Control', (('<keys>', 'Keyboard sequence; string of the following characters (0-9, *, #)'),), None,  'Emulates the ME keypad by sending each keystroke as a character in a <keys> string.\n\
If emulation fails, a +CME ERROR: <err> is returned. If emulation succeeds, the result \
depends on the GSM sequence activated.')),
('AT+CCLK', (c[0], 'Clock Management', (('<date and time string>', 'String format for date/time is "yy/MM/dd,hh:mm:ss"\nNote: Valid years are 98 (for 1998) to 97 (for 2097). The seconds field is not mandatory.'),), None,  'Sets or gets the current date and time of the ME real-time clock.')),
('AT+CALA', (c[0], 'Alarm Management', (('<date and time string>', 'String format for alarms: "yy/MM/dd,hh:mm:ss" (see +CCLK)\nNote: Seconds are taken into account.'), ('<index>', 'Offset in the alarm list, range 1 to 16')), None,  'Sets the alarm date/time in the ME. The maximum number of alarms is 16.')),
# Call Control
('ATD', (c[1], 'Dial command', (('<nb>', 'Destination phone number'),), None,  "The ATD command sets a voice, data or fax call. As per GSM 02.30, the dial command also \
controls supplementary services.\n\
For a data or a fax call, the application sends the following ASCII string to the product (the bearer must \
be previously selected with the +CBST command):\n\
 ATD<nb> where <nb> is the destination phone number;\n\
For a voice call, the application sends the following ASCII string to the product: (the bearer may be \
selected previously, if not a default bearer is used).\n\
 ATD<nb>; where <nb> is the destination phone number.\n\
Please note that for an international number, the local international prefix does not need to be set \
(usually 00) but does need to be replaced by the '+' character.\n\
\nThere are other varieties of the ATD command available (using phonebook memory); please search online for help on these.")),
('ATH', (c[1], 'Hang-Up command',  (('<n>', '0: Ask for disconnection (default value)\n1: Ask for outgoing call disconnection'),), None,  'The ATH (or ATH0) command disconnects the remote user. In the case of multiple calls, all calls are released \
(active, on-hold and waiting calls). The specific ATH1 command has been appended to disconnect the current \
outgoing call, only in dialing or alerting state (ie. ATH1 can be used only after the ATD command, and before \
its terminal response (OK, NO CARRIER, ...). It can be useful in the case of multiple calls.')),
('ATA', (c[1], 'Answer a Call', None, None, 'When the product receives a call, it sets the RingInd signal and sends the ASCII "RING" or "+CRING: \
<type>" string to the application (+CRING if the cellular result code +CRC is enabled). Then it waits for the \
application to accept the call with the ATA command.')),
('AT+CEER', (c[1], 'Extended Error Report', None, None,  'This command gives the cause of call release when the last call set up (originating or answering) failed.')),
('AT+VTD', (c[1], 'DTMF Signals - set tone duration', (('<v>', 'tone duration.\n*100 is the duration in ms. If < 4, tone duration is 300 ms; if n > 255, the value used is modulo 256.\nDefault value: 300 ms, that is <n> = 3.'),), None,  'The modem can send DTMF tones over the GSM network. This command is used \
to define tone duration (the default value is 300ms). To define this duration, the application uses:\n\
AT+VTD=<n> where <n>*100 gives the duration in ms. If n < 4, tone duration is 300 ms.\n\
See also: AT+VTS')),
('AT+VTS', (c[1], 'DTMF Signals - send tone', (('<Tone>', 'DTMF tone to transmit. Tone is in {0-9, *, #, A, B, C, D}'),), None, 'The modem can send DTMF tones over the GSM network. This command enables \
tones to be transmitted only when there is an active call.\nSee also: AT+VTD\n\n\
Example:\n\
To send tone sequence 13#, the application sends:\n\
AT+VTS=1;+VTS=3;+VTS=#')),
('ATDL', (c[1], 'Redial Last Telephone Number', None, None,  'This command redials the last number used in the ATD command. The last number dialed is displayed followed by ";" for voice calls only.')),
('AT%D', (c[1], 'Automatic Dialing with DTR', (('<n>', 'Enable or disables automatic message transmission or number dialing.\n\
Informs the product that the number is a voice rather than a fax or data number.\n\
0 Disables automatic DTR number dialing / message transmission.\n\
1; Enables automatic DTR dialing if DTR switches from OFF to ON; Dials the phone number in the first \
location of the ADN phonebook. Voice call.\n\
1 Activates automatic DTR dialing if DTR switches from OFF to ON; Dials the phone number in the first \
location of the ADN phonebook. Data or Fax call.\n\
2 Activates automatic DTR message transmission if DTR switches from OFF to ON.'),), None,  'This command enables and disables:\n\
- Automatic dialing of the phone number stored in the first location of the ADN phonebook,\n\
- Automatic sending of the short message (SMS) stored in the first location of the SIM.\n\
The number is dialed when DTR OFF switches ON. The short message is sent when DTR OFF switches ON.')),
('ATS0', (c[1], 'Automatic Answer', (('<value>', 'is the number of rings before automatic answer (3 characters padded with zeros)\n\
Range of values is 0 to 255'),), None,  'This S0 parameter determines and controls the modem automatic answering mode.')),
('AT+CICB', (c[1], 'Incoming Call Bearer', (('<mode>', '0: Data\n1: Fax\n2: Speech'),), None,  'This command sets the type of incoming calls when no incoming bearer is given (see +CSNS).\nNote: Setting the +CICB command affects the current value of +CSNS.')),
('AT+CSNS', (c[1], 'Single Numbering Scheme', (('<mode>', '0: Voice\n2: Fax\n4: Data'),), None,  'This command selects the bearer to be used when an MT single numbering scheme call is set up (see +CICB).\nNote: Setting the +CSNS command affects the current value of +CICB.')),
('AT+VGR', (c[1], 'Gain Control - Reception', (('<Rgain>', 'reception gain'),), None,  'This command is used by the application to tune the receive gain of the speaker.')),
('AT+VGT', (c[1], 'Gain Control - Transmission', (('<Tgain>', 'transmission gain'),), None,  'This command is used by the application to tune the transmit gain of the microphone.')),
('AT+CMUT', (c[1], 'Microphone Mute Control', (('<mode>', '0: microphone mute off (default)\n1: microphone mute on'),), None, 'This command mutes the microphone input on the device. This command is only allowed during a call.')),
('AT+CVHU', (c[1], 'Voice Hangup Control', (('<mode>', '0: "Drop DTR" ignored but OK response given. ATH disconnects.\n\
1: "Drop DTR" and ATH ignored but OK response given.\n\
2: "Drop DTR" behavior according to &D setting. ATH disconnects.'),), None, 'This command selects whether ATH or "drop DTR" causes a voice connection to be disconnected or not. Voice connection also includes alternating mode calls that are currently in voice mode.\n\
When <mode>=2, this command must be viewed in conjunction with the V.25ter command &D, or &D will be ignored')),
# Network Service
('AT+CSQ', (c[2], 'Signal Quality', None, (('<rssi>', '0: -113 dBm or less\n1: -111 dBm\n2 to 30: -109 to -53 dBm\n31: -51dBm or greater\n99: not known or not detectable'),
                                           ('<ber>', '0...7: as RXQUAL values in the table GSM 05.08')),
            'This command determines the received signal strength indication (<rssi>) and the channel bit error rate (<ber>) with or without a SIM card inserted')),
('AT+COPS', (c[2], 'Operator Selection', (('<mode>', '0: automatic (default value)\n1: manual\n2: deregistration; ME will be unregistered until <mode>=0 or 1 is selected.\n3: set only <format> (for read command AT+COPS?)\n4: manual / automatic (<oper> shall be present), if manual selection fails, automatic mode is entered.\n<format>: format of <oper> field'),
                                          ('<format>', '0: long alphanumeric format <oper>\n1: short alphanumeric format <oper>\n2: numeric <oper> (default value) <stat>: status of <oper>\n\n<stat>\n 0: unknown\n 1: available\n 2: current\n 3: forbidden'),
                                          ('<oper>', 'operator identifier (MCC/MNC in numeric format only for operator selection)\nThe long alphanumeric format can be up to 16 characters long. The short alphanumeric format can be up to 8 characters long.'),
                                         ), None, 'Select the Network Operator.')),
('AT+CREG', (c[2], 'Network Registration', (('<mode>', '0: Disable network registration unsolicited result code (default)\n1: Enable network registration code result code +CREG: <stat>\n2: Enable network registration and location information unsolicited result code +CREG: <stat>,<lac>,<ci> if there is a change of network cell.'),),
                                           (('<stat>', '0: not registered, ME is not currently searching for a new operator.\n\
1: registered, home network.\n2: not registered, ME currently searching for a new operator to register to.\n\
3: registration denied.\n4: unknown.\n5: registered, roaming.'),
                                            ('<lac>', 'string type; two byte location area code in hexadecimal format'),
                                            ('<ci>', 'string type; two byte cell ID in hexadecimal format')), 
             'This command is used by the application to ascertain the registration status of the device.')),
('AT+WOPN', (c[2], 'Read Operator Name')),
('AT+WOPN', (c[2], 'Selection of Preferred PLMN List')),
('AT+CPLS', (c[2], 'Selection of Preferred PLMN List')),
('AT+CPOL', (c[2], 'Preferred Operator List')),
('AT+COPN', (c[2], 'Read Operator Name', None, (('<NumOper>', 'the operator in numeric format'), ('<AlphaOper>', 'the operator in long alphanumeric format')), 'This command returns the list of all operator names (in numeric and alphanumeric format) stored in the module.')),
# Security
('AT+CPIN', (c[3], 'Enter PIN', (('<pin>', 'the personal identification number'), ('<puk>', 'the personal unblocking key needed to change the PIN; syntax: AT+CPIN=<puk>,<new pin>')), None, 'This command enters the ME passwords (CHV1 / CHV2 / PUK1 / PUK2, etc.), that are required before any ME functionality can be used.')),
('AT+CPIN2', (c[3], 'Enter PIN2', (('<pin2>', 'the personal identification number 2'), ('<puk2>', 'the personal unblocking key 2 needed to change the PIN 2; syntax: AT+CPIN=<puk2>,<new pin 2>')), None, 'This command validates the PIN2 code (CHV2) or the PUK2 code (UNBLOCK CHV2) and defines a new \
PIN2 code. Of course, the +CPIN command allows PIN2 or PUK2 codes to be validated, but only when the \
last command executed resulted in PIN2 authentication failure. PIN2 length is between 4 and 8 digits; PUK2 \
length is 8 digits only.')),
('AT+CPINC', (c[3], 'PIN Remaining Attempt Number', None, (('<n1>', 'attempts left for PIN1 (0 = blocked, 3 max)'),
                                                           ('<n2>', 'attempts left for PIN2 (0 = blocked, 3 max)'),
                                                           ('<k1>', 'attempts left for PUK1 (0 = blocked, 10 max)'),
                                                           ('<k2>', 'attempts left for PUK2 (0 = blocked, 10 max)')),
              'This command gets the number of valid attempts for PIN1 (CHV1), PIN2 (CHV2), PUK1 (UNBLOCK CHV1) and PUK2 (UNBLOCK CHV2) identifiers.')),
('AT+CLCK', (c[3], 'Call Barring')),
('AT+CPWD', (c[3], 'Change Password')),
# Phonebook
('AT+CPBS', (c[4], 'Select Phonebook Memory Storage', (('"SM"', 'ADN (SIM phonebook)'),
                                                       ('"FD"', 'FDN (SIM Fix Dialing, restricted phonebook)'),
                                                       ('"ON"', 'MSISDN (SIM own numbers)'),
                                                       ('"EN"', 'EN (SIM emergency number)'),
                                                       ('"LD"', 'LND (combined ME and SIM last dialing phonebook)'),
                                                       ('"MC"', 'MSD (ME missed calls list)'),
                                                       ('"ME"', 'ME (ME phonebook)'),
                                                       ('"MT"', 'MT (combined ME and SIM phonebook)'),
                                                       ('"RC"', 'LIC (ME received calls list)'),
                                                       ('"SN"', 'SDN (Services dialing phonebook)')),
             None, 'This command selects phonebook memory storage.', 'Available Phonebooks:')),
('AT+CPBR', (c[4], 'Read Phonebook Entries', (('<first_entry>', 'Location of phonebook entry or start of range of locations (if <last_entry> is specified) of the phonebook entries'),
                                              ('<last_entry>', 'End of range of locations of the phonebook entries')), None, 'This command returns phonebook entries for a range of locations from the current phonebook memory storage selected with +CPBS.')),
('AT+CPBF', (c[4], 'Find Phonebook Entries', (('<string>', 'Searched starting string (depends on the format of the data stored in the phonebooks'),), None, 'This command returns phonebook entries with alphanumeric fields starting with a given string. The \
+CPBF command can be used to display all phonebook entries sorted in alphabetical order. This command is not allowed for "LD", "RC", "MC", "SN" or "EN" phonebooks, which do not contain alphanumeric fields.')),
('AT+CPBW', (c[4], 'Write Phonebook Entry', (('<index>', 'Integer type value depending on the capacity of the phonebook memory'),
                                              ('<number>', 'Phone number in ASCII format'),
                                              ('<type>', 'TON/NPI (Type of address byte in integer format)'),
                                              ('text>', 'Text label/name of entry. String type')), None, 'This command writes a phonebook entry in location number <index> in the current phonebook memory storage.\n\
This command is not allowed for "EN", "LD", "MC", "RC", "MT", and "SN" phonebooks (they cannot be written).')),
('AT+CPBP', (c[4], 'Phonebook Phone Search')),
('AT+CPBN', (c[4], 'Move Action in Phonebook')),
('AT+CNUM', (c[4], 'Subscriber Number', None, (('<alphax>', 'optional alphanumeric string associated with <numberx>'),
                                               ('<numberx>', 'string type phone number with format as specified by <typex>'),
                                               ('<typex>', 'type of address byte in integer format')), 'This command returns the subscriber MSISDN(s). If the subscriber has different MSISDNs for different services, each MSISDN is returned in a separate line.')),
('AT+WAIP', (c[4], 'Avoid Phonebook Initialization')),
('AT+WDCP', (c[4], 'Delete Calls Phonebook')),
('AT+CSVM', (c[4], 'Set Voice Mail Number')),
# Short Messages (SMS)
('AT+CSMS', (c[5], 'Select Message Service', (('<service>', '0: SMS AT commands are compatible with GSM 07.05 Phase 2 version 4.7.0.\n\
1: SMS AT commands are compatible with GSM 07.05 Phase 2 + version'),), None, 'The supported services include originated (SMS-MO) and terminated short messages (SMS-MT) as well as Cell Broadcast Message (SMS-CB) services.')),
('AT+CNMA', (c[5], 'New Message Acknowledgment', (('<n>', '0: send RP-ACK without PDU (same as TEXT mode)\n\
1: send RP-ACK with optional PDU message\n2: send RP-ERROR with optional PDU message'),
                                                  ('<length>', 'Length of the PDU message')), None, 'This command allows reception of a new message routed directly to the TE to be acknowledged.\n\
In TEXT mode, only positive acknowledgement to the network (RP-ACK) is possible.\n\
In PDU mode, either positive (RP-ACK) or negative (RP-ERROR) acknowledgement to the network is possible.\n\
Acknowledgement with +CNMA is possible only if the +CSMS parameter is set to 1 (+CSMS=1) when a \
+CMT or +CDS indication is shown (see +CNMI command).\n\
If no acknowledgement occurs within the network timeout, an RP-ERROR is sent to the network. The <mt> \
and <ds> parameters of the +CNMI command are then reset to zero (do not show new message indication).')),
('AT+CPMS', (c[5], 'Preferred Message Storage', (('<mem1>', 'Memory used to list, read and delete messages. It can be:\n\
 "SM": SMS message storage in SIM (default)\n\
 "BM": CBM message storage (in volatile memory).\n\
 "SR": Status Report message storage (in SIM if the EF-SMR file exists, otherwise in the ME non volatile memory)\n\
       Note: "SR" ME non-volatile memory is cleared when another SIM card is inserted. It is kept, even after a reset, while the same SIM card is used.'),
                                                 ('<mem2>', 'Memory to be used to write and send messages\n "SM": SMS message storage in SIM (default)')),
             (('<used1>', 'Used memory 1'),('total1', 'Total memory 1'),('<used2>', 'Used memory 2'),('total2', 'Total memory 2')),
             'This command allows the message storage area to be selected (for reading, writing, etc).')),
('AT+CMGF', (c[5], 'Preferred Message Format', (('<mode>', '0: PDU mode\n1: Text mode'),), None, 'The message formats supported are text mode and PDU mode.')),
('AT+CSAS', (c[5], 'Save Settings')),
('AT+CRES', (c[5], 'Restore Settings')),
('AT+CNMI', (c[5], 'New Message Indication', (('<mode>', 'Controls the processing of unsolicited result codes. Values:\n\
0: Buffer unsolicited result codes in the TA. If TA result code buffer is full, indications can be buffered in \
some other place, or the oldest indications may be discarded and replaced with the new received indications\n\
1: Discard indication and reject new received message unsolicited result codes when TA-TE link is reserved. Otherwise forward them directly to the TE\n\
2: Buffer unsolicited result codes in the TA when TA-TE link is reserved and flush them to the TE after reservation. Otherwise forward them directly to the TE\n\
3: Forward unsolicited result codes directly to the TE. TA-TE link specific inband used to embed result codes and data when TA is in on-line data mode'),
                                              ('<mt>', 'Sets the result code indication routing for SM-DELIVERs. Default is 0. Values:\n\
0: No SMS-DELIVER indications are routed.\n\
1: SMS-DELIVERs are routed using unsolicited code: +CMTI: "SM",<index>\n\
2: SMS-DELIVERs (except class 2 messages) are routed using unsolicited code: +CMT: [<alpha>,]\
<length> <CR> <LF> <pdu> (PDU mode) or +CMT: <oa>,[<alpha>,] <scts> [,<tooa>, <fo>, <pid>, <dcs>,<sca>, <tosca>, <length>] <CR><LF><data> (text mode)\n\
3: Class 3 SMS-DELIVERs are routed directly using code in <mt>=2 ; Message of other classes result in indication <mt>=1'),
                                              ('<bm>', 'Set the rules for storing received CBMs (Cell Broadcast Message). Default is 0. Values:\n\
0: No CBM indications are routed to the TE. The CBMs are stored.\n\
1: The CBM is stored and an indication of the memory location is routed to the customer application using unsolicited result code: +CBMI: "BM", <index>\n\
2: New CBMs are routed directly to the TE using unsolicited result code. +CBM: <length><CR><LF><pdu> (PDU mode) or +CBM:<sn>,<mid>,<dcs>,<page>,<pages>(Text mode) <CR><LF> <data>\n\
3: Class 3 CBMs: as <bm>=2. Other classes CBMs: as <bm>=1.'),
                                              ('<ds>', 'for SMS-STATUS-REPORTs. Default is 0. Values:\n\
0: No SMS-STATUS-REPORTs are routed.\n\
1: SMS-STATUS-REPORTs are routed using unsolicited code: +CDS: <length> <CR> <LF> <pdu> (PDU\n\
mode) or +CDS: <fo>,<mr>, [<ra>] , [<tora>], <scts>,<dt>,<st> (Text mode)\n\
2: SMS-STATUS-REPORTs are stored and routed using the unsolicited result code: +CDSI: "SR",<index>'),
                                              ('<bfr>', 'Default is 0. Values:\n\
0: TA buffer of unsolicited result codes defined within this command is flushed to the TE when <mode> 1...3\
is entered (OK response shall be given before flushing the codes)\n\
1: TA buffer of unsolicited result codes defined within this command is cleared when <mode> 1...3 is entered.')),
             None, 'This command selects the procedure for message reception from the network.')),
('AT+CMGR', (c[5], 'Read Message', (('<index>', 'Location of message to read'),), None, 'This command allows the application to read stored messages. The messages are read from the memory selected by the +CPMS command.')),
('AT+CMGL', (c[5], 'List Message', (('<stat>', 'Status of messages in memory to list. Allowed values are:\n\
Text mode     PDU mode\n\
"REC UNREAD"  0\n\
"REC READ"    1\n\
"STO UNSENT"  2\n\
"STO SENT"    3\n\
"ALL"         4'),), None, 'This command allows the application to read stored messages, by indicating the type of the message to read. The messages are read from the memory selected by the +CPMS command.')),
('AT+CMGS', (c[5], 'Send Message', (('<da>', 'Destination Address (text mode) - message destination phone number'),), None, 'The <address> field is the address of the terminal to which the message is sent. To send the message, \
simply type, <ctrl-Z> character (ASCII 26). The text can contain all existing characters except <ctrl-Z> and \
<ESC> (ASCII 27). This command can be aborted using the <ESC> character when entering text. In PDU \
mode, only hexadecimal characters are used (\'0\'...\'9\',\'A\'...\'F\').')),
('AT+CMGW', (c[5], 'Write Message to Memory')),
('AT+CMSS', (c[5], 'Send Message from Storage', (('<index>', 'location of stored message'),
                                                 ('<da>', 'destination address'),
                                                 ('<toda>', 'type of destination address')),
                                                (('<mr>', 'message reference'),), 'This command sends a message stored at location value <index>.')),
('AT+CSMP', (c[5], 'Set Text Mode Parameters', (('<fo>', 'byte comprising 6 fields, RP, UDHI, SRR, VPFG, RD and MTI'),
                                                ('<vp>', 'validity period'),
                                                ('<pid>', 'used to indicate the higher layer protocol being used or indicates interworking with a certain type of \
telematic device. For example, 0x22 is for group 3 telefax, 0x24 is for voice telephone, 0x25 is for ERMES.'),
                                                ('<dcs>', 'used to determine the way the information is encoded.')), None, 'This command selects a value for <vp>, <pid>, and <dcs>.')),
('AT+CMGD', (c[5], 'Delete Message', (('<index>', 'Integer type values in the range of location numbers of SIM Message memory when the preferred message storage is "SM or "SR".'),
                                      ('<DelFlag>', '0: Delete message at location <index>.\n\
1: Delete All READ messages\n\
2: Delete All READ and SENT messages\n\
3: Delete All READ, SENT and UNSENT messages\n\
4: Delete All messages.')), None, 'This command deletes one or several messages from preferred message storage.')),
('AT+CSCA', (c[5], 'Service Center Address', (('<sca>', 'service center address'),), None, 'This command sets (or queries) the service center to which SMS messages must be sent.')),
('AT+CSCB', (c[5], 'Select Cell Broadcast Message Types', (('<mode>', '0 - CBM reception activated\n1 - CBM reception deactivated'), ('<mids>', 'message identifiers - indicates the type of message idenitfiers for which the ME should listen'), ('<dcss>', 'Supported Languages')), None, 'This command selects which types of CBMs are to be received by the ME.')),
('AT+WCBM', (c[5], 'Cell Broadcast Message Identifiers')),
('AT+WMSC', (c[5], 'Message Status Modification')),
('AT+WMGO', (c[5], 'Message Overwriting')),
('AT+WUSS', (c[5], 'Unchange SMS Status')),
# Supplementary Services
('AT+CCFC', (c[6], 'Call Forwarding')),
('AT+CCWA', (c[6], 'Call Waiting')),
('AT+CLIR', (c[6], 'Calling Line Identification Restriction', (('<n>', 'Sets the line ID restriction for outgoing calls. Values:\n\
0: Presentation indicator is used according to the subscription of the CLIR service\n\
1: CLIR invocation\n2: CLIR suppression'),), (('<m>', 'Shows the subscriber CLIR status in the network. Values:\n\
0: CLIR not provisioned\n1: CLIR provisioned in permanent mode\n2: Unknown (no network...)\n3: CLIR temporary mode presentation restricted\n4: CLIR temporary mode presentation allowed'),),
             'This command controls the Calling Line Identification restriction supplementary service.')),
('AT+CLIP', (c[6], 'Calling Line Identification Presentation',
             (('<n>', 'Parameter sets/shows the result code presentation in the TA. Values:\n0: Disable\n1: Enable'),),
             (('<m>', 'Parameter shows the subscriber CLIP service status in the network. Values:\n0: CLIP not provisioned\n1: CLIP provisioned\n2: Unknown (no network...)'),),
             'This command controls the calling line identification presentation supplementary service. When presentation \
of the CLI (Calling Line Identification) is enabled (and calling subscriber allows), +CLIP response is returned \
after every RING (or +CRING) result code.')),
('AT+COLP', (c[6], 'Connected Line Identification Presentation')),
('AT+CAOC', (c[6], 'Advice Of Charge')),
('AT+CAMM', (c[6], 'Accumulated Call Meter Maximum')),
('AT+CPUC', (c[6], 'Price Per Unit and Currency Table')),
('AT+CHLD', (c[6], 'Call Related Supplementary Services')),
('AT+CHLD', (c[6], 'Call Related Supplementary Services')),
('AT+CLCC', (c[6], 'List Current Calls', None, (('<idx>', 'integer type, call identification as described in GSM 02.30'),
                                                ('<dir>', '0: mobile originated (MO) call\n2: mobile terminated (MT) call'),
                                                ('<stat>', '0: active\n\
1: held\n\
2: dialing (MO call)\n\
3: alerting (MO call)\n\
4: incoming (MT call)\n\
5: waiting (MT call)'),
                                                ('<mode>', '0: voice\n\
1: data\n\
2: fax\n\
9: unknown'),
                                                ('<mpty>', '0: call is not one of multiparty (conference) call parties\n\
1: call is one of multiparty (conference) call parties'),
                                                ('<number>', 'string type phone number in format specified by <type>'),
                                                ('<type>', 'type of address byte in integer format'),
                                                ('<alpha>', 'optional string type alphanumeric representation of <number> corresponding to the entry found in phonebook')),
             'This command returns a list of current calls.')),
('AT+CSSN', (c[6], 'Supplementary Service Notifications')),
('AT+CUSD', (c[6], 'Unstructured Supplementary Service Data', (('<n>', '0: Disable the result code presentation\n\
1: Enable the result code presentation\n\
2: Cancel session (not applicable to read command response)'),
                                                               ('<str>', 'network string, converted in the selected character set'),
                                                               ('<dcs>', 'the data coding scheme received (TSM TS 03.38)')),
             (('<m>', '0: no further user action required (network initiated USSD-Notify, or no further information needed after mobile initiated operation)\n\
1: further user action required (network initiated USSD-Request, or further information needed after mobile initiated operation)\n\
2: USSD terminated by network\n\
4: Operation not supported'),),
             'The USSD supplementary service is described in GSM 02.90. It is based on sequences of digits which may \
be entered by a mobile user with a handset. A sequence entered is sent to the network which replies with an \
alphanumerical string, for display only, or for display plus request for the next sequence.\n\
This command is used to:\n\
- Enable or disable the CUSD indication sent to the application by the product when an incoming USSD is received\n\
- Send and receive USSD strings')),
('AT+CCUG', (c[6], 'Closed User Group')),
# Data
('AT+CBST', (c[7], 'Bearer Type Selection')),
('AT+FCLASS', (c[7], 'Select Mode', (('<n>', '0: Data\n1: Fax class 1\n2: Fax class 2'),), None, 'This command puts the modem into a particular operating mode (data or fax).')),
('AT+CR', (c[7], 'Service Reporting Control')),
('AT+CRC', (c[7], 'Cellular Result Dodes', (('<mode>', '0: Disable extended reports\n1: Enable extended reports'),), None, 'This command shows more detailed ring information for an incoming call (voice or data). Instead of the string \
"RING", an extended string is used to indicate which type of call is ringing (e.g. +CRING: VOICE).\n\
These extended indications are:\n\
+CRING: ASYNC     for asynchronous transparent\n\
+CRING: REL ASYNC for asynchronous non-transparent\n\
+CRING: VOICE     for normal speech.\n\
+CRING: FAX       for fax calls')),
('AT+ILRR', (c[7], 'DTE-DCE Local Rate Reporting')),
('AT+CRLP', (c[7], 'Radio Link Protocol Parameters')),
('AT+DOPT', (c[7], 'Radio Link Protocol Parameters')),
# Fax
('AT+FTM', (c[8], 'Transmit Speed')),
('AT+FRM', (c[8], 'Receive Speed')),
('AT+FTH', (c[8], 'HDLC Transmit Speed')),
('AT+FRH', (c[8], 'HDLC Receive Speed')),
('AT+FTS', (c[8], 'Stop Transmission and Wait')),
('AT+FRS', (c[8], 'Receive Silence')),
# Fax Class 2
('AT+FDT', (c[9], 'Transmit Data')),
('AT+FDR', (c[9], 'Receive Data')),
('AT+FET', (c[9], 'Transmit Page Punctuation')),
('AT+FPTS', (c[9], 'Page Transfer Status Parameters')),
('AT+FK', (c[9], 'Terminate Session')),
('AT+FBOR', (c[9], 'Page Transfer Bit Order')),
('AT+FBUF', (c[9], 'Buffer Size Report')),
('AT+FCQ', (c[9], 'Copy Quality Checking')),
('AT+FCR', (c[9], 'Capability to Receive')),
('AT+FDIS', (c[9], 'Current Session Parameters')),
('AT+FDCC', (c[9], 'DCE Capabilities Parameters')),
('AT+FLID', (c[9], 'Local ID String')),
('AT+FPHCTO', (c[9], 'Page Transfer Timeout Parameter')),
# V24-V25
('AT+IPR', (c[10], 'Fixed DTE Rate', (('<value>', 'Baud rates that can be used by the DCE.\n0 enables autobauding on some modems.'),), None, 'This commands specifies the data rate at which the DCE will accept commands.')),
('AT+ICF', (c[10], 'DTE-DCE Character Framing', (('<format>', '0: Autodetect\n\
1: 8 Data 2 Stop\n\
   <parity> parameter is ignored\n\
2: 8 Data 1 Parity 1 Stop\n\
   If no <parity> provided, 3 is used by default as <parity> value\n\
3: 8 Data 1 Stop\n\
   <parity> parameter is ignored\n\
4: 7 Data 2 Stop\n\
   <parity> parameter is ignored\n\
5: 7 Data 1 Parity 1 Stop\n\
   If no <parity> provided, 3 is used by default as <parity> value\n\
6: 7 Data 1 Stop\n\
   <parity> parameter is ignored'),
                                                 ('<parity', '0: Odd\n1: Even\n2: Mark\n3: Space\n4: None')), None, 'This command determines the local serial port start-stop (asynchronous) character framing that the DCE uses.')),
('AT+IFC', (c[10], 'DTE-DCE Flow Control')),
('AT&C', (c[10], 'Set DCD Signal', (('<n>', '0: DCD always on\n1: DCD matches the state of the remote modem\'s data carrier'),), None, 'This commands controls the Data Carrier Detect (DCD) signal.')),
('AT&D', (c[10], 'Set DTR Signal', (('<n>', '0: The DTR signal is ignored\n1: Modem switches from data to command mode when DTR switches from ON to OFF\n2: Upon DTR switch from ON to OFF, the call is released'),), None, 'This commands controls the Data Terminal Ready (DTR) signal.')),
('AT&S', (c[10], 'Set DSR Signal', (('<n>', '0: DSR always on\n1: DSR off in command mode. DSR on in data mode.'),), None, 'This commands controls the Data Set Ready (DSR) signal.')),
('ATO', (c[10], 'Back to Online Mode', None, None, 'If a connection has been established and the ME is in command mode, this command allows you to return to online data mode.')),
('ATQ', (c[10], 'Result Code Suppression', (('<n>', '0: DCE transmit result codes\n1: Result codes are suppressed and not transmitted'),), None, 'This command determines whether the mobile equipment sends result codes or not.')),
('ATV', (c[10], 'DCE Response Format', (('<n>', '0: DCE transmits limited headers and trailers and numeric result codes\n1: DCE transmits full headers and trailers and verbose response text'),), None, 'This command determines the DCE response format, with or without header characters <CR><LF>. Result codes are provided as numeric or verbose.')),
('ATZ', (c[10], 'Default Configuration', None, None, 'This command restores the configuration profile. Any call is released')),
('AT&W', (c[10], 'Save Configuration', None, None, 'This command writes the active configuration to a non-volatile memory (EEPROM).')),
('AT&T', (c[10], 'Auto-Tests')),
('ATE', (c[10], 'Echo', (('<n>', '0: Characters are not echoed\n1: Characters are echoed'),), None, 'This command is used to determine whether the modem echoes characters received by an external application (DTE).')),
('AT&F', (c[10], 'Restore Factory Settings', (('<n>', '0: Restore factory settings'),), None, 'This command is used to restore the factory settings from EEPROM.')),
('AT&V', (c[10], 'Display Configuration', (('<n>', '0 Displays the modem configuration in RAM. Default value if no parameter provided.\n\
1: Displays the modem configuration in EEPROM.\n\
2: Displays the modem factory configuration.'),), None, 'This command is used to display the modem configuration.')),
('ATI', (c[10], 'Request Identification Information', (('<n>', '0: Displays manufacturer followed by model identification. Equivalent to +CGMI and +CGMM.\n\
3: Displays revision identification. Equivalent to +CGMR.\n\
4: Displays modem configuration in RAM. Equivalent to &V0.\n\
5: Displays modem configuration in EEPROM. Equivalent to &V1.\n\
6: Displays modem data features. Lists the supported data rates, data modes, and fax classes.\n\
7: Displays modem voice features.'),), None, 'This command causes the product to transmit one or more lines of specific information text.')),
('AT+WMUX', (c[10], 'Multiplexing Mode')),
# Specific AT Commands
('AT+CCED', (c[11], 'Cell Environment Description')),
('AT+WIND', (c[11], 'General Indications')),
('AT+ADC', (c[11], 'Analog Digital Converter Measurements')),
('AT+CMER', (c[11], 'Mobile Equipment Event Reporting')),
('AT+CIND', (c[11], 'Indicator Control')),
('AT+CMEC', (c[11], 'Mobile Equipment Control Mode')),
('AT+WLPR', (c[11], 'Read Language Preference')),
('AT+WLPW', (c[11], 'Write Language Preference')),
('AT+WIOR', (c[11], 'Read GPIO Value')),
('AT+WIOW', (c[11], 'Write GPIO Value')),
('AT+WIOM', (c[11], 'Input/Output Management')),
('AT+WAC', (c[11], 'Abort Command')),
('AT+WTONE', (c[11], 'Play Tone')),
('AT+WDTMF', (c[11], 'Play DTMF Tone')),
('AT+WDWL', (c[11], 'Downloading')),
('AT+WVR', (c[11], 'Voice Rate')),
('AT+WDR', (c[11], 'Data Rate')),
('AT+WSVG', (c[11], 'Select Voice Gain')),
('AT+WSTR', (c[11], 'Status Request')),
)