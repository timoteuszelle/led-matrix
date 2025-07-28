# Version Information

## Current Version
- **Version**: 1.0.1
- **Branch**: nixpkgs-v1.0.1
- **Latest Commit**: TBD

## Usage with specific commit

For reproducible builds, use the specific commit hash:

```nix
led-matrix-monitoring = {
  url = "github:timoteuszelle/led-matrix/31c313214572e2f2b49cb21e961e5aa64a2b6c51";
  inputs.nixpkgs.follows = "nixpkgs";
};
```

## Changelog

### v1.0.1 (2025-07-28)
- Fixed pyproject.toml deprecation warnings:
  - Updated license format to modern SPDX expression
  - Removed deprecated license classifier
- Improved Python packaging standards compliance
- Prepared for nixpkgs pyproject.toml build system support

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

