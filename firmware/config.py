# Non-secret settings. Secrets (Wi-Fi, token) live in secrets.yaml.
COUNTRY = "IL"

# Host running the add-on. Use the IP address: MicroPython can't resolve ".local" names.
SERVER_HOST = "192.168.68.166"  # Home Assistant (runs the add-on)
SERVER_PORT = 8099  # add-on port

ROTATE = 90  # must match the add-on's `rotate` option (only used for local screens)
USE_WATCHDOG = False  # False while developing (WDT can't be stopped once started)

SECRETS_FILE = "secrets.yaml"
