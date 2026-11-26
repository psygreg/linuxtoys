{
  description = "LinuxToys - tools, tweaks and a software manager for Linux";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
      ];
    in
    flake-utils.lib.eachSystem systems (
      system:
      let
        pkgs = import nixpkgs { inherit system; };
        linuxtoys = pkgs.callPackage ./nix/package.nix { };
        app = {
          type = "app";
          program = "${linuxtoys}/bin/linuxtoys";
          meta.description = "LinuxToys - tools, tweaks and a software manager for Linux";
        };
      in
      {
        packages = {
          inherit linuxtoys;
          default = linuxtoys;
        };
        apps = {
          linuxtoys = app;
          default = app;
        };
        devShells.default = import ./shell.nix { inherit pkgs; };
        formatter = pkgs.nixfmt;
      }
    )
    // {
      overlays.default = final: prev: {
        linuxtoys = final.callPackage ./nix/package.nix { };
      };

      # `programs.linuxtoys.enable = true` adds the flake's package to the
      # system profile. The package itself carries the GTK/Python runtime
      # and the wrapper environment, so no NixOS options are required.
      nixosModules.default =
        {
          config,
          lib,
          pkgs,
          ...
        }:
        let
          system = pkgs.stdenv.hostPlatform.system;
        in
        {
          options.programs.linuxtoys.enable = lib.mkEnableOption "LinuxToys";

          config = lib.mkIf config.programs.linuxtoys.enable {
            environment.systemPackages = [ self.packages.${system}.default ];
          };
        };
    };
}
