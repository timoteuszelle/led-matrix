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
    
    # Development tools
    python3Packages.pip
    python3Packages.setuptools
    python3Packages.wheel
  ];
  
  shellHook = ''
    echo "LED Matrix Monitoring Development Environment"
    echo "Available commands:"
    echo "  python3 led_system_monitor.py --help"
    echo "  led-matrix-monitor --help"
    echo "  nix build"
  '';
}
