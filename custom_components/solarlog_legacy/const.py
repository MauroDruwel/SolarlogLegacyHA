"""Constants for the Solar-Log Legacy integration."""

DOMAIN = "solarlog_legacy"
ATTRIBUTION = "Data provided by Solar-Log"

CONF_HOST = "host"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_HOST = "http://solar-log"
DEFAULT_SCAN_INTERVAL = 15
MIN_SCAN_INTERVAL = 10
MAX_SCAN_INTERVAL = 300

TIMEOUT_NORMAL = 5
TIMEOUT_PCJS = 30

BASE_VARS_INTERVAL = 86400
PCJS_INTERVAL = 3600
