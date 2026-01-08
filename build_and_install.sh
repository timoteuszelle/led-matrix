sudo ./install_deps.sh
pyinstaller   --onedir   --name led_mon --add-data plugins:plugins --add-data snapshot_files:snapshot_files --add-data config.yaml:. --clean   --noconfirm main.py
sudo ./install_service.sh
