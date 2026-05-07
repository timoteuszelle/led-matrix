
# Built-in Dependencies
import subprocess
import time
import os
import re
import threading
from threading import Timer
import argparse
import logging
from enum import Enum
import shutil
import signal
import sys
from pathlib import Path
from led_mon import shared_state
from led_mon.drawing import DrawingThread

# Internal Dependencies
from led_mon.shared_state import discover_led_devices
from led_mon.patterns import id_patterns
import queue

# External Dependencies
import numpy as np
import sounddevice as sd
from scipy.signal import butter, sosfiltfilt
from pulsectl import Pulse


level = logging.WARNING
if os.getenv("LOG_LEVEL", "").lower() == "debug":
    level = logging.DEBUG
elif os.getenv("LOG_LEVEL", "").lower() == "error":
    level = logging.ERROR
elif os.getenv("LOG_LEVEL", "").lower() == "info":
    level = logging.INFO

logging.basicConfig(
    level=level,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

log = logging.getLogger(__name__)

class DeviceType(Enum):
    SOURCE = 1
    SINK = 2

SOURCE_CHECK_INTERVAL_SEC = 1
DEFAULT_ZERO_FRAME_NOTIFY_DELAY_SEC = 4.0
DEFAULT_SILENT_PULSE_AFTER_SEC = 12.0
DEFAULT_SILENT_PULSE_PERIOD_SEC = 3.8
DEFAULT_SILENT_PULSE_REVEAL_SEC = 5.0

# Configuration
SAMPLE_RATE = 48000
CHUNK_SIZE = 1024
UPDATE_RATE = 0.03 # 33 fps

# 9 frequency bands (If you use an EasyEffects filter, match the centers as closely as possible)
BAND_CENTERS = [31.5, 63, 125, 250, 500, 1000, 2000, 4000, 8000]  # Hz
Q = 1.414
INPUTMODULE_CONTROL_APP = shutil.which('inputmodule-control')
# Backward-compatible alias
MODUE_CONTROL_APP = INPUTMODULE_CONTROL_APP
PACTL_APP = shutil.which('pactl')

def has_inputmodule_control():
    return bool(INPUTMODULE_CONTROL_APP and Path(INPUTMODULE_CONTROL_APP).is_file())

# Pre-compute bandpass filters (used in python file mode)
filters = []
for fc in BAND_CENTERS:
    low = fc / Q
    high = fc * Q
    sos = butter(4, [low, high], btype='band', fs=SAMPLE_RATE, output='sos')
    filters.append(sos)

# Scale RMS to 0–34 range for --eq
def scale_rms(rms, min_db=-60, max_db=0):
    db = 20 * np.log10(rms + 1e-10)
    normalized = np.clip((db - min_db) / (max_db - min_db), 0, 1)
    return int(normalized * 34)

def clamp_positive_float(value, default):
    try:
        parsed = float(value)
        return parsed if parsed > 0 else float(default)
    except (TypeError, ValueError):
        return float(default)

def clamp_nonnegative_int(value, default):
    try:
        parsed = int(value)
        return parsed if parsed >= 0 else int(default)
    except (TypeError, ValueError):
        return int(default)

def resolve_input_stream_device(input_mode, input_device_hint=None):
    if input_device_hint:
        return input_device_hint
    if input_mode != 'microphone':
        return 'default'
    try:
        devices = sd.query_devices()
        input_devices = [d for d in devices if int(d.get('max_input_channels', 0)) > 0]
        non_monitor_devices = [
            d for d in input_devices
            if 'monitor' not in str(d.get('name', '')).lower()
        ]
        preferred = [
            d for d in non_monitor_devices
            if any(
                token in str(d.get('name', '')).lower()
                for token in ('mic', 'microphone', 'capture', 'input')
            )
        ]
        selected = preferred[0] if preferred else (non_monitor_devices[0] if non_monitor_devices else None)
        if selected:
            selected_name = selected.get('name')
            log.info(f"Using microphone input device: {selected_name}")
            return selected_name
    except Exception as e:
        log.warning(f"Could not auto-select microphone input device: {e}")
    return 'default'


# Lock for writing to LED matrix device
device_lock = threading.Lock()
_device_write_locks = {}
_device_write_locks_guard = threading.Lock()

def get_device_write_lock(device_name):
    with _device_write_locks_guard:
        lock = _device_write_locks.get(device_name)
        if lock is None:
            lock = threading.Lock()
            _device_write_locks[device_name] = lock
        return lock

def get_notification_pattern(source):
    if re.match(".*headphone.*|.*Audio_Expansion.*", source):
        # Wired headphones
        return 'zigzag'
    elif re.match(".*analog-stereo.*", source):
        # Speakers
        return 'all-on'
    elif re.match(".*bluez.*", source):
        # BlueTooth device
        return 'gradient'
    else:
        # Other
        return 'gradient'
    
def draw_source_change_cue(source):
    if not has_inputmodule_control():
        return
    pattern = get_notification_pattern(source)
    devices= discover_led_devices()
    # Only one instance will usually detect the source change, so it notifies both devices
    cmd_1 = [
            INPUTMODULE_CONTROL_APP,
            '--serial-dev', devices[0][1],
            'led-matrix',
            '--pattern',
            pattern
    ]
    if len(devices) > 1:
        cmd_2 = [
                INPUTMODULE_CONTROL_APP,
                '--serial-dev', devices[1][1],
                'led-matrix',
                '--pattern',
                pattern
        ]
    else:
        cmd_2 = None
    with device_lock:
        if not shared_state.id_key_press_active:
            for _ in range(3):
                subprocess.call(cmd_1, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if cmd_2:
                    subprocess.call(cmd_2, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    
def get_default_device(dev_type: DeviceType):
    with Pulse() as pulse_tmp:  # Temporary connection to query
        server_info = pulse_tmp.server_info()
        new_dev = \
            server_info.default_source_name if dev_type == DeviceType.SOURCE \
            else server_info.default_sink_name if dev_type == DeviceType.SINK \
            else None
        return new_dev
    
class Equalizer():
    
    def __init__(self, device_location):
        self.done = False
        self.device_name = None
        self.last_known_sink = None
        self.audio_buffer = np.zeros((CHUNK_SIZE, 2), dtype=np.float32)
        self.buffer_lock = threading.Lock()
        self.queue = queue.Queue(2)
        self.drawing_thread = DrawingThread(device_location, self.queue)
        self.drawing_thread.start()
        
    def stop(self):
        if not self.done:
            self.done = True
            try:
                self.queue.put_nowait(None)  # Sentinel to stop DrawingThread
            except queue.Full:
                try:
                    self.queue.get_nowait()
                except queue.Empty:
                    pass
                try:
                    self.queue.put_nowait(None)
                except queue.Full:
                    pass
        device_name = self.device_name if self.device_name else "<unknown>"
        log.debug(f"Stop equalizer on device {device_name}")

    def queue_frame(self, grid, animate=False):
        frame = (grid, animate)
        try:
            self.queue.put_nowait(frame)
        except queue.Full:
            try:
                self.queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self.queue.put_nowait(frame)
            except queue.Full:
                pass
    
    # Pipewire is supposed to automatically make the default source track the default sink's monitor, but the
    # capability is fragile and can sometimes be permanently broken. So we track sink changes and set the default
    # source to its monitor, to ensure continued data flow. We also draw a visual cue identifying the new source.
    def force_monitor_source(self):
        if not PACTL_APP:
            if not hasattr(self, '_pactl_missing_logged'):
                self._pactl_missing_logged = True
                log.warning("pactl was not found on PATH; skipping monitor-source auto-sync for equalizer.")
            return
        try:
            current_sink = get_default_device(DeviceType.SINK)
            if current_sink == self.last_known_sink or current_sink is None:
                if not self.done:
                    Timer(SOURCE_CHECK_INTERVAL_SEC, self.force_monitor_source).start()
                return

            expected_source = f"{current_sink}.monitor"
            current_source = get_default_device(DeviceType.SOURCE)

            if current_source != expected_source and current_source is not None:
                log.info(f"New sink detected: {current_sink}")
                subprocess.run(
                    [PACTL_APP, 'set-default-source', expected_source],
                    check=True,
                    capture_output=True,
                    text=True
                )
                #time.sleep(0.2)  # tiny settle time, may not be needed
                verified = get_default_device(DeviceType.SOURCE)
                if verified == expected_source:
                    log.info(f"Default source changed: {current_source} → {expected_source}")
                    draw_source_change_cue(expected_source)
                else:
                    log.warning(f"Failed to change default source: still {verified}")
                    
            self.last_known_sink = current_sink

        except subprocess.CalledProcessError as e:
            log.error(f"Failed to check/fix default source: {e}")
        except Exception as e:
            log.error(f"Unexpected error in force_monitor_source: {e}")
        if not self.done:
            Timer(SOURCE_CHECK_INTERVAL_SEC, self.force_monitor_source).start()
        
    def cleanup(self, sig=None, frame=None):
        self.stop()

    def audio_callback(self, indata, frames, time_info, status):
        if status:
            log.debug(f"Audio callback status ({self.device_name or 'unknown'}): {status}")
        with self.buffer_lock:
            self.audio_buffer = indata.copy()
        
    def draw_inverted_silence_pulse(self, elapsed_sec, pulse_period_sec, reveal_sec):
        pulse_period_sec = clamp_positive_float(pulse_period_sec, DEFAULT_SILENT_PULSE_PERIOD_SEC)
        reveal_sec = clamp_positive_float(reveal_sec, DEFAULT_SILENT_PULSE_REVEAL_SEC)
        base_foreground = max(1, int(shared_state.foreground_value))
        phase = (elapsed_sec / pulse_period_sec) % 1.0
        # Triangle wave avoids the visual "pause" at min/max that a sinusoid can create.
        wave = 1.0 - abs((2.0 * phase) - 1.0)

        x = np.arange(9, dtype=float)[:, None]
        y = np.arange(34, dtype=float)[None, :]
        center_x = 4.0
        center_y = 16.5
        norm_x = (x - center_x) / 4.0
        norm_y = (y - center_y) / 16.5
        radial = np.sqrt((norm_x ** 2) + (norm_y ** 2))
        angle = np.arctan2(norm_y, norm_x)

        # Warp radial distance into a star-like contour.
        star_scale = 1.0 + (0.28 * np.cos(4.0 * angle))
        star_radius = radial / np.clip(star_scale, 0.45, None)
        pulse_radius = 0.22 + (1.20 * wave)
        shell_width = 0.11
        shell = np.exp(-((star_radius - pulse_radius) ** 2) / (2.0 * (shell_width ** 2)))
        fill = np.clip((pulse_radius - star_radius) / max(pulse_radius, 1e-6), 0.0, 1.0)
        shape = np.clip((0.50 * fill) + (0.50 * shell), 0.0, 1.0)

        brightness = 0.30 + (0.70 * wave)
        grid = np.rint(np.clip(base_foreground * shape * brightness, 0, 255)).astype(int)
        grid = np.where(shape > 0.04, np.maximum(grid, 1), grid)

        reveal = np.clip(elapsed_sec / reveal_sec, 0.0, 1.0)
        paused_mask = (id_patterns['equalizer_paused'] > 0).astype(float)
        grid = np.rint(grid * (1.0 - (paused_mask * reveal))).astype(int)
        self.queue_frame(grid, False)

    def run(
        self,
        channel,
        external_filter,
        device_name,
        input_mode='playback',
        input_device=None,
        level_gain=1.0,
        noise_gate_level=0,
        silence_level_sum_threshold=0,
        zero_frame_notify_delay_sec=DEFAULT_ZERO_FRAME_NOTIFY_DELAY_SEC,
        silent_pulse_after_sec=DEFAULT_SILENT_PULSE_AFTER_SEC,
        silent_pulse_period_sec=DEFAULT_SILENT_PULSE_PERIOD_SEC,
        silent_pulse_reveal_sec=DEFAULT_SILENT_PULSE_REVEAL_SEC,
    ):
        self.device_name = device_name
        if not has_inputmodule_control():
            log.error("The executable file inputmodule-control was not found on the executable Path. The equalizer will not run.")
            self.stop()
            return False

        input_mode = str(input_mode or 'playback').strip().lower()
        if input_mode not in ('playback', 'microphone'):
            log.warning(f"Unknown equalizer input mode '{input_mode}', defaulting to playback.")
            input_mode = 'playback'

        zero_frame_notify_delay_sec = max(
            0.0,
            clamp_positive_float(zero_frame_notify_delay_sec, DEFAULT_ZERO_FRAME_NOTIFY_DELAY_SEC)
        )
        legacy_silent_pulse_after_sec = clamp_positive_float(silent_pulse_after_sec, DEFAULT_SILENT_PULSE_AFTER_SEC)
        silent_pulse_after_sec = min(zero_frame_notify_delay_sec, legacy_silent_pulse_after_sec)
        silent_pulse_period_sec = clamp_positive_float(silent_pulse_period_sec, DEFAULT_SILENT_PULSE_PERIOD_SEC)
        silent_pulse_reveal_sec = clamp_positive_float(silent_pulse_reveal_sec, DEFAULT_SILENT_PULSE_REVEAL_SEC)
        level_gain = max(0.1, clamp_positive_float(level_gain, 1.0))
        noise_gate_level = min(34, clamp_nonnegative_int(noise_gate_level, 0))
        silence_level_sum_threshold = clamp_nonnegative_int(silence_level_sum_threshold, 0)
        if input_mode == 'playback':
            activity_resume_threshold = max(18, silence_level_sum_threshold + 10)
            activity_resume_hold_sec = 0.45
        else:
            activity_resume_threshold = max(26, silence_level_sum_threshold + 12)
            activity_resume_hold_sec = 0.30

        if input_mode == 'playback':
            self.force_monitor_source()
        device_write_lock = get_device_write_lock(device_name)

        stream_device = resolve_input_stream_device(input_mode, input_device)
        stream_channels = 2
        try:
            if stream_device != 'default':
                device_info = sd.query_devices(stream_device, 'input')
                stream_channels = 2 if int(device_info.get('max_input_channels', 1)) >= 2 else 1
            elif input_mode == 'microphone':
                default_info = sd.query_devices(kind='input')
                stream_channels = 2 if int(default_info.get('max_input_channels', 1)) >= 2 else 1
        except Exception as e:
            log.warning(f"Could not query input channels for '{stream_device}', falling back to mono: {e}")
            stream_channels = 1

        def make_stream(selected_device, channels):
            return sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=channels,
                blocksize=CHUNK_SIZE,
                callback=self.audio_callback,
                device=selected_device
            )

        try:
            stream = make_stream(stream_device, stream_channels)
        except Exception as e:
            if stream_device != 'default':
                log.warning(f"Unable to open input device '{stream_device}', retrying with default input: {e}")
                stream_device = 'default'
                stream_channels = 2 if input_mode == 'playback' else 1
                stream = make_stream(stream_device, stream_channels)
            else:
                log.error(f"Unable to open equalizer input stream: {e}")
                self.stop()
                return False

        last_nonzero_frame_ts = time.monotonic()
        pulse_phase_anchor_ts = last_nonzero_frame_ts
        idle_mode = None
        idle_mode_started_ts = None
        active_candidate_started_ts = None
        
        def update_leds():
            nonlocal last_nonzero_frame_ts, pulse_phase_anchor_ts, idle_mode, idle_mode_started_ts, active_candidate_started_ts

            def render_silent_pulse(now):
                nonlocal idle_mode, idle_mode_started_ts
                if idle_mode != 'silent-pulse':
                    idle_mode = 'silent-pulse'
                    idle_mode_started_ts = now
                pulse_elapsed = now - pulse_phase_anchor_ts
                self.draw_inverted_silence_pulse(
                    elapsed_sec=pulse_elapsed,
                    pulse_period_sec=silent_pulse_period_sec,
                    reveal_sec=silent_pulse_reveal_sec,
                )

            while not self.done:
                with self.buffer_lock:
                    buffer_snapshot = self.audio_buffer.copy()
                if buffer_snapshot.ndim == 1:
                    chunk = buffer_snapshot
                else:
                    selected_channel = min(channel, max(0, buffer_snapshot.shape[1] - 1))
                    chunk = buffer_snapshot[:, selected_channel]

                levels = []

                if external_filter:
                    # EasyEffects mode: audio already EQ'd → measure energy in each band
                    for center_freq in BAND_CENTERS:
                        # Use wide-ish windows to capture EasyEffects' output without double-filtering
                        low = center_freq * 0.75
                        high = center_freq * 1.35
                        sos = butter(2, [low, high], btype='band', fs=SAMPLE_RATE, output='sos')
                        filtered = sosfiltfilt(sos, chunk)
                        rms = np.sqrt(np.mean(filtered ** 2))
                        level = scale_rms(rms)
                        levels.append(level)

                else:
                    # Python mode: apply our fixed narrow bandpass filters
                    for sos in filters:
                        filtered = sosfiltfilt(sos, chunk)
                        rms = np.sqrt(np.mean(filtered ** 2))
                        level = scale_rms(rms)
                        levels.append(level)
                boosted_levels = [min(34, int(round(level * level_gain))) for level in levels]
                levels = [0 if level < noise_gate_level else level for level in boosted_levels]

                cmd = [
                    INPUTMODULE_CONTROL_APP,
                    '--serial-dev', device_name,
                    'led-matrix',
                    '--eq',
                ] + [str(l) for l in levels]
                levels_sum = sum(levels)
                now = time.monotonic()
                if not shared_state.id_key_press_active:
                    if levels_sum > silence_level_sum_threshold:
                        if idle_mode == 'silent-pulse':
                            if levels_sum >= activity_resume_threshold:
                                if active_candidate_started_ts is None:
                                    active_candidate_started_ts = now
                                if now - active_candidate_started_ts >= activity_resume_hold_sec:
                                    last_nonzero_frame_ts = now
                                    idle_mode = None
                                    idle_mode_started_ts = None
                                    active_candidate_started_ts = None
                                    with device_write_lock:
                                        subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                else:
                                    render_silent_pulse(now)
                            else:
                                active_candidate_started_ts = None
                                render_silent_pulse(now)
                        else:
                            active_candidate_started_ts = None
                            last_nonzero_frame_ts = now
                            idle_mode = None
                            idle_mode_started_ts = None
                            with device_write_lock:
                                subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        active_candidate_started_ts = None
                        silence_sec = now - last_nonzero_frame_ts
                        if silence_sec >= silent_pulse_after_sec:
                            render_silent_pulse(now)

                time.sleep(UPDATE_RATE)

        update_thread = threading.Thread(target=update_leds, daemon=True)
        update_thread.start()

        with stream:
            log.debug(
                f"Running equalizer for {channel} channel on {device_name} "
                f"using {input_mode} input via '{stream_device}' "
                f"with {'EasyEffects' if external_filter else 'Python'} filter"
            )
            try:
                while not self.done:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                self.cleanup()
        return True
            
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="LED Matrix Audio Visualizer - Single Channel")
    parser.add_argument(
        '--channel',
        choices=['left', 'right'],
        required=True,
        help="Which channel and device to process: 'left' or 'right'"
    )
    parser.add_argument(
        '--use-easyeffects',
        action='store_true',
        help="Use EasyEffects upstream processing (skip Python bandpass filters)"
    )
    parser.add_argument(
        '--serial-dev-left',
        default='/dev/ttyACM0',   # ← customize these defaults or override via args
        help="Serial device for left channel"
    )
    parser.add_argument(
        '--serial-dev-right',
        default='/dev/ttyACM1',
        help="Serial device for right channel"
    )
    args = parser.parse_args()
    
    devices: tuple[str, str] = discover_led_devices()

    if args.channel == 'left':
        channel = 0  # left = column 0 in stereo buffer
        serial_dev = args.serial_dev_left
        location = devices[0][0] if len(devices) > 0 else None
    else:
        channel = 1  # right = column 1
        serial_dev = args.serial_dev_right
        location = devices[1][0] if len(devices) > 1 else None

    use_external_filter = args.use_easyeffects
    if location is not None:
        eq = Equalizer(location)
        eq.run(channel=channel, external_filter=use_external_filter, device_name=serial_dev)
        def stop_and_exit(sig=None, frame=None):
            eq.cleanup()
            sys.exit(0)
        signal.signal(signal.SIGINT, stop_and_exit )
        signal.signal(signal.SIGTERM, stop_and_exit)
    else:
        log.error(f"LED matrix device {serial_dev} not found. Please check your connections and try again.")