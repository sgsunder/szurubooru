{
  lib,
  fetchurl,
  python3,
  ffmpeg-headless,
  postgresql,
  which,
}: let
  src = ./.;
  version = (lib.importTOML (src + "/pyproject.toml")).project.version;

  testing-postgresql = python3.pkgs.buildPythonPackage {
    pname = "testing.postgresql";
    version = "1.3.0";
    format = "wheel";
    src = fetchurl {
      url = "https://files.pythonhosted.org/packages/11/76/d614d4bc950d961a73c952e9a2e0956d02d0869a86d3dfad070376863988/testing.postgresql-1.3.0-py2.py3-none-any.whl";
      hash = "sha256-G0Ha65jfyM1KWEu5Ho9fSrGCmThw+VJXr+XxumFRpZg=";
    };
    doCheck = false;
    propagatedBuildInputs = with python3.pkgs; [pg8000 testing-common-database];
  };

  pytest-pgsql = python3.pkgs.buildPythonPackage {
    pname = "pytest-pgsql";
    version = "1.1.2";
    format = "wheel";
    src = fetchurl {
      url = "https://files.pythonhosted.org/packages/b5/68/7b44e25d51a2569ea74626a53072cc9c73388cb495bc3fc0c92157f9c809/pytest_pgsql-1.1.2-py3-none-any.whl";
      hash = "sha256-RdEn759i0p5BgDpWlRKcCG13ZmNIcW2DeCq/13EIrPs=";
    };
    doCheck = false;
    propagatedBuildInputs = with python3.pkgs; [freezegun pytest sqlalchemy testing-postgresql];
  };

  # Not packaged in nixpkgs.
  imagedominantcolor = python3.pkgs.buildPythonPackage {
    pname = "imagedominantcolor";
    version = "1.0.1";
    format = "wheel";
    src = fetchurl {
      url = "https://files.pythonhosted.org/packages/8c/cf/92931dbe2151fc92db9827dd12da43fc97e6579e3658e847f10e2f5bce67/imagedominantcolor-1.0.1-py3-none-any.whl";
      hash = "sha256-2JDWH3hjf3GPXravvWCRkxe4icRcXEEz1r+OZwsY/2w=";
    };
    doCheck = false;
    propagatedBuildInputs = with python3.pkgs; [pillow];
  };

  # Not packaged in nixpkgs..
  videohash = python3.pkgs.buildPythonPackage {
    pname = "videohash";
    version = "3.0.1";
    format = "wheel";
    src = fetchurl {
      url = "https://files.pythonhosted.org/packages/c1/e5/3fa06f6fc3c7b31cccaa2222c12d459332d2e419cebf238c31bd07cb3e60/videohash-3.0.1-py3-none-any.whl";
      hash = "sha256-miMNnN701bZ3xzd930d2YrA/7v1S/2dUV+Cu8+GbpNY=";
    };
    doCheck = false;
    propagatedBuildInputs = with python3.pkgs; [pillow imagehash yt-dlp imagedominantcolor];
  };

  pkg = python3.pkgs.buildPythonApplication {
    pname = "szurubooru-server";
    inherit src version;
    pyproject = true;

    nativeBuildInputs = with python3.pkgs; [setuptools pythonRelaxDepsHook];
    pythonRemoveDeps = ["pillow-avif-plugin"];

    nativeCheckInputs =
      (with python3.pkgs; [
        freezegun
        pytest-cov
        pytest-pgsql
        pytest-xdist
        pytestCheckHook
        testing-postgresql
      ])
      ++ [
        ffmpeg-headless
        postgresql
        which
      ];

    preCheck = ''
      export TEST_ENVIRONMENT=true
      export HOME=$(mktemp -d)
    '';

    # restrict pytest thread count to prevent excessive simultaneous postgres queries
    # which leads to slowdowns + timeout errors
    dontUsePytestXdist = true;
    pytestFlags = ["--tb=short" "--numprocesses=2"];

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
      videohash
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

      install -m0644 $src/config.yaml.dist $out/${python3.sitePackages}/config.yaml.dist
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
