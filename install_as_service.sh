#!/bin/bash
args="$*"
chmod +x run.sh
rm -f fwledmonitor.service || true
sed -i "s#led_system_monitor.py.*\$#led_system_monitor.py ${args}#" run.sh
cat <<EOF >>./fwledmonitor.service
[Unit]
Description=Framework 16 LED System Monitor
After=network.service

[Service]
Type=simple
Restart=always
WorkingDirectory=$PWD
ExecStart=sh -c "'$PWD/run.sh'"

[Install]
WantedBy=default.target
EOF

sudo systemctl stop fwledmonitor
sudo cp fwledmonitor.service /lib/systemd/system
sudo systemctl daemon-reload
sudo systemctl enable fwledmonitor
