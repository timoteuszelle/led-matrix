# Framework 16 LED Matrix System Monitoring Application

This software is intended for use on a Framework 16 laptop with LED Matrix Panels installed. It's a clone of the [LED System Monitor](https://code.karsttech.com/jeremy/FW_LED_System_Monitor.git) project, with certain modifications and extensions applied.

## Capabilities
* Display system performance characteristics in real-time
  * CPU utilization
  * Battery charge level and plug status + memory utilization
  * Disk Input/Output rates
  * Network Upload/Download rates
  * Temperature sensor readings
  * Fan speeds
* Display any system monitoring app on any quadrant
  * Top or bottom of left or right panel
  * Specified via program arguments
* Display a "snapshot" from specified json file(s) on either or both panels. Continuous or periodic display is supported.
* Keyboard shortcut identifies apps running in each quadrant by displaying abbreviated name 
* Plugin framework supports simplified development of addiitonal LED Panel applications
* Automatic detection of left and right LED panels
## Capabilities added to the original implementation
 * Temp sensor and fan speed apps
 * Metrics apps configurable to any matrix quadrant
 * Plugin capability
 * Automatic device detection
 * Snapshot app
## Installation
* Install [PyEnv](https://github.com/pyenv/pyenv)  
* Any other python virtual environment package may be used. Commands below work with PyEnv.
```
cd led-matrix
pyenv install 3.11
pyenv virtualenv 3.11 3.11
pyenv activate
pip install -r requirements.txt
```
* If you want to run the code as a linux service, you need to install the python dependencies as the root user
* ```ic
  cd led-matrix
  sudo pip install -r requirements.txt
  ```
## Run
```
cd led-matrix
python led-sysyem-monitor.py [--help] [--top-left {cpu,net,disk,mem-bat,none,temp,fan}]
                             [--bottom-left {cpu,net,disk,mem-bat,none,temp,fan}]
                             [--top-right {cpu,net,disk,mem-bat,none,temp,fan}]
                             [--bottom-right {cpu,net,disk,mem-bat,none,temp,fan}]
                             [--left-snap LEFT_SNAP]
                             [--right-snap RIGHT_SNAP]
                             [--snapshot-path SNAPSHOT_PATH]
                             [--snapshot-interval SNAPSHOT_INTERVAL]
                             [--snapshot-duration SNAPSHOT_DURATION]
                             [--no-key-listener] [--disable-plugins]
python led-sysyem-monitor.py --help #For more verbose help info
```
## Run as a Linux service
```
cd led-matrix
./install_as_service.sh [...args] #program args to be applied when starting or restarting the service
sudo systemctl start|stop|restart|status fwledmonitor
```
## Keyboard Shortcut
* Alt+I: displays app names in each quadrant while keys are pressed
* Disable key listener with `--no-key-listener` program arg
* To use the key listener, the app must have read permission on the keyboard device (e.g /dev/input/event7). The service runs as root, and therefore has the required access. If you want toi use the key listener while running the app directly, you need to add your user account to the `input` group and ensure there is a group read permission on the keyboard device. **NB:** Consider the implications of this. Any program running as a user in the `input` group will be able to capture your keystrokes.
## Plugin Development
* Add a file in the `plugins` dir with a name that matches the blob pattern `*_plugin.py`
* See `temp_fan_plugin.py` for an implementation example
## Notes
* See https://github.com/FrameworkComputer/inputmodule-rs for info about the LED matrix device. Be sure to run the code that installs the udev rules for accessing the devices.
* To list your input devices, use the following python code after installing [Python-evdev](https://python-evdev.readthedocs.io/en/latest/index.html)
```
>>> import evdev

>>> devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
>>> for device in devices:
>>>     print(device.path, device.name, device.phys)
/dev/input/event1    Dell Dell USB Keyboard   usb-0000:00:12.1-2/input0
/dev/input/event0    Dell USB Optical Mouse   usb-0000:00:12.0-2/input0
```
* The baseline reference for calculating the ratio used to display temperature and fan speed readings were arbitarily defined. See `TEMP_REF` and `MAX_FAN_SPEED` in `temp_fan_plugin.py`.  
* To examine system performance measures manually and in detail, run `python ps-util-sensors.py`
* To use a different key combination for identifying the running apps, see `KEY_I` and `MODIFIER_KEYS` in `led_system_monitor.py`
