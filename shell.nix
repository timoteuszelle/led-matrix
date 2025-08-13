with import <nixpkgs> {};
mkShell {
  buildInputs = [
    stdenv.cc.cc.lib
    libgcc
    zstd
    python311
    python311Packages.pip
    python311Packages.virtualenv
    rocmPackages.rocm-runtime
    rocmPackages.hipblas
    rocmPackages.rocblas
  ];
  LD_LIBRARY_PATH = lib.makeLibraryPath [
    stdenv.cc.cc.lib
    libgcc
    zstd
    rocmPackages.rocm-runtime
    rocmPackages.hipblas
    rocmPackages.rocblas
  ];
}
