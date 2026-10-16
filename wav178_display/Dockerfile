FROM ghcr.io/home-assistant/base:latest@sha256:8fde4170393bdf7a121ea4d6e34b417e1d0b90125948459f9f9f70cdf5d77c16

RUN apk add --no-cache python3 py3-pillow font-dejavu tzdata

ARG BUILD_VERSION=0.6.0
ARG BUILD_ARCH
LABEL io.hass.version="${BUILD_VERSION}" \
      io.hass.type="app" \
      io.hass.arch="${BUILD_ARCH}"

ENV PYTHONUNBUFFERED=1 PYTHONUTF8=1
WORKDIR /app
COPY app/ /app/
COPY run.sh /run.sh
RUN chmod 755 /run.sh
# This app is one foreground Python process. Use Docker's init (Supervisor)
# instead of the inherited s6 entrypoint, which changes the process environment.
ENTRYPOINT ["/run.sh"]
CMD []
