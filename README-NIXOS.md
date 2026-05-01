# Framework 16 LED Matrix Monitoring - NixOS Integration

This repository provides a NixOS package and a standalone NixOS module (`ledmatrixmonitoring.nix`) for the Framework 16 LED Matrix monitor service.

## What is new in the module design

- **Standalone module file**: `ledmatrixmonitoring.nix` (no large inline module block in `flake.nix`)
- **Nix-native configuration schema**: `services.led-matrix-monitoring.layout` (typed options for quadrants/apps)
- **Configuration mode switch**: `configurationMode = "linuxOS" | "nix-flake" | "nix-module"`
- **Backward compatibility**: legacy quadrant shorthand (`topLeft`, `bottomLeft`, etc.) and `settings`/`configFile` remain available
- **Non-Nix Linux flow unchanged**: scripts like `build_and_install.sh` and `install_service.sh` are untouched

## Quick start (flake-based NixOS)

### 1) Add input

```nix
{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    led-matrix-monitoring = {
      url = "github:timoteuszelle/led-matrix/main";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };
}
```

### 2) Import the module

```nix
{
  imports = [
    inputs.led-matrix-monitoring.nixosModules.led-matrix-monitoring
    # or: inputs.led-matrix-monitoring.nixosModules.ledmatrixmonitoring
  ];
}
```

### 3) Configure the service (recommended style)

```nix
{
  services.led-matrix-monitoring = {
    enable = true;
    configurationMode = "nix-module";

    layout = {
      duration = 10;
      quadrants = {
        topLeft = [{ name = "cpu"; }];
        bottomLeft = [{ name = "mem-bat"; }];
        topRight = [{ name = "disk"; }];
        bottomRight = [{ name = "net"; }];
      };
    };

    # Optional examples:
    # disableKeyListener = true;
    # disablePlugins = true;
    # user = "tim";
    # environment.DISPLAY = ":0";
  };
}
```

### 4) Rebuild

```bash
sudo nixos-rebuild switch --flake .#your-hostname
```

## Configuration modes

- `linuxOS`
  - Service behaves like normal Linux packaging lookup (no Nix-managed config file injected)
  - Do **not** combine with `layout`, `settings`, `config`, `configFile`, or legacy quadrant shorthand
- `nix-flake`
  - Nix-managed config source required (`layout`, `settings`, `configFile`, or legacy shorthand)
- `nix-module`
  - Same runtime behavior as `nix-flake`, named for direct module-centric workflows

## Configuration sources (priority and compatibility)

Recommended:
- `layout` (typed, future-friendly Nix schema)

Also supported:
- `settings` (raw attrset rendered to YAML)
- `config` (deprecated alias of `settings`)
- `configFile` (path to YAML file)
- Legacy shorthand: `topLeft`, `bottomLeft`, `topRight`, `bottomRight` (+ `legacyDuration`)

## Notes for future development

The new schema aligns with long-term roadmap goals:
- clean mode boundaries
- easier extension for additional app fields/options
- stronger validation in module assertions
- easier API-oriented evolution without forcing users to hand-maintain YAML-shaped config in Nix

## Troubleshooting

Check service status:
```bash
systemctl status led-matrix-monitoring
```

Follow logs:
```bash
journalctl -u led-matrix-monitoring -f
```

Test binary:
```bash
led-matrix-monitor --help
```
