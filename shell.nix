{ pkgs ? import <nixpkgs> {} }:

let
  led-matrix-monitoring = pkgs.callPackage ./default.nix {};
in
pkgs.mkShell {
  buildInputs = with pkgs; [
    # The built package for testing
    led-matrix-monitoring
    
    # Development dependencies
    python3
    python3Packages.pyserial
    python3Packages.numpy
    python3Packages.psutil
    python3Packages.evdev
    python3Packages.pynput
    python3Packages.pyyaml  # NEW: Required for YAML config
    
    # Development tools
    python3Packages.pip
    python3Packages.setuptools
    python3Packages.wheel
    python3Packages.pyinstaller  # Optional: for testing PyInstaller builds
  ];
  
  shellHook = ''
    echo "LED Matrix Monitoring Development Environment"
    echo "Available commands:"
    echo "  python3 main.py --help                 (run directly with local config.yaml)"
    echo "  python3 main.py -cf config.yaml        (run with explicit config)"
    echo "  led-matrix-monitor --help              (run installed version)"
    echo "  nix build                              (build the package)"
    echo ""
    echo "Config file location: ~/.config/led-matrix/config.yaml"
    echo "Example config: see config.yaml in this directory"
  '';
}
