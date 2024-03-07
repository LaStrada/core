"""Support for Airthings sensors."""
from __future__ import annotations

from airthings_for_consumer_api_client.parser import AirthingsDevice

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    CONCENTRATION_PARTS_PER_BILLION,
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS,
    EntityCategory,
    UnitOfPressure,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import AirthingsDataCoordinatorType
from .const import DOMAIN

SENSORS: dict[str, SensorEntityDescription] = {
    "radonShortTermAvg": SensorEntityDescription(
        key="radonShortTermAvg",
        native_unit_of_measurement="Bq/m³",
        translation_key="radon",
    ),
    "temp": SensorEntityDescription(
        key="temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    "humidity": SensorEntityDescription(
        key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
    ),
    "pressure": SensorEntityDescription(
        key="pressure",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.MBAR,
    ),
    "battery": SensorEntityDescription(
        key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "co2": SensorEntityDescription(
        key="co2",
        device_class=SensorDeviceClass.CO2,
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
    ),
    "voc": SensorEntityDescription(
        key="voc",
        device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS,
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_BILLION,
    ),
    "light": SensorEntityDescription(
        key="light",
        native_unit_of_measurement=PERCENTAGE,
        translation_key="light",
    ),
    "virusRisk": SensorEntityDescription(
        key="virusRisk",
        translation_key="virus_risk",
    ),
    "mold": SensorEntityDescription(
        key="mold",
        translation_key="mold",
    ),
    "rssi": SensorEntityDescription(
        key="rssi",
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "pm1": SensorEntityDescription(
        key="pm1",
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        device_class=SensorDeviceClass.PM1,
    ),
    "pm25": SensorEntityDescription(
        key="pm25",
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        device_class=SensorDeviceClass.PM25,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Airthings sensor."""

    coordinator: AirthingsDataCoordinatorType = hass.data[DOMAIN][entry.entry_id]
    entities = [
        AirthingsHeaterEnergySensor(
            coordinator,
            airthings_device,
            SENSORS[sensor_types.sensor_type],
        )
        for airthings_device in coordinator.data.values()
        for sensor_types in airthings_device.sensors
        if sensor_types.sensor_type in SENSORS
    ]
    async_add_entities(entities)


class AirthingsHeaterEnergySensor(
    CoordinatorEntity[AirthingsDataCoordinatorType], SensorEntity
):
    """Representation of a Airthings Sensor device."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AirthingsDataCoordinatorType,
        airthings_device: AirthingsDevice,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

        self.entity_description = entity_description

        self._attr_unique_id = (
            f"{airthings_device.serial_number}_{entity_description.key}"
        )
        self._id = airthings_device.serial_number
        self._attr_device_info = DeviceInfo(
            configuration_url=(
                "https://dashboard.airthings.com/devices/"
                f"{airthings_device.serial_number}"
            ),
            identifiers={(DOMAIN, airthings_device.serial_number)},
            name=airthings_device.name,
            manufacturer="Airthings",
            model=airthings_device.type,
        )

    @property
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""
        for sensor in self.coordinator.data[self._id].sensors:
            if sensor.sensor_type == self.entity_description.key:
                return sensor.value
        return None

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        for sensor in self.coordinator.data[self._id].sensors:
            if sensor.sensor_type == self.entity_description.key:
                return True
        return False
