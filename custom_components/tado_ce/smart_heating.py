"""Smart Heating Manager for Tado CE.

Provides intelligent heating analytics including:
- Temperature rate calculation (heating/cooling rates)
- Time to target estimation
- Comfort risk prediction

This module uses in-memory storage for temperature history,
which means data is reset on HA restart. This is acceptable
as the system will re-learn within 1-2 hours of operation.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

_LOGGER = logging.getLogger(__name__)

# Configuration
HISTORY_WINDOW_HOURS = 2  # Keep 2 hours of history
MIN_DATA_POINTS = 3  # Minimum points needed for rate calculation
MIN_TIME_SPAN_MINUTES = 15  # Minimum time span for meaningful rate


@dataclass
class TemperatureReading:
    """A single temperature reading with context."""
    timestamp: datetime
    temperature: float
    is_heating: bool  # True if HVAC is actively heating/cooling
    target_temperature: Optional[float] = None


class ZoneHistory:
    """Temperature history for a single zone."""
    
    def __init__(self, zone_id: str, zone_name: str):
        self.zone_id = zone_id
        self.zone_name = zone_name
        self.readings: list[TemperatureReading] = []
        self._last_heating_rate: Optional[float] = None
        self._last_cooling_rate: Optional[float] = None
        self._rate_updated_at: Optional[datetime] = None
    
    def add_reading(self, reading: TemperatureReading) -> None:
        """Add a temperature reading and prune old data."""
        self.readings.append(reading)
        self._prune_old_readings()
    
    def _prune_old_readings(self) -> None:
        """Remove readings older than HISTORY_WINDOW_HOURS."""
        cutoff = datetime.now() - timedelta(hours=HISTORY_WINDOW_HOURS)
        self.readings = [r for r in self.readings if r.timestamp > cutoff]
    
    def get_heating_rate(self) -> Optional[float]:
        """Calculate heating rate (°C/hour) when HVAC is active.
        
        Uses linear regression on temperature readings where is_heating=True.
        Returns positive value for heating, negative for cooling (AC).
        """
        heating_readings = [r for r in self.readings if r.is_heating]
        return self._calculate_rate(heating_readings)
    
    def get_cooling_rate(self) -> Optional[float]:
        """Calculate cooling rate (°C/hour) when HVAC is off.
        
        Uses linear regression on temperature readings where is_heating=False.
        Returns negative value (temperature dropping) typically.
        """
        cooling_readings = [r for r in self.readings if not r.is_heating]
        return self._calculate_rate(cooling_readings)
    
    def _calculate_rate(self, readings: list[TemperatureReading]) -> Optional[float]:
        """Calculate temperature rate using linear regression.
        
        Args:
            readings: List of temperature readings to analyze
            
        Returns:
            Rate in °C/hour, or None if insufficient data
        """
        if len(readings) < MIN_DATA_POINTS:
            return None
        
        # Check time span
        time_span = (readings[-1].timestamp - readings[0].timestamp).total_seconds()
        if time_span < MIN_TIME_SPAN_MINUTES * 60:
            return None
        
        # Simple linear regression: y = mx + b
        # x = time in hours from first reading
        # y = temperature
        n = len(readings)
        base_time = readings[0].timestamp
        
        sum_x = 0.0
        sum_y = 0.0
        sum_xy = 0.0
        sum_x2 = 0.0
        
        for r in readings:
            x = (r.timestamp - base_time).total_seconds() / 3600  # Hours
            y = r.temperature
            sum_x += x
            sum_y += y
            sum_xy += x * y
            sum_x2 += x * x
        
        # Calculate slope (rate)
        denominator = n * sum_x2 - sum_x * sum_x
        if abs(denominator) < 0.0001:
            return None
        
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        
        # Round to 2 decimal places
        return round(slope, 2)
    
    def get_time_to_target(self, current_temp: float, target_temp: float) -> Optional[int]:
        """Estimate time to reach target temperature in minutes.
        
        Args:
            current_temp: Current temperature
            target_temp: Target temperature
            
        Returns:
            Estimated minutes to reach target, or None if cannot estimate
        """
        diff = target_temp - current_temp
        
        if abs(diff) < 0.1:
            return 0  # Already at target
        
        # Use heating rate if we need to heat up, cooling rate if cooling down
        if diff > 0:
            rate = self.get_heating_rate()
        else:
            rate = self.get_cooling_rate()
        
        if rate is None or abs(rate) < 0.01:
            return None
        
        # Time = distance / speed
        hours = abs(diff) / abs(rate)
        minutes = int(hours * 60)
        
        # Cap at reasonable maximum (8 hours)
        return min(minutes, 480)
    
    def predict_temperature(self, minutes_ahead: int, is_heating: bool) -> Optional[float]:
        """Predict temperature at a future time.
        
        Args:
            minutes_ahead: Minutes into the future
            is_heating: Whether HVAC will be active
            
        Returns:
            Predicted temperature, or None if cannot predict
        """
        if not self.readings:
            return None
        
        current_temp = self.readings[-1].temperature
        rate = self.get_heating_rate() if is_heating else self.get_cooling_rate()
        
        if rate is None:
            return None
        
        hours = minutes_ahead / 60
        predicted = current_temp + (rate * hours)
        
        return round(predicted, 1)


class SmartHeatingManager:
    """Manages smart heating analytics for all zones."""
    
    def __init__(self):
        self._zones: dict[str, ZoneHistory] = {}
        self._enabled = False
    
    def enable(self) -> None:
        """Enable smart heating tracking."""
        self._enabled = True
        _LOGGER.info("Smart Heating Manager enabled")
    
    def disable(self) -> None:
        """Disable smart heating tracking."""
        self._enabled = False
        _LOGGER.info("Smart Heating Manager disabled")
    
    @property
    def is_enabled(self) -> bool:
        return self._enabled
    
    def get_zone(self, zone_id: str, zone_name: str = "") -> ZoneHistory:
        """Get or create zone history tracker."""
        if zone_id not in self._zones:
            self._zones[zone_id] = ZoneHistory(zone_id, zone_name or f"Zone {zone_id}")
        return self._zones[zone_id]
    
    def record_temperature(
        self,
        zone_id: str,
        zone_name: str,
        temperature: float,
        is_heating: bool,
        target_temperature: Optional[float] = None
    ) -> None:
        """Record a temperature reading for a zone.
        
        This should be called on each zone state update.
        
        Args:
            zone_id: Zone identifier
            zone_name: Human-readable zone name
            temperature: Current temperature
            is_heating: Whether HVAC is actively heating/cooling
            target_temperature: Current target temperature (optional)
        """
        if not self._enabled:
            return
        
        zone = self.get_zone(zone_id, zone_name)
        reading = TemperatureReading(
            timestamp=datetime.now(),
            temperature=temperature,
            is_heating=is_heating,
            target_temperature=target_temperature
        )
        zone.add_reading(reading)
        
        _LOGGER.debug(
            f"Smart Heating: Recorded {zone_name} temp={temperature}°C "
            f"heating={is_heating} target={target_temperature}"
        )
    
    def get_heating_rate(self, zone_id: str) -> Optional[float]:
        """Get heating rate for a zone in °C/hour."""
        if zone_id not in self._zones:
            return None
        return self._zones[zone_id].get_heating_rate()
    
    def get_cooling_rate(self, zone_id: str) -> Optional[float]:
        """Get cooling rate for a zone in °C/hour."""
        if zone_id not in self._zones:
            return None
        return self._zones[zone_id].get_cooling_rate()
    
    def get_time_to_target(
        self,
        zone_id: str,
        current_temp: float,
        target_temp: float
    ) -> Optional[int]:
        """Get estimated time to reach target in minutes."""
        if zone_id not in self._zones:
            return None
        return self._zones[zone_id].get_time_to_target(current_temp, target_temp)
    
    def is_comfort_at_risk(
        self,
        zone_id: str,
        current_temp: float,
        target_temp: float,
        minutes_until_schedule: int,
        is_currently_heating: bool
    ) -> Optional[bool]:
        """Check if comfort target is at risk of being missed.
        
        Args:
            zone_id: Zone identifier
            current_temp: Current temperature
            target_temp: Target temperature at schedule time
            minutes_until_schedule: Minutes until next schedule change
            is_currently_heating: Whether HVAC is currently active
            
        Returns:
            True if target will likely be missed, False if OK, None if unknown
        """
        if zone_id not in self._zones:
            return None
        
        zone = self._zones[zone_id]
        predicted = zone.predict_temperature(minutes_until_schedule, is_currently_heating)
        
        if predicted is None:
            return None
        
        # For heating: at risk if predicted < target - 0.5°C
        # For cooling (AC): at risk if predicted > target + 0.5°C
        if target_temp > current_temp:
            # Heating scenario
            return predicted < (target_temp - 0.5)
        else:
            # Cooling scenario (AC)
            return predicted > (target_temp + 0.5)
    
    def get_stats(self) -> dict:
        """Get statistics about tracked zones."""
        return {
            "enabled": self._enabled,
            "zones_tracked": len(self._zones),
            "zones": {
                zone_id: {
                    "name": zone.zone_name,
                    "readings": len(zone.readings),
                    "heating_rate": zone.get_heating_rate(),
                    "cooling_rate": zone.get_cooling_rate(),
                }
                for zone_id, zone in self._zones.items()
            }
        }


# Global instance
_manager: Optional[SmartHeatingManager] = None


def get_smart_heating_manager() -> SmartHeatingManager:
    """Get the global SmartHeatingManager instance."""
    global _manager
    if _manager is None:
        _manager = SmartHeatingManager()
    return _manager
