import contextlib as _contextlib

try:
    import msvcrt as _msvcrt

    # Length 0 sequences, length 1 sequences...
    _ESCAPE_SEQUENCES = [frozenset(("\x00", "\xe0"))]

    _next_input = _msvcrt.getwch

    _set_terminal_raw = _contextlib.nullcontext

    _input_ready = _msvcrt.kbhit

except ImportError:  # Unix
    import sys as _sys, tty as _tty, termios as _termios, \
        select as _select, functools as _functools

    # Length 0 sequences, length 1 sequences...
    _ESCAPE_SEQUENCES = [
        frozenset(("\x1b",)),
        frozenset(("\x1b\x5b", "\x1b\x4f"))]

    @_contextlib.contextmanager
    def _set_terminal_raw():
        fd = _sys.stdin.fileno()
        old_settings = _termios.tcgetattr(fd)
        try:
            _tty.setraw(_sys.stdin.fileno())
            yield
        finally:
            _termios.tcsetattr(fd, _termios.TCSADRAIN, old_settings)

    _next_input = _functools.partial(_sys.stdin.read, 1)

    def _input_ready():
        return _select.select([_sys.stdin], [], [], 0) == ([_sys.stdin], [], [])

_MAX_ESCAPE_SEQUENCE_LENGTH = len(_ESCAPE_SEQUENCES)

def _get_keystroke():
    key = _next_input()
    while (len(key) <= _MAX_ESCAPE_SEQUENCE_LENGTH and
           key in _ESCAPE_SEQUENCES[len(key)-1]):
        key += _next_input()
    return key

def _flush():
    while _input_ready():
        _next_input()

def key_pressed(key: str = None, *, flush: bool = True) -> bool:
    """Return True if the specified key has been pressed

    Args:
        key: The key to check for. If None, any key will do.
        flush: If True (default), flush the input buffer after the key was found.
    
    Return:
        boolean stating whether a key was pressed.
    """
    with _set_terminal_raw():
        if key is None:
            if not _input_ready():
                return False
            if flush:
                _flush()
            return True

        while _input_ready():
            keystroke = _get_keystroke()
            if keystroke == key:
                if flush:
                    _flush()
                return True
        return False

def print_key() -> None:
    """Print the key that was pressed
    
    Useful for debugging and figuring out keys.
    """
    with _set_terminal_raw():
        _flush()
        print("\\x" + "\\x".join(map("{:02x}".format, map(ord, _get_keystroke()))))

def wait_key(key=None, *, pre_flush=False, post_flush=True) -> str:
    """Wait for a specific key to be pressed.

    Args:
        key: The key to check for. If None, any key will do.
        pre_flush: If True, flush the input buffer before waiting for input.
        Useful in case you wish to ignore previously pressed keys.
        post_flush: If True (default), flush the input buffer after the key was
        found. Useful for ignoring multiple key-presses.
    
    Returns:
        The key that was pressed.
    """
    with _set_terminal_raw():
        if pre_flush:
            _flush()

        if key is None:
            key = _get_keystroke()
            if post_flush:
                _flush()
            return key

        while _get_keystroke() != key:
            pass
        
        if post_flush:
            _flush()

        return key