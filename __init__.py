"""
Sensables.IO IAQ Integration for Home Assistant

This integration creates sensors from webhook data received via HTTP POST requests.
Place this file in: custom_components/sensables_iaq/__init__.py
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.http import HomeAssistantView
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.const import STATE_UNKNOWN

from .const import (
    DOMAIN,
    CONF_WEBHOOK_ID,
    CONF_SENSOR_PREFIX,
    CONF_LOCATION,
    CONF_TEMPERATURE_UNIT,
    CONF_EXPIRE_AFTER,
    DEFAULT_WEBHOOK_ID,
    DEFAULT_SENSOR_PREFIX,
    DEFAULT_LOCATION,
    DEFAULT_TEMPERATURE_UNIT,
    DEFAULT_EXPIRE_AFTER,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Sensables.IO IAQ from a config entry."""
    webhook_id = entry.data.get(CONF_WEBHOOK_ID, DEFAULT_WEBHOOK_ID)
    sensor_prefix = entry.data.get(CONF_SENSOR_PREFIX, DEFAULT_SENSOR_PREFIX)
    location = entry.data.get(CONF_LOCATION, DEFAULT_LOCATION)
    temperature_unit = entry.data.get(CONF_TEMPERATURE_UNIT, DEFAULT_TEMPERATURE_UNIT)
    expire_after = entry.data.get(CONF_EXPIRE_AFTER, DEFAULT_EXPIRE_AFTER)
    
    # Create entity component
    component = EntityComponent(_LOGGER, DOMAIN, hass)
    
    # Store configuration and sensors
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "webhook_id": webhook_id,
        "sensor_prefix": sensor_prefix,
        "location": location,
        "temperature_unit": temperature_unit,
        "expire_after": expire_after,
        "sensors": {},
        "entities": {},
        "component": component,
        "entry": entry,
    }
    
    # Register webhook endpoint
    view = WebhookSensorView(hass, entry.entry_id)
    hass.http.register_view(view)
    
    # Set up periodic cleanup of expired sensors
    async def cleanup_expired_sensors(now):
        """Remove expired sensors."""
        current_time = datetime.now()
        expired_sensors = []
        
        entry_data = hass.data[DOMAIN][entry.entry_id]
        for sensor_id, sensor_data in entry_data["sensors"].items():
            last_updated = sensor_data.get("last_updated")
            if last_updated and (current_time - last_updated).total_seconds() > expire_after:
                expired_sensors.append(sensor_id)
        
        for sensor_id in expired_sensors:
            _LOGGER.info(f"Removing expired sensor: {sensor_id}")
            entry_data["sensors"].pop(sensor_id, None)
            entity = entry_data["entities"].get(sensor_id)
            if entity:
                await component.async_remove_entity(entity.entity_id)
                entry_data["entities"].pop(sensor_id, None)
    
    # Schedule cleanup every 5 minutes
    entry_data = hass.data[DOMAIN][entry.entry_id]
    entry_data["cleanup_cancel"] = async_track_time_interval(
        hass, cleanup_expired_sensors, timedelta(minutes=5)
    )
    
    _LOGGER.info(f"Sensables.IO IAQ integration loaded. Webhook endpoint: /api/webhook/{webhook_id}")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    
    # Cancel cleanup task
    if "cleanup_cancel" in entry_data:
        entry_data["cleanup_cancel"]()
    
    # Remove all entities
    component = entry_data["component"]
    for entity in entry_data["entities"].values():
        await component.async_remove_entity(entity.entity_id)
    
    # Remove the config entry data
    hass.data[DOMAIN].pop(entry.entry_id)
    
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


class WebhookSensorView(HomeAssistantView):
    """Handle webhook requests and create/update sensors."""
    
    def __init__(self, hass: HomeAssistant, entry_id: str):
        self.hass = hass
        self.entry_id = entry_id
        entry_data = hass.data[DOMAIN][entry_id]
        webhook_id = entry_data["webhook_id"]
        self.url = f"/api/webhook/{webhook_id}"
        self.name = f"api:sensables_iaq_{webhook_id}"
        self.requires_auth = False  # Webhooks should not require authentication
        
    async def post(self, request):
        """Handle POST requests to webhook."""
        try:
            data = await request.json()
            
            # Get device name from header
            device_name = request.headers.get('device-name', 'unknown_device')
            device_name = device_name.lower().replace(' ', '_').replace('-', '_')
            
            _LOGGER.debug(f"Received webhook data from device '{device_name}': {data}")
            
            # Process the webhook data and create/update sensors
            await self._process_webhook_data(data, device_name)
            
            return self.json({"status": "success", "message": "Sensors updated"})
            
        except Exception as e:
            _LOGGER.error(f"Error processing webhook data: {e}")
            return self.json({"status": "error", "message": str(e)}, status_code=400)
    
    async def _process_webhook_data(self, data: Dict[str, Any], device_name: str = "unknown"):
        """Process webhook data and create sensors for air quality device."""
        entry_data = self.hass.data[DOMAIN][self.entry_id]
        sensor_prefix = entry_data["sensor_prefix"]
        location = entry_data["location"].strip()
        temperature_unit = entry_data["temperature_unit"]
        current_time = datetime.now()
        
        def celsius_to_fahrenheit(celsius_value):
            """Convert Celsius to Fahrenheit."""
            return round((celsius_value * 9/5) + 32, 1)
        
        # Define sensor configurations with proper units, device classes, and icons
        SENSOR_CONFIG = {
            "temperature": {
                "unit": "°F" if temperature_unit == "fahrenheit" else "°C", 
                "device_class": "temperature", 
                "name": "Temperature", 
                "icon": "mdi:thermometer"
            },
            "humidity": {"unit": "%", "device_class": "humidity", "name": "Humidity", "icon": "mdi:water-percent"},
            "iaq": {"unit": None, "device_class": None, "name": "Indoor Air Quality Index", "icon": "mdi:air-filter"},
            "voc": {"unit": "ppb", "device_class": None, "name": "VOC", "icon": "mdi:chemical-weapon"},
            "co2": {"unit": "ppm", "device_class": "carbon_dioxide", "name": "CO2", "icon": "mdi:molecule-co2"},
            "gas": {"unit": "Ω", "device_class": None, "name": "Gas Resistance", "icon": "mdi:resistor"},
            "pm1": {"unit": "μg/m³", "device_class": "pm1", "name": "PM1.0", "icon": "mdi:blur"},
            "pm25": {"unit": "μg/m³", "device_class": "pm25", "name": "PM2.5", "icon": "mdi:blur-linear"},
            "pm10": {"unit": "μg/m³", "device_class": "pm10", "name": "PM10", "icon": "mdi:grain"},
            "radon": {"unit": "Bq/m³", "device_class": None, "name": "Radon", "icon": "mdi:radioactive"},
            "mq7": {"unit": None, "device_class": None, "name": "MQ7 (CO Sensor)", "icon": "mdi:gas-cylinder"},
            "mq4": {"unit": None, "device_class": None, "name": "MQ4 (Methane Sensor)", "icon": "mdi:fire"},
            "mold": {"unit": None, "device_class": None, "name": "Mold Risk", "icon": "mdi:water-alert"},
            "smoke": {"unit": None, "device_class": None, "name": "Smoke Detector", "icon": "mdi:smoke-detector"},
            "co": {"unit": "ppm", "device_class": "carbon_monoxide", "name": "Carbon Monoxide", "icon": "mdi:molecule-co"},
        }
        
        for key, value in data.items():
            if key not in SENSOR_CONFIG:
                _LOGGER.debug(f"Unknown sensor type: {key}, adding with default config")
                config = {"unit": None, "device_class": None, "name": key.title(), "icon": "mdi:gauge"}
            else:
                config = SENSOR_CONFIG[key]
            
            # Convert temperature if needed
            processed_value = value
            if key == "temperature" and temperature_unit == "fahrenheit":
                try:
                    processed_value = celsius_to_fahrenheit(float(value))
                    _LOGGER.debug(f"Converted temperature from {value}°C to {processed_value}°F")
                except (ValueError, TypeError):
                    _LOGGER.warning(f"Could not convert temperature value: {value}")
                    processed_value = value
            
            # Create sensor ID with optional location
            if location:
                sensor_id = f"{sensor_prefix}_{location}_{device_name}_{key}".lower()
                display_name = f"{location.title()} {config['name']}"
                friendly_name = f"{location.title()} {device_name.replace('_', ' ').title()} {config['name']}"
            else:
                sensor_id = f"{sensor_prefix}_{device_name}_{key}".lower()
                display_name = f"{device_name.replace('_', ' ').title()} {config['name']}"
                friendly_name = display_name
            
            sensor_id = "".join(c for c in sensor_id if c.isalnum() or c == "_")
            
            # Store sensor data with enhanced attributes
            entry_data["sensors"][sensor_id] = {
                "value": processed_value,
                "original_value": value,
                "last_updated": current_time,
                "config": config,
                "device_name": device_name,
                "location": location,
                "display_name": display_name,
                "attributes": {
                    "device_name": device_name,
                    "location": location if location else None,
                    "sensor_type": key,
                    "unit_of_measurement": config["unit"],
                    "device_class": config["device_class"],
                    "source": "sensables_iaq_webhook",
                    "last_updated": current_time.isoformat(),
                    "friendly_name": friendly_name,
                    "temperature_unit": temperature_unit if key == "temperature" else None,
                    "original_celsius": value if key == "temperature" and temperature_unit == "fahrenheit" else None,
                }
            }
            
            # Create or update entity
            if sensor_id not in entry_data["entities"]:
                entity = WebhookSensorEntity(self.hass, self.entry_id, sensor_id)
                entry_data["entities"][sensor_id] = entity
                
                # Add entity through the component
                component = entry_data["component"]
                await component.async_add_entities([entity])
                _LOGGER.info(f"Created new sensor: {config.get('name', key)} (ID: {sensor_id})")
            else:
                # Update existing entity
                entity = entry_data["entities"][sensor_id]
                entity.async_write_ha_state()
                _LOGGER.debug(f"Updated sensor: {config.get('name', key)} with value: {processed_value}")
        
        _LOGGER.info(f"Processed {len(data)} sensors for device: {device_name}")
        if temperature_unit == "fahrenheit":
            temp_sensors = [k for k in data.keys() if k == "temperature"]
            if temp_sensors:
                _LOGGER.info(f"Temperature conversion enabled: C → F")


class WebhookSensorEntity(Entity):
    """Representation of a Sensables.IO IAQ webhook sensor."""
    
    def __init__(self, hass: HomeAssistant, entry_id: str, sensor_id: str):
        """Initialize the sensor."""
        self.hass = hass
        self.entry_id = entry_id
        self._sensor_id = sensor_id
        self._attr_unique_id = f"sensables_iaq_{sensor_id}"
        
        # Get sensor configuration
        entry_data = self.hass.data[DOMAIN][entry_id]
        sensor_data = entry_data["sensors"].get(sensor_id, {})
        config = sensor_data.get("config", {})
        device_name = sensor_data.get("device_name", "unknown")
        location = sensor_data.get("location", "")
        
        # Set the clean name directly from config, not from display_name
        self._attr_name = config.get('name', sensor_id)
        self._attr_device_class = config.get("device_class")
        self._attr_native_unit_of_measurement = config.get("unit")
        self._attr_icon = config.get("icon")
        
        # Set entity_id manually to ensure it's properly set
        self.entity_id = f"sensor.{sensor_id}"
        
    @property
    def state(self):
        """Return the state of the sensor."""
        entry_data = self.hass.data[DOMAIN][self.entry_id]
        sensor_data = entry_data["sensors"].get(self._sensor_id)
        if sensor_data:
            return sensor_data["value"]
        return STATE_UNKNOWN
    
    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        entry_data = self.hass.data[DOMAIN][self.entry_id]
        sensor_data = entry_data["sensors"].get(self._sensor_id)
        if sensor_data:
            return sensor_data.get("attributes", {})
        return {}
    
    @property
    def should_poll(self):
        """No polling needed."""
        return False
    
    @property
    def available(self):
        """Return True if entity is available."""
        entry_data = self.hass.data[DOMAIN][self.entry_id]
        return self._sensor_id in entry_data["sensors"]
    
    @property
    def device_class(self):
        """Return the device class."""
        return self._attr_device_class
    
    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._attr_native_unit_of_measurement
    
    @property
    def icon(self):
        """Return the icon."""
        return self._attr_icon
    
    @property
    def device_info(self):
        """Return device information to group sensors by device."""
        entry_data = self.hass.data[DOMAIN][self.entry_id]
        sensor_data = entry_data["sensors"].get(self._sensor_id, {})
        device_name = sensor_data.get("device_name", "unknown")
        location = sensor_data.get("location", "")
        
        # Create device identifier - include location if specified
        if location:
            device_id = f"{location}_{device_name}"
            device_display_name = f"{location.title()} {device_name.replace('_', ' ').title()}"
        else:
            device_id = device_name
            device_display_name = device_name.replace("_", " ").title()
        
        return {
            "identifiers": {(DOMAIN, device_id)},
            "name": device_display_name,
            "manufacturer": "Sensables.IO",
            "model": "IAQ Sensor Device",
            "sw_version": "1.0",
        }