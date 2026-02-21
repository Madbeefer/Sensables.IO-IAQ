"""Constants for the Sensables.IO IAQ integration.

Version: 1.0.0
"""

DOMAIN = "sensables_iaq"

# Configuration keys
CONF_WEBHOOK_ID = "webhook_id"
CONF_SENSOR_PREFIX = "sensor_prefix"
CONF_LOCATION = "location"
CONF_TEMPERATURE_UNIT = "temperature_unit"
CONF_EXPIRE_AFTER = "expire_after"

# Default values
DEFAULT_WEBHOOK_ID = "sensables_iaq"
DEFAULT_SENSOR_PREFIX = "sensables"
DEFAULT_LOCATION = ""
DEFAULT_TEMPERATURE_UNIT = "celsius"
DEFAULT_EXPIRE_AFTER = 3600
