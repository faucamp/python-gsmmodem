#!/usr/bin/env python

"""\
GSMTerm: A user-friendly terminal for interacting with a GSM modem

Note: The "Console" object was copied from pySerial's miniterm.py code

@author: Francois Aucamp <francois.aucamp@gmail.com>
"""

from __future__ import print_function
import os, sys, threading
import serial

from gsmmodem.serial_comms import SerialComms

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
    
    def __init__(self, port, baudrate=9600):
        super(RawTerm, self).__init__(port, baudrate, notifyCallbackFunc=self._handleModemNotification)
        self.port = port
        self.baudrate = baudrate
        self.echo = True
    
    def _handleModemNotification(self, line):
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
                    # Convert newline input into \r\n
                    self.serial.write(self.EOL_SEQ)
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
    EXIT_CHARACTER_2 = chr(4) # CTRL+D
    
    BACKSPACE_CHARACTER = chr(127)
    
    RESET_SEQ = '\033[0m'
    COLOR_SEQ = '\033[1;{0}m'
    BOLD_SEQ = '\033[1m'
    
    # ANSI colour escapes
    COLOR_RED = COLOR_SEQ.format(30+1)
    COLOR_GREEN = COLOR_SEQ.format(30+2)
    COLOR_YELLOW = COLOR_SEQ.format(30+3)
    COLOR_BLUE = COLOR_SEQ.format(30+4)
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
        
    def _handleModemNotification(self, line):
        # Clear any input prompt
        self._removeInputPrompt()
        if line == 'ERROR':
            print(self._color(self.COLOR_RED, line))
        else:
            print(self._color(self.COLOR_CYAN, line))
        self._refreshInputPrompt()
        
    def _handleResponse(self, lines):
        # Clear any input prompt
        self._removeInputPrompt()
        if line[-1] == 'ERROR':
            lines(self._color(self.COLOR_RED, lines))
        else:
            print(self._color(self.COLOR_CYAN, lines))
        self._refreshInputPrompt()
    
    def _addToHistory(self, command):
        self.history.append(command)
        if len(self.history) > 100:
            self.history = self.history[1:]
    
    def _inputLoop(self):
        """ Loop and copy console->serial until EXIT_CHARCTER character is found. """
        try:
            while self.alive:
                try:
                    c = console.getkey()
                except KeyboardInterrupt:
                    c = serial.to_bytes([3])
                if c == self.EXIT_CHARACTER or c == self.EXIT_CHARACTER_2:
                    self._removeInputPrompt()
                    print(self._color(self.COLOR_YELLOW, 'CLOSING TERMINAL...')) 
                    self.stop()                
                elif c == console.CURSOR_LEFT:
                    if self.cursorPos > 0:
                        self.cursorPos -= 1
                        sys.stdout.write(c)
                        sys.stdout.flush()
                elif c == console.CURSOR_RIGHT:
                    if self.cursorPos < len(self.inputBuffer):
                        self.cursorPos += 1
                        sys.stdout.write(c)
                        sys.stdout.flush()
                elif c == console.CURSOR_UP:
                    if self.historyPos > 0:
                        self.historyPos -= 1
                        clearLen = len(self.inputBuffer)
                        self.inputBuffer = list(self.history[self.historyPos])
                        self.cursorPos = len(self.inputBuffer)
                        self._refreshInputPrompt(clearLen)
                elif c == console.CURSOR_DOWN:
                    if self.historyPos < len(self.history)-1:
                        clearLen = len(self.inputBuffer)
                        self.historyPos += 1
                        self.inputBuffer = list(self.history[self.historyPos])                        
                        self.cursorPos = len(self.inputBuffer)
                        self._refreshInputPrompt(clearLen)
                elif c == '\n':
                    # Convert newline input into \r\n
                    if len(self.inputBuffer) > 0:
                        inputStr = ''.join(self.inputBuffer).strip()
                        self.inputBuffer = []
                        self.cursorPos = 0
                        if len(inputStr) > 0:
                            self.serial.write(inputStr)
                            self.serial.write(self.EOL_SEQ)                    
                            self._addToHistory(inputStr)
                            self.historyPos = len(self.history)                    
                    # Locally just echo the real newline
                    sys.stdout.write(c)
                    sys.stdout.flush()                    
                    
                elif c == self.BACKSPACE_CHARACTER:
                    if self.cursorPos > 0:
                        #print( 'cp:',self.cursorPos,'was:', self.inputBuffer)
                        self.inputBuffer = self.inputBuffer[0:self.cursorPos-1] + self.inputBuffer[self.cursorPos:]
                        self.cursorPos -= 1
                        #print ('cp:', self.cursorPos,'is:', self.inputBuffer)                        
                        self._refreshInputPrompt(len(self.inputBuffer)+1)
                elif c == console.DELETE:
                    if self.cursorPos < len(self.inputBuffer):
                        #print( 'cp:',self.cursorPos,'was:', self.inputBuffer)
                        self.inputBuffer = self.inputBuffer[0:self.cursorPos] + self.inputBuffer[self.cursorPos+1:]                        
                        #print ('cp:', self.cursorPos,'is:', self.inputBuffer)
                        self._refreshInputPrompt(len(self.inputBuffer)+1)
                elif len(c) == 1 and self._isPrintable(c):
                    self.inputBuffer.insert(self.cursorPos, c)
                    self.cursorPos += 1
                    self._refreshInputPrompt()
                else:
                    for a in c:
                        print('GOT:',a,'(',ord(a),')')
        except:
            self.alive = False
            raise
    
    def _isPrintable(self, char):
        return 33 <= ord(char) <= 126 or char.isspace()  
        
    def _refreshInputPrompt(self, clearLen=0):        
        endPoint = clearLen if clearLen > 0 else len(self.inputBuffer)
        sys.stdout.write('\r{0}{1}{2}{3}'.format(self.PROMPT, ''.join(self.inputBuffer), (clearLen - len(self.inputBuffer)) * ' ', console.CURSOR_LEFT * (endPoint - self.cursorPos)))
        sys.stdout.flush()
    
    def _removeInputPrompt(self):
        sys.stdout.write('\r{0}\r'.format(' ' * (len(self.PROMPT) + len(self.inputBuffer))))
    
#    def start(self):    
#        self.stdscr = curses.initscr()
#        curses.noecho()
#        curses.cbreak()
#        self.stdscr.keypad(1)
#        curses.start_color()
#        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)        
#        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
#        curses.init_pair(3, curses.COLOR_BLUE, curses.COLOR_BLACK)
#        super(GsmTerm, self).start()        
    
#    def stop(self):
#        curses.nocbreak();
#        self.stdscr.keypad(0)
#        curses.echo()
#        curses.endwin()
#        super(GsmTerm, self).stop()
        
    
 

    
    
#    def _inputLoop(self):
#        """ Loop and copy console->serial until EXIT_CHARCTER character is found. """
#        try:
#            while self.alive:
#                d = self.stdscr.getch()
                
                #if d == 
                
#                c = chr(d)
#                self.stdscr.addstr('{0}:{1}\n'.format(d,c), curses.color_pair(3))
#                if c == self.EXIT_CHARACTER:
#                    self.stop()
#                elif c == '\n':
                    # Convert newline input into \r\n
#                    self.serial.write(self.EOL_SEQ)
#                    if self.echo:
                        # Locally just echo the real newline
#                        self.stdscr.addstr(c, )
#                        sys.stdout.flush()
#                else:
                    #print('writing: ', c)
                    #self.
#                    self.serial.write(c)
#                    if self.echo:
#                        self.stdscr.addstr(c)
#                        sys.stdout.flush()
#        except:
#            self.alive = False
#            raise





