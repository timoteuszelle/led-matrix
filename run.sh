sudo apt install -y python3-numpy python3-psutil python3-serial python3-evdev

xhost +
export DISPLAY=:0
python3 ./led_system_monitor.py -tr temp -br fan
