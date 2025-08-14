# Version Information

## Current Version
- **Version**: 1.1.0
- **Branch**: fix/robustness-and-permission-handling
- **Latest Commit**: 39344ccceceb81e08c6ec162fad871cd06080948

## Usage with specific commit

For reproducible builds, use the specific commit hash:

```nix
led-matrix-monitoring = {
  url = "github:timoteuszelle/led-matrix/main";
  inputs.nixpkgs.follows = "nixpkgs";
};
```

## Changelog

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

