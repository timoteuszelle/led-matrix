# ZaneyOS Integration Guide

This document explains how to integrate the LED Matrix Monitoring service into your ZaneyOS configuration.

## Step 1: Add the flake input to zaneyos

In `/home/tim/zaneyos/flake.nix`, add this as an input:

```nix
{
  description = "ZaneyOS";

  inputs = {
    home-manager = {
      url = "github:nix-community/home-manager/release-25.05";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    nixpkgs.url = "github:nixos/nixpkgs/nixos-25.05";
    nixpkgs-unstable.url = "github:nixos/nixpkgs/nixpkgs-unstable";
    nvf.url = "github:notashelf/nvf";
    stylix.url = "github:danth/stylix/release-25.05";
    nixos-hardware.url = "github:NixOS/nixos-hardware/master";
    nix-flatpak.url = "github:gmodena/nix-flatpak?ref=latest";
    led-matrix-monitoring = {
      url = "github:timoteuszelle/led-matrix/main";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = {
    nixpkgs,
    nixos-hardware,
    nixpkgs-unstable,
    nix-flatpak,
    led-matrix-monitoring, # Add this
    ...
  } @ inputs: let
    # ... rest of configuration
```

## Step 2: Add the module to the amd profile

In `$HOME/zaneyos/profiles/amd/default.nix`:

```nix
{host, inputs, ...}: { # Add inputs parameter
  imports = [
    ../../hosts/${host}
    ../../modules/drivers
    ../../modules/core
    inputs.led-matrix-monitoring.nixosModules.led-matrix-monitoring # Add this line
    # or inputs.led-matrix-monitoring.nixosModules.ledmatrixmonitoring
  ];
  # Enable GPU Drivers
  drivers.amdgpu.enable = true;
  drivers.nvidia.enable = false;
  drivers.nvidia-prime.enable = false;
  drivers.intel.enable = false;
  vm.guest-services.enable = false;
}
```

## Step 3: Add the package to host-packages.nix

In `$HOME/zaneyos/hosts/sakai/host-packages.nix`, add the package:

```nix
{ inputs, pkgs, ... }:

{
  environment.systemPackages = with pkgs; [
    # ... your existing packages
    inputs.led-matrix-monitoring.packages.${pkgs.system}.default
  ];
}
```

## Step 4: Configure the service

You have two options for service configuration:

### Option A: Add to core/services.nix

Add the service configuration to `/home/tim/zaneyos/modules/core/services.nix`:

```nix
# Add this to the existing services.nix file
services.led-matrix-monitoring = {
  enable = true;

  # linuxOS | nix-flake | nix-module
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
  # Optional: disable keyboard listener if you don't want Alt+I shortcut
  # disableKeyListener = true;
  # Optional: disable plugins
  # disablePlugins = true;

  # Optional: environment override for display server access
  # environment.DISPLAY = ":0";
  # Optional: run as a different user (default is root)
  # user = "tim";
};
```

### Option B: Create a dedicated led-matrix service file

Create `$HOME/zaneyos/modules/core/led-matrix.nix`:

```nix
{...}: {
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
    # Optional settings
    # disableKeyListener = false;
    # disablePlugins = false;
    # user = "root";
  };
}
```

Then add it to `$HOME/zaneyos/modules/core/default.nix`:

```nix
{inputs, ...}: {
  imports = [
    ./boot.nix
    ./flatpak.nix
    ./fonts.nix
    ./greetd.nix
    ./hardware.nix
    ./led-matrix.nix  # Add this line
    ./network.nix
    # ... rest of imports
  ];
}
```

## Configuration Options

Recommended options:
- `configurationMode = "nix-module"` (or `nix-flake`)
- `layout.duration`
- `layout.quadrants.topLeft|bottomLeft|topRight|bottomRight`
- each app item supports `name`, `duration`, `animate`, `scope`, `persistentDraw`, `disposeFn`, `display`, and `args`

Compatibility options are still available:
- `settings` / `config` / `configFile`
- legacy shorthand `topLeft`, `bottomLeft`, `topRight`, `bottomRight`

## Building and Testing

After making the changes:

1. Build your system:
   ```bash
   cd ~/zaneyos
   sudo nixos-rebuild switch --flake .#amd
   ```

2. Check service status:
   ```bash
   systemctl status led-matrix-monitoring
   ```

3. View logs:
   ```bash
   journalctl -u led-matrix-monitoring -f
   ```

4. Test the binary directly:
   ```bash
   led-matrix-monitor --help
   ```

## User Permissions

If you run as a non-root user and keep key listening enabled, the service adds the `input` supplementary group at service runtime. Consider the security implications of keyboard device access.

## Development

To work on the package:

```bash
cd /run/media/tim/data/personal-git/led-matrix-monitoring
nix develop  # Enter development shell
# Make changes to the Python code
nix build    # Test build
```

To update in your system after changes:
```bash
cd ~/zaneyos
sudo nixos-rebuild switch --flake .#amd
```

