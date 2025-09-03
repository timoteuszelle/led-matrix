#!/bin/bash
chmod +x run.sh
dsp=$DISPLAY
args="$*"
rm -f fwledmonitor.service || true
if [[ ! -z "$args" ]];then
    sed -i "s#led_system_monitor.py.*\$#led_system_monitor.py ${args}#" run.sh
fi
cat <<EOF >>./fwledmonitor.service
[Unit]
Description=Framework 16 LED System Monitor
After=network.service

[Service]
Environment=DISPLAY=${dsp}
Type=simple
Restart=always
WorkingDirectory=$PWD
ExecStart=sh -c ./run.sh

[Install]
WantedBy=default.target
EOF

sudo systemctl stop fwledmonitor
sudo cp fwledmonitor.service /lib/systemd/system
sudo systemctl daemon-reload
sudo systemctl enable fwledmonitor
