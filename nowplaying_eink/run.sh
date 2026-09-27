#!/usr/bin/with-contenv bashio
# with-contenv exposes SUPERVISOR_TOKEN (used by the ha_entity source).
bashio::log.info "Starting Now Playing e-Ink"
cd /opt/nowplaying || exit 1
exec python3 -m app.main --options /data/options.json
