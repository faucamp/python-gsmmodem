""" Contains monkey-patched equivalents for a few commonly-used Python 2.7-and-higher functions.
Used to provide backwards-compatibility with Python 2.6
"""
import sys
if sys.version_info[0] == 2 and sys.version_info[1] < 7:
    import threading
    
    # threading.Event.wait() always returns None in Python < 2.7 so we need to patch it
    if hasattr(threading, '_Event'): # threading.Event is a function that return threading._Event
        # This is heavily Python-implementation-specific, so patch where we can, otherwise leave it
        def wrapWait(func):
            def newWait(self, timeout=None):
                func(self, timeout)
                return self.is_set()            
            return newWait
        threading._Event.wait = wrapWait(threading._Event.wait)
    else:
        raise ImportError('Could not patch this version of Python 2.{0} for compatibility with python-gsmmodem.'.format(sys.version_info[1]))
if sys.version_info[0] == 2:
    str = str
else:
    str = lambda x: x