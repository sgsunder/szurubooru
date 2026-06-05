{
  lib,
  python3,
  ffmpeg-headless,
}: let
  src = ./.;
  version = (lib.importTOML (src + "/pyproject.toml")).project.version;

  pkg = python3.pkgs.buildPythonApplication {
    pname = "szurubooru-server";
    inherit src version;
    pyproject = true;

    nativeBuildInputs = with python3.pkgs; [setuptools];
    propagatedBuildInputs = with python3.pkgs; [
      certifi
      coloredlogs
      legacy-cgi
      numpy
      pillow
      pillow-heif
      psycopg2-binary
      pynacl
      pyrfc3339
      pytz
      pyyaml
      sqlalchemy
      yt-dlp
    ];

    makeWrapperArgs = [
      "--prefix PATH : ${lib.makeBinPath [ffmpeg-headless]}"
    ];

    postInstall = ''
      mkdir $out/bin
      install -m0755 $src/szuru-admin $out/bin/szuru-admin

      mkdir -p $out/share/szurubooru
      substitute $src/alembic.ini $out/share/szurubooru/alembic.ini \
        --replace-fail "script_location = szurubooru/migrations" \
                       "script_location = $out/${python3.sitePackages}/szurubooru/migrations"
    '';

    # Alembic is used to run database migrations. It needs szurubooru in its
    # environment so it can discover the migration scripts and models.
    passthru.alembic = python3.pkgs.alembic.overrideAttrs (old: {
      propagatedBuildInputs = old.propagatedBuildInputs ++ [pkg];
    });

    # Waitress is the WSGI server used to run szurubooru in production.
    passthru.waitress = python3.pkgs.waitress.overrideAttrs (old: {
      propagatedBuildInputs = old.propagatedBuildInputs ++ [pkg];
    });

    meta = {
      description = "Server of szurubooru, an image board engine for small and medium communities";
      homepage = "https://github.com/rr-/szurubooru";
      license = lib.licenses.gpl3;
    };
  };
in
  pkg
