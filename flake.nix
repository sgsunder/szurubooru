{
  description = "szurubooru, an image board engine for small and medium communities";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = {
    self,
    nixpkgs,
  }: let
    systems = [
      "x86_64-linux"
      "aarch64-linux"
      "x86_64-darwin"
      "aarch64-darwin"
    ];
    forAllSystems = f:
      nixpkgs.lib.genAttrs systems (system:
        f nixpkgs.legacyPackages.${system});
  in {
    packages = forAllSystems (pkgs: rec {
      szurubooru-server = pkgs.callPackage ./server/package.nix {};
      szurubooru-client = pkgs.callPackage ./client/package.nix {};
      default = szurubooru-server;
    });
  };
}
