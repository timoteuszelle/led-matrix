{
  description = "LED Matrix Monitoring application for Framework 16";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };
  outputs = { self, nixpkgs, flake-utils }:
    let
      nixosModule = import ./ledmatrixmonitoring.nix;
    in
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        led-matrix-monitoring = pkgs.callPackage ./default.nix {};
      in
      {
        packages = {
          default = led-matrix-monitoring;
          led-matrix-monitoring = led-matrix-monitoring;
        };

        apps = {
          default = {
            type = "app";
            program = "${led-matrix-monitoring}/bin/led-matrix-monitor";
          };
        };

        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            python3
            python3Packages.pyserial
            python3Packages.numpy
            python3Packages.psutil
            python3Packages.evdev
            python3Packages.pynput
          ];
        };
      }
    ) // {
      nixosModules = {
        default = nixosModule;
        led-matrix-monitoring = nixosModule;
        ledmatrixmonitoring = nixosModule;
      };
    };
}

