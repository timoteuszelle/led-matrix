{ ... }:

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

    disableKeyListener = true;
    disablePlugins = false;
    user = "root";
  };
}
