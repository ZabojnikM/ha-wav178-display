FROM ghcr.io/home-assistant/base:latest

RUN apk add --no-cache python3 py3-pillow font-dejavu tzdata

ARG BUILD_VERSION=0.1.0
ARG BUILD_ARCH
LABEL io.hass.version="${BUILD_VERSION}" \
      io.hass.type="app" \
      io.hass.arch="${BUILD_ARCH}"

ENV PYTHONUNBUFFERED=1 PYTHONUTF8=1
WORKDIR /app
COPY app/ /app/
COPY run.sh /run.sh
RUN chmod 755 /run.sh
CMD ["/run.sh"]
