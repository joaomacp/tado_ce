"""Heating cycle detection logic."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from .heating_cycle_models import HeatingCycle, HeatingCycleConfig, TemperatureReading

_LOGGER = logging.getLogger(__name__)

# Maximum cycle duration before timeout
MAX_CYCLE_DURATION = timedelta(hours=6)


class HeatingCycleDetector:
    """Detect heating cycle start, end, and interruptions for a single zone."""
    
    def __init__(self, zone_id: str, config: HeatingCycleConfig):
        """Initialize detector for a specific zone."""
        self._zone_id = zone_id
        self._config = config
        self._active_cycle: Optional[HeatingCycle] = None
        self._last_target_temp: Optional[float] = None
        
    def check_setpoint_change(
        self, new_target: float, timestamp: datetime
    ) -> bool:
        """Check if setpoint increased (potential cycle start).
        
        Returns:
            True if a new cycle was started, False otherwise.
        """
        if self._last_target_temp is None:
            self._last_target_temp = new_target
            return False
        
        if new_target > self._last_target_temp:
            # Setpoint increased, start new cycle
            if self._active_cycle:
                # Interrupt existing cycle
                self._active_cycle.interrupted = True
                self._active_cycle.interrupt_reason = "manual_setpoint_change"
                _LOGGER.debug(
                    "Zone %s: Interrupted active cycle due to setpoint change",
                    self._zone_id
                )
            
            # Start new cycle
            self._active_cycle = HeatingCycle(
                zone_id=self._zone_id,
                start_time=timestamp,
                end_time=None,
                start_temp=None,  # Will be set on first temp update
                target_temp=new_target,
                first_rise_time=None,
                first_rise_temp=None,
                temperature_readings=[],
                completed=False,
                interrupted=False,
                interrupt_reason=None,
            )
            self._last_target_temp = new_target
            
            _LOGGER.info(
                "Zone %s: Started new heating cycle, target=%.1f°C",
                self._zone_id,
                new_target
            )
            return True
        
        self._last_target_temp = new_target
        return False
    
    def on_temperature_update(self, temp: float, timestamp: datetime) -> None:
        """Process temperature update."""
        if not self._active_cycle:
            return
        
        # Set start_temp on first update
        if self._active_cycle.start_temp is None:
            self._active_cycle.start_temp = temp
            _LOGGER.debug(
                "Zone %s: Set cycle start_temp=%.1f°C",
                self._zone_id,
                temp
            )
        
        # Add temperature reading (with limit to prevent memory leak)
        if len(self._active_cycle.temperature_readings) < 100:
            self._active_cycle.temperature_readings.append(
                TemperatureReading(time=timestamp, temp=temp)
            )
        else:
            # Already at limit, log warning once
            if len(self._active_cycle.temperature_readings) == 100:
                _LOGGER.warning(
                    "Zone %s: Reached 100 temperature readings limit for cycle",
                    self._zone_id
                )
        
        # Detect first rise (inertia detection)
        if self._active_cycle.first_rise_time is None and self._active_cycle.start_temp is not None:
            temp_increase = temp - self._active_cycle.start_temp
            if temp_increase >= self._config.inertia_threshold_celsius:
                self._active_cycle.first_rise_time = timestamp
                self._active_cycle.first_rise_temp = temp
                _LOGGER.debug(
                    "Zone %s: Detected first rise at %.1f°C (+%.2f°C)",
                    self._zone_id,
                    temp,
                    temp_increase
                )
    
    def check_cycle_complete(self) -> Optional[HeatingCycle]:
        """Check if active cycle is complete.
        
        Returns:
            Completed cycle if target reached, None otherwise.
        """
        if not self._active_cycle:
            return None
        
        if not self._active_cycle.temperature_readings:
            return None
        
        current_temp = self._active_cycle.temperature_readings[-1].temp
        if current_temp >= self._active_cycle.target_temp:
            # Target reached
            self._active_cycle.end_time = datetime.now(timezone.utc)
            self._active_cycle.completed = True
            completed = self._active_cycle
            self._active_cycle = None
            
            _LOGGER.info(
                "Zone %s: Cycle completed, duration=%.1f min",
                self._zone_id,
                (completed.end_time - completed.start_time).total_seconds() / 60
            )
            return completed
        
        return None
    
    def check_cycle_timeout(self) -> bool:
        """Check if active cycle has timed out.
        
        Returns:
            True if cycle was timed out, False otherwise.
        """
        if not self._active_cycle:
            return False
        
        age = datetime.now(timezone.utc) - self._active_cycle.start_time
        if age > MAX_CYCLE_DURATION:
            self._active_cycle.interrupted = True
            self._active_cycle.interrupt_reason = "timeout"
            self._active_cycle.end_time = datetime.now(timezone.utc)
            
            _LOGGER.warning(
                "Zone %s: Cycle timed out after %.1f hours",
                self._zone_id,
                age.total_seconds() / 3600
            )
            
            self._active_cycle = None
            return True
        
        return False
    
    def resume_cycle(self, cycle: HeatingCycle) -> None:
        """Resume an active cycle after restart."""
        self._active_cycle = cycle
        self._last_target_temp = cycle.target_temp
        
        _LOGGER.info(
            "Zone %s: Resumed active cycle from %s",
            self._zone_id,
            cycle.start_time.isoformat()
        )
    
    def get_active_cycle(self) -> Optional[HeatingCycle]:
        """Get currently active cycle."""
        return self._active_cycle
