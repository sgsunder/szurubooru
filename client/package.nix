{
  lib,
  buildNpmPackage,
  writeText,
}: let
  src = ./.;
  version = (lib.importTOML ./../server/pyproject.toml).project.version;
in
  buildNpmPackage {
    pname = "szurubooru-client";
    inherit src version;

    npmDepsHash = "sha256-HtcitZl2idgVleB6c0KCTSNLxh7hP8/G/RGdMaQG3iI=";
    makeCacheWritable = true;

    BUILD_INFO = "nixpkgs-v${version}";

    npmBuildFlags = [
      "--gzip"
    ];

    installPhase = ''
      runHook preInstall

      mkdir $out
      mv ./public/* $out

      runHook postInstall
    '';

    meta = {
      description = "Client of szurubooru, an image board engine for small and medium communities";
      homepage = "https://github.com/rr-/szurubooru";
      license = lib.licenses.gpl3;
    };
  }
