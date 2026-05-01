# Built In Dependencies
import os
import numpy as np
import threading
import logging
import time

# Internal dependencies
from led_mon.patterns import letters_5_x_6, numerals
from led_mon import drawing
from led_mon.equalizer_files.visualize import Equalizer, has_inputmodule_control
from led_mon.shared_state import discover_led_devices

log = logging.getLogger(__name__)
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}

log_level = LOG_LEVELS[os.environ.get("LOG_LEVEL", "warning").lower()]
log.setLevel(log_level)

####  Monitor functions ####

equalizers = {}
equalizer_retry_after = {}
EQUALIZER_RETRY_BACKOFF_SEC = 30

def run_equalizer(_, grid, foreground_value, idx, **kwargs):
    external_filter = kwargs.get('external-filter', False)
    side = kwargs.get('side', None)
    if side not in ('left', 'right'):
        log.error(f"Unexpected equalizer side arg '{side}'. Expected 'left' or 'right'.")
        return

    if not has_inputmodule_control():
        log.error("inputmodule-control is not available on PATH. Skipping equalizer startup.")
        return

    if side in equalizers:
        return
    if time.time() < equalizer_retry_after.get(side, 0):
        return

    # device tuple => ('<location>', '<serial device>')
    devices: tuple[str, str] = discover_led_devices() or []
    channel = 0 if side == 'left' else 1
    if len(devices) <= channel:
        log.warning(f"Equalizer requested for {side} side, but matching LED device was not discovered.")
        return
    device = devices[channel]

    eq = Equalizer(device_location=device[0])
    equalizers[side] = eq

    def _run():
        try:
            ok = eq.run(channel=channel, external_filter=external_filter, device_name=device[1])
            if ok is False:
                equalizer_retry_after[side] = time.time() + EQUALIZER_RETRY_BACKOFF_SEC
        except Exception as e:
            log.error(f"Equalizer runtime error on {side} side: {e}")
            equalizer_retry_after[side] = time.time() + EQUALIZER_RETRY_BACKOFF_SEC
        finally:
            if equalizers.get(side) is eq:
                del equalizers[side]

    eq_thread = threading.Thread(target=_run, daemon=True)
    eq_thread.start()
    if len(equalizers) > 2:
        log.info(f"run_equalizer: Active equalizers: {len(equalizers)}")
    
def dispose_equalizer(**kwargs):
    side = kwargs.get('side', None)
    if side is None:
        log.error("dispose_equalizer called without required 'side' arg.")
        return

    eq = equalizers.pop(side, None)
    if eq is not None:
        eq.stop()
    equalizer_retry_after.pop(side, None)
    if len(equalizers) > 2:
        log.info(f"dispose_equalizer: Active equalizers: {len(equalizers)}")

#### Implement high-level drawing functions to be called by app functions below ####

draw_app = getattr(drawing, 'draw_app')

#### Implement low-level drawing functions ####
# These functions will be dynamically imported by drawing.py and called by their corresponding app function

# No implementations needed since the script draws continuoulsy on grid until dispose function is called
direct_draw_funcs = {
    "equalizer": {
        "fn": lambda *x: None,
        "border":lambda *x: None
    }
}

# Implement app functions that call your direct_draw functions
# These functions will be dynamically imported by led_system_monitor.py. They call the direct_draw_funcs
# defined above, providing additional capabilities that can be targeted to panel quadrants

app_funcs = [
    {
        "name": "equalizer",
        "fn": run_equalizer
    },
    {
        "name": "equalizer_dispose",
        "fn": dispose_equalizer
    }
]

# Provide id patterns that identify your apps
# These items will be dynamically imported by drawing.py

id_patterns = {
    "equalizer": np.concatenate((np.zeros((10,9)), letters_5_x_6["E"], np.zeros((2,9)), letters_5_x_6["Q"], np.zeros((10,9)))).T,
    "equalizer_paused": np.concatenate((np.zeros((5,9)), letters_5_x_6["E"], np.zeros((2,9)), letters_5_x_6["Q"],  np.zeros((3,9)), numerals["0"], np.zeros((5,9)))).T,

}
