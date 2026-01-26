"""Smart Heating Manager for Tado CE.

Provides intelligent heating analytics including:
- Temperature rate calculation (heating/cooling rates)
- Time to target estimation
- Comfort risk prediction
- Weather compensation (Phase 3)

This module uses in-memory storage for temperature history,
which means data is reset on HA restart. This is acceptable
as the system will re-learn within 1-2 hours of operation.
"""
import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Configuration
HISTORY_WINDOW_HOURS = 2  # Keep 2 hours of history
MIN_DATA_POINTS = 3  # Minimum points needed for rate calculation
MIN_TIME_SPAN_MINUTES = 15  # Minimum time span for meaningful rate

# Weather compensation presets: (cold_threshold, cold_factor, warm_threshold, warm_factor)
WEATHER_COMPENSATION_PRESETS = {
    "none": (None, 1.0, None, 1.0),
    "light": (5, 1.1, 15, 0.95),
    "moderate": (5, 1.2, 10, 0.9),
    "aggressive": (0, 1.4, 10, 0.8),
}


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
    
    def __init__(self, hass: "HomeAssistant" = None):
        self._zones: dict[str, ZoneHistory] = {}
        self._enabled = False
        self._hass = hass
        # Weather compensation settings
        self._outdoor_temp_entity: str = ""
        self._weather_compensation: str = "none"
        self._use_feels_like: bool = False
    
    def configure_weather(
        self,
        outdoor_temp_entity: str = "",
        weather_compensation: str = "none",
        use_feels_like: bool = False
    ) -> None:
        """Configure weather compensation settings.
        
        Args:
            outdoor_temp_entity: Entity ID for outdoor temperature
            weather_compensation: Preset name (none/light/moderate/aggressive)
            use_feels_like: Whether to use feels-like temperature
        """
        self._outdoor_temp_entity = outdoor_temp_entity
        self._weather_compensation = weather_compensation
        self._use_feels_like = use_feels_like
        _LOGGER.info(
            f"Smart Heating: Weather compensation configured - "
            f"entity={outdoor_temp_entity}, preset={weather_compensation}, "
            f"feels_like={use_feels_like}"
        )
    
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
            "weather_compensation": self._weather_compensation,
            "outdoor_temp_entity": self._outdoor_temp_entity,
            "use_feels_like": self._use_feels_like,
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
    
    def get_outdoor_temperature(self) -> Optional[float]:
        """Get current outdoor temperature from configured entity.
        
        Returns:
            Outdoor temperature in °C, or None if not available
        """
        if not self._hass or not self._outdoor_temp_entity:
            return None
        
        try:
            state = self._hass.states.get(self._outdoor_temp_entity)
            if state is None or state.state in ('unknown', 'unavailable'):
                return None
            
            # Check if it's a weather entity (has temperature attribute)
            if self._outdoor_temp_entity.startswith('weather.'):
                temp = state.attributes.get('temperature')
                if temp is not None:
                    if self._use_feels_like:
                        # Try to get feels-like from attributes
                        feels_like = self._get_feels_like_from_weather(state)
                        if feels_like is not None:
                            return feels_like
                    return float(temp)
            else:
                # Regular sensor entity
                return float(state.state)
        except (ValueError, TypeError) as e:
            _LOGGER.debug(f"Failed to get outdoor temperature: {e}")
            return None
        
        return None
    
    def _get_feels_like_from_weather(self, state) -> Optional[float]:
        """Extract feels-like temperature from weather entity.
        
        Different weather integrations use different attribute names:
        - AccuWeather: apparent_temperature
        - PirateWeather: apparent_temperature
        - OpenWeatherMap: feels_like
        - Tomorrow.io: (calculate from temp/humidity/wind)
        
        Args:
            state: Weather entity state object
            
        Returns:
            Feels-like temperature, or None if not available
        """
        attrs = state.attributes
        
        # Try common attribute names
        for attr_name in ['apparent_temperature', 'feels_like', 'feelslike']:
            if attr_name in attrs and attrs[attr_name] is not None:
                try:
                    return float(attrs[attr_name])
                except (ValueError, TypeError):
                    continue
        
        # Calculate feels-like if we have temp, humidity, and wind
        temp = attrs.get('temperature')
        humidity = attrs.get('humidity')
        wind_speed = attrs.get('wind_speed')
        
        if temp is not None and humidity is not None:
            return self._calculate_feels_like(
                float(temp),
                float(humidity),
                float(wind_speed) if wind_speed else 0
            )
        
        return None
    
    def _calculate_feels_like(
        self,
        temp: float,
        humidity: float,
        wind_speed: float = 0
    ) -> float:
        """Calculate feels-like temperature.
        
        Uses wind chill for cold weather (≤10°C) and heat index for warm weather.
        
        Args:
            temp: Temperature in °C
            humidity: Relative humidity (0-100)
            wind_speed: Wind speed in km/h (default 0)
            
        Returns:
            Feels-like temperature in °C
        """
        # Wind chill for cold weather (≤10°C and wind > 4.8 km/h)
        if temp <= 10 and wind_speed > 4.8:
            # Wind chill formula (Environment Canada)
            # T_wc = 13.12 + 0.6215*T - 11.37*V^0.16 + 0.3965*T*V^0.16
            v_pow = wind_speed ** 0.16
            feels_like = 13.12 + 0.6215 * temp - 11.37 * v_pow + 0.3965 * temp * v_pow
            return round(feels_like, 1)
        
        # Heat index for warm weather (≥27°C)
        if temp >= 27:
            # Simplified heat index formula
            # HI = -8.785 + 1.611*T + 2.339*RH - 0.146*T*RH - 0.012*T² - 0.016*RH² + 0.002*T²*RH + 0.001*T*RH² - 0.000002*T²*RH²
            t = temp
            rh = humidity
            hi = (-8.785 + 1.611 * t + 2.339 * rh - 0.146 * t * rh 
                  - 0.012 * t * t - 0.016 * rh * rh 
                  + 0.002 * t * t * rh + 0.001 * t * rh * rh 
                  - 0.000002 * t * t * rh * rh)
            return round(hi, 1)
        
        # For moderate temperatures, just return actual temp
        return temp
    
    def get_compensated_rate(self, base_rate: float, for_heating: bool = True) -> float:
        """Apply weather compensation to a heating/cooling rate.
        
        Args:
            base_rate: Base rate in °C/hour
            for_heating: True for heating rate, False for cooling rate
            
        Returns:
            Compensated rate in °C/hour
        """
        if self._weather_compensation == "none":
            return base_rate
        
        outdoor_temp = self.get_outdoor_temperature()
        if outdoor_temp is None:
            return base_rate
        
        preset = WEATHER_COMPENSATION_PRESETS.get(
            self._weather_compensation,
            WEATHER_COMPENSATION_PRESETS["none"]
        )
        cold_thresh, cold_factor, warm_thresh, warm_factor = preset
        
        # For heating: cold weather = slower heating (more heat loss)
        # For cooling: cold weather = faster cooling (more heat loss)
        factor = 1.0
        
        if cold_thresh is not None and outdoor_temp < cold_thresh:
            if for_heating:
                # Cold weather: heating takes longer (divide by factor)
                factor = 1.0 / cold_factor
            else:
                # Cold weather: cooling is faster (multiply by factor)
                factor = cold_factor
        elif warm_thresh is not None and outdoor_temp > warm_thresh:
            if for_heating:
                # Warm weather: heating is faster (multiply by factor)
                factor = 1.0 / warm_factor
            else:
                # Warm weather: cooling is slower (divide by factor)
                factor = warm_factor
        
        compensated = base_rate * factor
        
        _LOGGER.debug(
            f"Weather compensation: outdoor={outdoor_temp}°C, "
            f"preset={self._weather_compensation}, factor={factor:.2f}, "
            f"base_rate={base_rate:.2f}, compensated={compensated:.2f}"
        )
        
        return round(compensated, 2)
    
    def get_compensated_time_to_target(
        self,
        zone_id: str,
        current_temp: float,
        target_temp: float
    ) -> Optional[int]:
        """Get weather-compensated time to reach target in minutes.
        
        Args:
            zone_id: Zone identifier
            current_temp: Current temperature
            target_temp: Target temperature
            
        Returns:
            Estimated minutes to reach target with weather compensation
        """
        if zone_id not in self._zones:
            return None
        
        zone = self._zones[zone_id]
        diff = target_temp - current_temp
        
        if abs(diff) < 0.1:
            return 0  # Already at target
        
        # Get base rate
        if diff > 0:
            base_rate = zone.get_heating_rate()
            for_heating = True
        else:
            base_rate = zone.get_cooling_rate()
            for_heating = False
        
        if base_rate is None or abs(base_rate) < 0.01:
            return None
        
        # Apply weather compensation
        compensated_rate = self.get_compensated_rate(base_rate, for_heating)
        
        if abs(compensated_rate) < 0.01:
            return None
        
        # Time = distance / speed
        hours = abs(diff) / abs(compensated_rate)
        minutes = int(hours * 60)
        
        # Cap at reasonable maximum (8 hours)
        return min(minutes, 480)


# Global instance
_manager: Optional[SmartHeatingManager] = None


def get_smart_heating_manager() -> SmartHeatingManager:
    """Get the global SmartHeatingManager instance."""
    global _manager
    if _manager is None:
        _manager = SmartHeatingManager()
    return _manager
