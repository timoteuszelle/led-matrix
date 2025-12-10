# Version Information

## Current Version
- **Version**: 1.1.1
- **Branch**: main
- **Latest Commit**: c609efc2805484a23274845e13082d67f642e6e0

## Usage with specific commit

For reproducible builds, use the specific commit hash:

```nix
led-matrix-monitoring = {
  url = "github:timoteuszelle/led-matrix/main";
  inputs.nixpkgs.follows = "nixpkgs";
};
```

## Changelog

### v1.1.1 (2025-11-20)
- **Robustness Fixes**:
  - Fixed brightness scaling to properly use `max_brightness` from sysfs backlight devices
  - Added clamping of brightness values to valid byte range [0, 255] to prevent overflow errors
  - Added safe byte conversion in LED drawing to prevent invalid values being sent to hardware
  - Clamped CPU percentage values to [0.0, 1.0] range to handle edge cases
- **Stability Improvements**:
  - Better handling of brightness calculation edge cases
  - More robust LED matrix value validation before hardware transmission

### v1.1.0 (2025-08-13)
- **Major Features**:
  - Merged latest upstream changes from MidnightJava/led-matrix
  - Complete plugin system with temperature and fan monitoring
  - Snapshot display functionality with JSON file support
  - Dual keyboard backend support (evdev + pynput)
- **Upstream Integration**:
  - Enhanced keyboard shortcut handling (Alt+I)
  - Multi-panel snapshot display with timing controls
  - Improved device discovery and communication
  - Better plugin path resolution for Nix installations
- **NixOS Improvements**:
  - Added pynput dependency for cross-platform compatibility
  - Fixed shell.nix with proper LED matrix development environment
  - Enhanced flake with complete dependency management
- **Robustness Enhancements**:
  - Graceful fallback when evdev unavailable
  - Better error handling in plugin loading
  - Improved hardware detection and permission handling

### v1.0.0 (2025-07-26)
- Initial NixOS packaging
- Complete flake with NixOS module support
- Robustness improvements:
  - Fixed evdev permission handling
  - Graceful degradation when hardware unavailable
  - Fixed Python regex deprecation warnings
  - Safe device access in main loop
- Comprehensive documentation for NixOS users
- Example configurations
- ZaneyOS integration guide

