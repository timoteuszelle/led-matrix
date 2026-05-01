# Example NixOS configuration for Framework 16 LED Matrix Monitoring
# Add this to your configuration.nix or import it as a module

{ config, lib, pkgs, ... }:

{
  # For flake users, add this to your flake.nix inputs:
  # led-matrix-monitoring = {
  #   url = "github:timoteuszelle/led-matrix/main";
  #   inputs.nixpkgs.follows = "nixpkgs";
  # };
  # And add one of:
  #   led-matrix-monitoring.nixosModules.led-matrix-monitoring
  #   led-matrix-monitoring.nixosModules.ledmatrixmonitoring
  # to your modules list.

  # Enable the LED Matrix Monitoring service
  services.led-matrix-monitoring = {
    enable = true;

    # linuxOS | nix-flake | nix-module
    configurationMode = "nix-module";

    # Recommended: Nix-native config schema
    layout = {
      duration = 10;
      quadrants = {
        topLeft = [{ name = "cpu"; }];
        bottomLeft = [{ name = "mem-bat"; }];
        topRight = [{ name = "disk"; }];
        bottomRight = [{ name = "net"; }];
      };
    };

    # Panel-scope note:
    # If an app is configured with scope = "panel", it owns the full panel for that side
    # and the sibling quadrant is suppressed while active.
    # If both top and bottom apps on a side are scope = "panel", top takes precedence.

    # Legacy shorthand still works for compatibility:
    # topLeft = "cpu";
    # bottomLeft = "mem-bat";
    # topRight = "disk";
    # bottomRight = "net";
    # Optional: Disable keyboard shortcut (Alt+I)
    # disableKeyListener = true;
    # Optional: Disable plugins
    # disablePlugins = true;

    # Optional: extra environment for graphical sessions
    # environment.DISPLAY = ":0";
    # Optional: Run as specific user instead of root
    # user = "your-username";
  };

  # Optional: Add the package to system packages for manual use
  # environment.systemPackages = [
  #   led-matrix-monitoring.packages.${pkgs.system}.default
  # ];
}

