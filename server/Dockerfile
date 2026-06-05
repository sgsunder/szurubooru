ARG PYTHON_VERSION=3.12


FROM python:${PYTHON_VERSION}-slim AS deps
WORKDIR /opt/app

RUN pip install --no-cache-dir pdm

COPY pyproject.toml pdm.lock ./
RUN pdm export -G server -o requirements.txt \
    && pdm export -G server -G dev -o requirements-dev.txt


FROM python:${PYTHON_VERSION}-slim AS prereqs
WORKDIR /opt/app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        dumb-init \
        ffmpeg \
        libheif-dev \
        libavif-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=deps /opt/app/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && rm requirements.txt

COPY ./ /opt/app/


FROM --platform=$BUILDPLATFORM prereqs AS testing
WORKDIR /opt/app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql \
    && rm -rf /var/lib/apt/lists/*
COPY --from=deps /opt/app/requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt && rm requirements-dev.txt

RUN addgroup --system app \
    && adduser --system --home /opt/app --ingroup app --no-create-home --gecos '' app \
    && chown app:app /opt/app

ENV TEST_ENVIRONMENT="true"
USER app
ENTRYPOINT ["pytest", "--tb=short"]
CMD ["szurubooru/"]


FROM prereqs AS development
WORKDIR /opt/app

ARG PUID=1000
ARG PGID=1000

COPY --from=deps /opt/app/requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt && rm requirements-dev.txt

RUN mkdir -p /data \
    && addgroup --gid ${PGID} app \
    && adduser --uid ${PUID} --ingroup app --home /opt/app --no-create-home --disabled-password --gecos '' app \
    && chown -R app:app /opt/app /data

USER app
CMD ["/opt/app/docker-start-dev.sh"]

ARG PORT=6666
ENV PORT=${PORT}
EXPOSE ${PORT}

ARG THREADS=4
ENV THREADS=${THREADS}

VOLUME ["/data/"]


FROM prereqs AS release
WORKDIR /opt/app

ARG PUID=1000
ARG PGID=1000

RUN mkdir -p /data \
    && addgroup --gid ${PGID} app \
    && adduser --uid ${PUID} --ingroup app --home /opt/app --no-create-home --disabled-password --gecos '' app \
    && chown -R app:app /opt/app /data

USER app
CMD ["/opt/app/docker-start.sh"]

ARG PORT=6666
ENV PORT=${PORT}
EXPOSE ${PORT}

ARG THREADS=4
ENV THREADS=${THREADS}

VOLUME ["/data/"]

ARG DOCKER_REPO
ARG BUILD_DATE
ARG SOURCE_COMMIT
LABEL \
    maintainer="" \
    org.opencontainers.image.title="${DOCKER_REPO}" \
    org.opencontainers.image.url="https://github.com/rr-/szurubooru" \
    org.opencontainers.image.documentation="https://github.com/rr-/szurubooru/blob/${SOURCE_COMMIT}/doc/INSTALL.md" \
    org.opencontainers.image.created="${BUILD_DATE}" \
    org.opencontainers.image.source="https://github.com/rr-/szurubooru" \
    org.opencontainers.image.revision="${SOURCE_COMMIT}" \
    org.opencontainers.image.licenses="GPL-3.0"
