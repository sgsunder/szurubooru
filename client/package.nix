{
  lib,
  buildNpmPackage,
  writeText,
  rev ? "unknown",
  buildDate ? 315532800, # 1980-01-01
}: let
  src = ./.;
in
  buildNpmPackage {
    pname = "szurubooru-client";
    inherit src;
    version = rev;

    npmDepsHash = "sha256-HtcitZl2idgVleB6c0KCTSNLxh7hP8/G/RGdMaQG3iI=";
    makeCacheWritable = true;

    BUILD_INFO = "nixpkgs-${rev}";
    BUILD_DATE = toString buildDate;

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
