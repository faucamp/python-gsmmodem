#!/usr/bin/env python

"""\
GSMTerm: A user-friendly terminal for interacting with a GSM modem

Note: The "Console" object was copied from pySerial's miniterm.py code

@author: Francois Aucamp <francois.aucamp@gmail.com>
"""

from __future__ import print_function
import os, sys, threading, time
import serial

from gsmmodem.serial_comms import SerialComms
from .trie import Trie
from gsmmodem.exceptions import TimeoutException

# first choose a platform dependant way to read single characters from the console 
global console

if os.name == 'nt':
    import msvcrt
    class Console(object):
        
        CURSOR_UP = '{0}{1}'.format(chr(0xe0), chr(0x48))
        CURSOR_DOWN = '{0}{1}'.format(chr(0xe0), chr(0x50))
        CURSOR_LEFT = '{0}{1}'.format(chr(0xe0), chr(0x4b))
        CURSOR_RIGHT = '{0}{1}'.format(chr(0xe0), chr(0x4d))
        #TODO: find out what this in windows:
        DELETE = ''
        HOME = ''
        END = ''
        
        def __init__(self):
            pass

        def setup(self):
            pass    # Do nothing for 'nt'

        def cleanup(self):
            pass    # Do nothing for 'nt'

        def getkey(self):
            while True:
                z = msvcrt.getch()
                if z == '\xe0': # extended (cursor keys, etc)
                    z += msvcrt.getch()
                    return z
                elif z == '\0':    # functions keys, ignore
                    msvcrt.getch()
                else:
                    if z == '\r':
                        return '\n'
                    return z

    console = Console()

elif os.name == 'posix':
    import termios, tty
    class Console(object):
        
        CURSOR_UP = '{0}{1}{2}'.format(chr(27), chr(91), chr(65))
        CURSOR_DOWN = '{0}{1}{2}'.format(chr(27), chr(91), chr(66))
        CURSOR_LEFT = '{0}{1}{2}'.format(chr(27), chr(91), chr(68))
        CURSOR_RIGHT = '{0}{1}{2}'.format(chr(27), chr(91), chr(67))
        DELETE = '{0}{1}{2}{3}'.format(chr(27), chr(91), chr(51), chr(126))
        HOME = '{0}{1}{2}'.format(chr(27), chr(79), chr(72))
        END = '{0}{1}{2}'.format(chr(27), chr(79), chr(70))
        
        def __init__(self):
            self.fd = sys.stdin.fileno()

        def setup(self):
            self.old = termios.tcgetattr(self.fd)
            new = termios.tcgetattr(self.fd)
            new[3] = new[3] & ~termios.ICANON & ~termios.ECHO & ~termios.ISIG
            new[6][termios.VMIN] = 1
            new[6][termios.VTIME] = 0
            termios.tcsetattr(self.fd, termios.TCSANOW, new)

#        def setup(self):
#            self.oldSettings = termios.tcgetattr(self.fd)            
#            tty.setraw(self.fd)            

        def getkey(self):
            c = os.read(self.fd, 4)
            #print (len(c))
            #for a in c:
            #    print('rx:',ord(a))           
            return c

        def cleanup(self):
            termios.tcsetattr(self.fd, termios.TCSAFLUSH, self.old)

    console = Console()

    def cleanup_console():
        console.cleanup()

    console.setup()
    sys.exitfunc = cleanup_console      # terminal modes have to be restored on exit...

else:
    raise NotImplementedError("Sorry no implementation for your platform (%s) available." % sys.platform)


class RawTerm(SerialComms):
    """ "Raw" terminal - basically just copies console input to serial, and prints out anything read """ 
    
    EXIT_CHARACTER = '\x1d'   # CTRL+]    
    WRITE_TERM = '\r' # Write terminator character
    
    def __init__(self, port, baudrate=9600):
        super(RawTerm, self).__init__(port, baudrate, notifyCallbackFunc=self._handleModemNotification)
        self.port = port
        self.baudrate = baudrate
        self.echo = True
    
    def _handleModemNotification(self, lines):
        for line in lines:
            print(line)
    
    def printStartMessage(self):
        print('\nRaw terminal connected to {0} at {1}bps.\nPress CTRL+] to exit.\n'.format(self.port, self.baudrate))
    
    def start(self):
        self.connect()
        # Start input thread
        self.alive = True
        self.inputThread = threading.Thread(target=self._inputLoop)
        self.inputThread.daemon = True
        self.inputThread.start()
        self.printStartMessage()   
        
    def stop(self):
        self.alive = False
        if threading.current_thread() != self.inputThread:
            self.inputThread.join()
        self.close()
    
    def _inputLoop(self):
        """ Loop and copy console->serial until EXIT_CHARCTER character is found. """
        try:
            while self.alive:
                try:
                    c = console.getkey()                    
                except KeyboardInterrupt:
                    print('kbint')
                    c = serial.to_bytes([3])
                if c == self.EXIT_CHARACTER: 
                    self.stop()
                elif c == '\n':
                    # Convert newline input into \r
                    self.serial.write(self.WRITE_TERM)
                    if self.echo:
                        # Locally just echo the real newline
                        sys.stdout.write(c)
                        sys.stdout.flush()
                else:
                    #print('writing: ', c)
                    self.serial.write(c)
                    if self.echo:
                        sys.stdout.write(c)
                        sys.stdout.flush()
        except:
            self.alive = False
            raise

class GsmTerm(RawTerm):
    """ User-friendly terminal for interacting with a GSM modem.
    
    Some features: tab-completion, help
    """
    
    PROMPT = 'GSM> '
    SMS_PROMPT = '> '
    EXIT_CHARACTER_2 = chr(4) # CTRL+D
    
    BACKSPACE_CHARACTER = chr(127)
    CTRL_Z_CHARACTER = chr(26) # Used when entering SMS messages with AT+CMGS
    ESC_CHARACTER = chr(27) # Used to cancel entering SMS messages with AT+CMGS
    
    RESET_SEQ = '\033[0m'
    COLOR_SEQ = '\033[1;{0}m'
    BOLD_SEQ = '\033[1m'
    
    # ANSI colour escapes
    COLOR_RED = COLOR_SEQ.format(30+1)
    COLOR_GREEN = COLOR_SEQ.format(30+2)
    COLOR_YELLOW = COLOR_SEQ.format(30+3)
    COLOR_BLUE = COLOR_SEQ.format(30+4)
    COLOR_MAGENTA = COLOR_SEQ.format(30+5)
    COLOR_WHITE = COLOR_SEQ.format(30+7)
    COLOR_CYAN = COLOR_SEQ.format(30+6)

    def __init__(self, port, baudrate=9600, useColor=True):
        super(GsmTerm, self).__init__(port, baudrate)
        self.inputBuffer = []
        self.history = []
        self.historyPos = 0
        self.useColor = useColor
        self.cursorPos = 0        
        if self.useColor:
            self.PROMPT = self._color(self.COLOR_GREEN, self.PROMPT)
            self.SMS_PROMPT = self._color(self.COLOR_GREEN, self.SMS_PROMPT)
        self._initAtCommandsTrie()
        # Flag that indicates whether the user is typing an SMS message's text
        self._typingSms = False

    def printStartMessage(self):
#        self.stdscr.addstr('GSMTerm started. Press CTRL+] to exit.')
        print('\nGSMTerm connected to {0} at {1}bps.\nPress CTRL+] or CTRL+D to exit.\n'.format(self.port, self.baudrate))
        self._refreshInputPrompt()

    def _color(self, color, msg):
        """ Converts a message to be printed to the user's terminal in red """
        if self.useColor:
            return '{0}{1}{2}'.format(color, msg, self.RESET_SEQ)
        else:
            return msg    

    def _boldFace(self, msg):
        """ Converts a message to be printed to the user's terminal in bold """
        return self._color(self.BOLD_SEQ, msg)

    def _handleModemNotification(self, lines):
        # Clear any input prompt
        self._removeInputPrompt()
        if self._typingSms:
            self.PROMPT = self._color(self.COLOR_CYAN, lines[0])
        if lines[-1] == 'ERROR':
            print(self._color(self.COLOR_RED, '\n'.join(lines)))
        else:
            print(self._color(self.COLOR_CYAN, '\n'.join(lines)))        
        self._refreshInputPrompt()
    
    def _addToHistory(self, command):
        self.history.append(command)
        if len(self.history) > 100:
            self.history = self.history[1:]
    
    def _inputLoop(self):
        """ Loop and copy console->serial until EXIT_CHARCTER character is found. """
        
        # Switch statement for handling "special" characters
        actionChars = {self.EXIT_CHARACTER: self._exit,
                       self.EXIT_CHARACTER_2: self._exit,
                        
                       console.CURSOR_LEFT: self._cursorLeft,
                       console.CURSOR_RIGHT: self._cursorRight,
                       console.CURSOR_UP: self._cursorUp,
                       console.CURSOR_DOWN: self._cursorDown,
                        
                       '\n': self._doConfirmInput,
                       '\t': self._doCommandCompletion,
                       
                       self.CTRL_Z_CHARACTER: self._handleCtrlZ,
                       self.ESC_CHARACTER: self._handleEsc,
                       
                       self.BACKSPACE_CHARACTER: self._handleBackspace,
                       console.DELETE: self._handleDelete,
                       console.HOME: self._handleHome,
                       console.END: self._handleEnd}

        try:
            while self.alive:
                try:
                    c = console.getkey()
                except KeyboardInterrupt:
                    c = serial.to_bytes([3])
                if c in actionChars:
                    # Handle character directly                    
                    actionChars[c]()
                elif len(c) == 1 and self._isPrintable(c):
                    self.inputBuffer.insert(self.cursorPos, c)
                    self.cursorPos += 1
                    self._refreshInputPrompt()
                #else:
                #    for a in c:
                #        print('GOT:',a,'(',ord(a),')')
        except:
            self.alive = False
            raise

    def _handleCtrlZ(self):
        """ Handler for CTRL+Z keypresses """
        if self._typingSms:
            self.serial.write(''.join(self.inputBuffer))
            self.serial.write(self.CTRL_Z_CHARACTER)
            self._typingSms = False
            self.inputBuffer = []
            self.cursorPos = 0
            sys.stdout.write('\n')
            self._refreshInputPrompt()
            
    def _handleEsc(self):
        """ Handler for CTRL+Z keypresses """
        if self._typingSms:
            self.serial.write(self.ESC_CHARACTER)
            self._typingSms = False
            self.inputBuffer = []
            self.cursorPos = 0

    def _exit(self):
        """ Shuts down the terminal (and app) """
        self._removeInputPrompt()
        print(self._color(self.COLOR_YELLOW, 'CLOSING TERMINAL...')) 
        self.stop()

    def _cursorLeft(self):
        """ Handles "cursor left" events """
        if self.cursorPos > 0:
            self.cursorPos -= 1
            sys.stdout.write(console.CURSOR_LEFT)
            sys.stdout.flush()

    def _cursorRight(self):
        """ Handles "cursor right" events """
        if self.cursorPos < len(self.inputBuffer):
            self.cursorPos += 1
            sys.stdout.write(console.CURSOR_RIGHT)
            sys.stdout.flush()

    def _cursorUp(self):
        """ Handles "cursor up" events """
        if self.historyPos > 0:
            self.historyPos -= 1
            clearLen = len(self.inputBuffer)
            self.inputBuffer = list(self.history[self.historyPos])
            self.cursorPos = len(self.inputBuffer)
            self._refreshInputPrompt(clearLen)

    def _cursorDown(self):
        """ Handles "cursor down" events """
        if self.historyPos < len(self.history)-1:
            clearLen = len(self.inputBuffer)
            self.historyPos += 1
            self.inputBuffer = list(self.history[self.historyPos])                        
            self.cursorPos = len(self.inputBuffer)
            self._refreshInputPrompt(clearLen)

    def _handleBackspace(self):
        """ Handles backspace characters """
        if self.cursorPos > 0:
            #print( 'cp:',self.cursorPos,'was:', self.inputBuffer)
            self.inputBuffer = self.inputBuffer[0:self.cursorPos-1] + self.inputBuffer[self.cursorPos:]
            self.cursorPos -= 1
            #print ('cp:', self.cursorPos,'is:', self.inputBuffer)                        
            self._refreshInputPrompt(len(self.inputBuffer)+1)

    def _handleDelete(self):
        """ Handles "delete" characters """
        if self.cursorPos < len(self.inputBuffer):
            self.inputBuffer = self.inputBuffer[0:self.cursorPos] + self.inputBuffer[self.cursorPos+1:]                        
            self._refreshInputPrompt(len(self.inputBuffer)+1)

    def _handleHome(self):
        """ Handles "home" character """
        self.cursorPos = 0
        self._refreshInputPrompt(len(self.inputBuffer))

    def _handleEnd(self):
        """ Handles "end" character """
        self.cursorPos = len(self.inputBuffer)
        self._refreshInputPrompt(len(self.inputBuffer))

    def _doConfirmInput(self):
        if self._typingSms:
            # SMS messages are confirmed with CTRL+Z or canceled with ESC
            inputStr = ''.join(self.inputBuffer[:self.cursorPos])
            self.serial.write(inputStr)
            self.inputBuffer = self.inputBuffer[self.cursorPos:]
            self.cursorPos = 0
            sys.stdout.write('\n')
            self._refreshInputPrompt()
            return       
        # Convert newline input into \r\n        
        if len(self.inputBuffer) > 0:
            inputStr = ''.join(self.inputBuffer).strip()
            self.inputBuffer = []
            self.cursorPos = 0
            inputStrLen = len(inputStr)            
            if len(inputStr) > 0:
                self._addToHistory(inputStr)
                self.historyPos = len(self.history)
            if inputStrLen > 2:
                if inputStr[0] == '?': # ?COMMAND
                    # Help requested with function                    
                    self._printCommandHelp(inputStr[1:])
                    return
                elif inputStr[-1] == inputStr[-2] == '?': # COMMAND??
                    # Help requested with function
                    cmd = inputStr[:-3 if inputStr[-3] == '=' else -2]                
                    self._printCommandHelp(cmd)
                    return
            inputStrLower = inputStr.lower()
            if inputStrLower.startswith('help'): # help COMMAND
                # Alternative help invocation
                self._printCommandHelp(inputStr[5:])
                return
            elif inputStrLower.startswith('ls'):                
                if inputStrLower == 'lscat':
                    sys.stdout.write('\n')         
                    for category in self.completion.categories:
                        sys.stdout.write('{0}\n'.format(category))
                    self._refreshInputPrompt(len(self.inputBuffer))
                    return
                elif inputStrLower == 'ls':
                    sys.stdout.write('\n')
                    for command in self.completion:
                        sys.stdout.write('{0:<8} - {1}\n'.format(command, self.completion[command][1]))
                    self._refreshInputPrompt(len(self.inputBuffer))
                    return                
                else:
                    ls = inputStrLower.split(' ', 1)                    
                    if len(ls) == 2:
                        category = ls[1].lower()
                        if category in [cat.lower() for cat in self.completion.categories]:
                            sys.stdout.write('\n')
                            for command in self.completion:
                                commandHelp = self.completion[command]
                                if category == commandHelp[0].lower():
                                    sys.stdout.write('{0:<8} - {1}\n'.format(command, commandHelp[1]))
                            self._refreshInputPrompt(len(self.inputBuffer))
                            return
            elif inputStrLower.startswith('load'):
                # Load a file containing AT commands to issue
                load = inputStr.split(' ', 1)                
                if len(load) == 2:                    
                    filename = load[1].strip()
                    try:
                        f = open(filename, 'r')
                    except IOError:
                        sys.stdout.write('\n{0}\n'.format(self._color(self.COLOR_RED, 'File not found: "{0}"'.format(filename))))
                        self._refreshInputPrompt(len(self.inputBuffer))                        
                    else:
                        atCommands = f.readlines()
                        f.close()                    
                        sys.stdout.write('\n')
                        for atCommand in atCommands: 
                            atCommand = atCommand.strip()
                            if len(atCommand) > 0 and atCommand[0] != '#':
                                self.inputBuffer = list(atCommand.strip())
                                self._refreshInputPrompt(len(self.inputBuffer))
                                self._doConfirmInput()
                                time.sleep(0.1)
                    return            
            if len(inputStr) > 0:
                if inputStrLower.startswith('at+cmgs='):
                    # Prepare for SMS input
                    self._typingSms = True
                    try:
                        sys.stdout.write('\n')
                        sys.stdout.flush()
                        response = self.write(inputStr + self.WRITE_TERM, waitForResponse=True, timeout=3, expectedResponseTermSeq='> ')
                    except TimeoutException:
                        self._typingSms = False                        
                    else:
                        sys.stdout.write(self._color(self.COLOR_YELLOW, 'Type your SMS message, and press CTRL+Z to send it or press ESC to cancel.\n'))                        
                        self.SMS_PROMPT = self._color(self.COLOR_GREEN, response[0])
                    self._refreshInputPrompt()                        
                    return
                self.serial.write(inputStr)
                self.serial.write(self.WRITE_TERM)
        # Locally just echo the real newline
        sys.stdout.write('\n')
        sys.stdout.flush()

    def _printGeneralHelp(self):
        sys.stdout.write(self._color(self.COLOR_WHITE, '\n\n== GSMTerm Help ==\n\n'))        
        sys.stdout.write('{0} Press the up & down arrow keys to move backwards or forwards through your command history.\n\n'.format(self._color(self.COLOR_YELLOW, 'Command History:')))
        sys.stdout.write('{0} Press the TAB key to provide command completion suggestions. Press the TAB key after a command is fully typed (with or without a "=" character) to quickly see its syntax.\n\n'.format(self._color(self.COLOR_YELLOW, 'Command Completion:')))
        sys.stdout.write('{0} Type a command, followed with two quesetion marks to access its documentation, e.g. "<COMMAND>??". Alternatively, precede the command with a question mark ("?<COMMAND>"), or type "help <COMMAND>".\n\n'.format(self._color(self.COLOR_YELLOW, 'Command Documentation:')))
        sys.stdout.write('{0} Type "ls [category]" to list the available AT commands known to GSMTerm for the given category (or all commands if no category is specified).\nType "lscat" to see a list of categories.\n\n'.format(self._color(self.COLOR_YELLOW, 'List Available Commands:')))
        sys.stdout.write('{0} Type "load <filename>" to load and execute a file containing AT commands, separated by newlines, e.g. "load ./myscript.txt".\n\n'.format(self._color(self.COLOR_YELLOW, 'Load Script:')))
        sys.stdout.write('To exit GSMTerm, press CTRL+] or CTRL+D.\n\n')
        self._refreshInputPrompt(len(self.inputBuffer))

    def _printCommandHelp(self, command=None):
        if command == None or len(command.strip()) == 0:
            # Print general help
            self._printGeneralHelp()
            return
        try:
            command = command.strip()
            commandHelp = self.completion[command.upper()]
        except KeyError:
            noHelp = True
        else:
            noHelp = commandHelp == None
        if noHelp:
            sys.stdout.write('\r No help available for: {0}\n'.format(self._color(self.COLOR_WHITE, command)))
        else:            
            sys.stdout.write('\n\n{0} ({1})\n\n'.format(self._color(self.COLOR_WHITE, commandHelp[1]), command))
            sys.stdout.write('{0} {1}\n'.format(self._color(self.COLOR_YELLOW, 'Category:'), commandHelp[0]))
            if len(commandHelp) == 2:
                sys.stdout.write('\nNo detailed help available for this command.\n\n')
                self._refreshInputPrompt(len(self.inputBuffer))
                return
            sys.stdout.write('{0} {1}\n'.format(self._color(self.COLOR_YELLOW, 'Description:'), commandHelp[4]))
            
            valuesIsEnum = len(commandHelp) >= 6            
            if valuesIsEnum: # "Values" is an enum of allowed values (not multiple variables); use custom label
                sys.stdout.write('{0} '.format(self._color(self.COLOR_YELLOW, commandHelp[5])))
            else:
                sys.stdout.write('{0} '.format(self._color(self.COLOR_YELLOW, 'Values:')))
            commandValues = commandHelp[2]
            syntax = [self._color(self.COLOR_WHITE, command)]
            if commandValues != None:
                if '+' in command or command.upper() in ['ATS0']:
                    syntax.append(self._color(self.COLOR_WHITE, '='))
                sys.stdout.write('\n')
                first = True
                for value, valueDesc in commandValues:
                    if first:                        
                        first = False
                    else:
                        syntax.append(',' if not valuesIsEnum else '|')
                    syntax.append(self._color(self.COLOR_MAGENTA, value))                    
                    sys.stdout.write(' {0} {1}\n'.format(self._color(self.COLOR_MAGENTA, value), valueDesc.replace('\n', '\n' + ' ' * (len(value) + 2)) if valueDesc != None else ''))
            else:
                sys.stdout.write('No parameters.\n')
            returnValues = commandHelp[3]
            if returnValues != None:
                sys.stdout.write('{0} '.format(self._color(self.COLOR_YELLOW, 'Response Values:')))
                sys.stdout.write('\n')
                for value, valueDesc in returnValues:
                    sys.stdout.write(' {0} {1}\n'.format(self._color(self.COLOR_CYAN, value), valueDesc.replace('\n', '\n' + ' ' * (len(value) + 2)) if valueDesc != None else ''))
            sys.stdout.write('{0}\n {1}\n\n'.format(self._color(self.COLOR_YELLOW, 'Command Syntax:'), ''.join(syntax)))
        self._refreshInputPrompt(len(self.inputBuffer))

    def _doCommandCompletion(self):
        """ Command-completion method """        
        prefix =  ''.join(self.inputBuffer).strip().upper()
        matches = self.completion.keys(prefix)
        matchLen = len(matches)        
        if matchLen == 0 and prefix[-1] == '=':
            try:                
                command = prefix[:-1]
            except KeyError:
                pass                        
            else:
                self.__printCommandSyntax(command)
        elif matchLen > 0:                        
            if matchLen == 1:
                if matches[0] == prefix:
                    # User has already entered command - show command syntax
                    self.__printCommandSyntax(prefix)
                else:
                    # Complete only possible command
                    self.inputBuffer = list(matches[0])
                    self.cursorPos = len(self.inputBuffer)
                    self._refreshInputPrompt(len(self.inputBuffer))
                return
            else:
                commonPrefix = self.completion.longestCommonPrefix(''.join(self.inputBuffer))
                self.inputBuffer = list(commonPrefix)
                self.cursorPos = len(self.inputBuffer)
                if matchLen > 20:
                    matches = matches[:20]
                    matches.append('... ({0} more)'.format(matchLen - 20))
            sys.stdout.write('\n')
            for match in matches:
                sys.stdout.write(' {0} '.format(match))
            sys.stdout.write('\n')
            sys.stdout.flush()
            self._refreshInputPrompt(len(self.inputBuffer))

    def __printCommandSyntax(self, command):
        """ Command-completion helper method: print command syntax """
        commandHelp = self.completion[command]
        if commandHelp != None and len(commandHelp) > 2:
            commandValues = commandHelp[2]
            #commandDefault = commandHelp[3]
            displayHelp = [self._color(self.COLOR_WHITE, command)]
            if commandValues != None:
                valuesIsEnum = len(commandHelp) >= 6
                if '+' in command or command.upper() in ['ATS0']:
                    displayHelp.append(self._color(self.COLOR_WHITE, '='))
                displayHelp.append(('|' if valuesIsEnum else ',').join([value[0] for value in commandValues]))
            sys.stdout.write('\r Syntax: {0}\n'.format(self._color(self.COLOR_WHITE, ''.join(displayHelp))))
            sys.stdout.flush()
            self._refreshInputPrompt(len(self.inputBuffer))

    def _isPrintable(self, char):
        return 33 <= ord(char) <= 126 or char.isspace()  

    def _refreshInputPrompt(self, clearLen=0):
        termPrompt = self.SMS_PROMPT if self._typingSms else self.PROMPT        
        endPoint = clearLen if clearLen > 0 else len(self.inputBuffer)
        sys.stdout.write('\r{0}{1}{2}{3}'.format(termPrompt, ''.join(self.inputBuffer), (clearLen - len(self.inputBuffer)) * ' ', console.CURSOR_LEFT * (endPoint - self.cursorPos)))
        sys.stdout.flush()

    def _removeInputPrompt(self):
        termPrompt = self.SMS_PROMPT if self._typingSms else self.PROMPT
        sys.stdout.write('\r{0}\r'.format(' ' * (len(termPrompt) + len(self.inputBuffer))))

    def _initAtCommandsTrie(self):
        self.completion = Trie()
        from .atcommands import ATCOMMANDS, CATEGORIES
        for command, help in ATCOMMANDS:
            if help != None:
                self.completion[command] = help
            else:
                self.completion[command] = None
        self.completion.categories = CATEGORIES

