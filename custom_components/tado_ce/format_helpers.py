"""Display formatting helpers for Tado CE entities.

All internal-to-display value conversions live here.
Maps that also exist in const.py (overlay, window type) are
derived from const.py canonical dicts — not duplicated.
"""
from __future__ import annotations

from .const import OVERLAY_MODE_REVERSE_MAP, WINDOW_TYPE_REVERSE_MAP

# === Maps owned by this module (no equivalent in const.py) ===

WEATHER_STATE_MAP: dict[str, str] = {
    "CLOUDY_MOSTLY": "Mostly Cloudy", "CLOUDY_PARTLY": "Partly Cloudy",
    "CLOUDY": "Cloudy", "DRIZZLE": "Drizzle", "FOGGY": "Foggy",
    "NIGHT_CLEAR": "Clear Night", "NIGHT_CLOUDY": "Cloudy Night",
    "RAIN": "Rain", "SCATTERED_RAIN": "Scattered Rain", "SNOW": "Snow",
    "SUN": "Sunny", "THUNDERSTORMS": "Thunderstorms", "WINDY": "Windy",
}

ZONE_TYPE_DISPLAY_MAP: dict[str, str] = {
    "HEATING": "Heating", "AIR_CONDITIONING": "Air Conditioning", "HOT_WATER": "Hot Water",
}

COMFORT_MODEL_DISPLAY_MAP: dict[str, str] = {"adaptive": "Adaptive", "seasonal": "Seasonal"}

INSIGHT_TYPE_DISPLAY_MAP: dict[str, str] = {
    "mold_risk": "Mold Risk", "comfort": "Comfort", "battery": "Battery",
    "connection": "Connection", "window_predicted": "Open Window",
    "condensation": "Condensation", "preheat_timing": "Preheat Timing",
    "schedule_deviation": "Schedule Deviation", "heating_anomaly": "Heating Anomaly",
    "cross_zone_mold": "Cross-Zone Mold", "cross_zone_window": "Cross-Zone Open Window",
    "cross_zone_condensation": "Cross-Zone Condensation",
    "cross_zone_efficiency": "Cross-Zone Efficiency",
    "api_quota_planning": "API Quota", "weather_impact": "Weather Impact",
    "overlay_duration": "Overlay Duration", "schedule_gap": "Schedule Gap",
    "frequent_override": "Frequent Override", "away_heating": "Away Heating",
    "home_all_off": "Home All Off", "solar_gain": "Solar Gain",
    "solar_ac_load": "Solar AC Load", "frost_risk": "Frost Risk",
    "heating_season": "Heating Season", "heating_off_cold": "Heating Off Cold",
    "boiler_flow_anomaly": "Boiler Flow Anomaly",
    "early_start_disabled": "Early Start Disabled",
    "thermal_efficiency": "Thermal Efficiency",
    "temp_imbalance": "Temperature Imbalance",
    "humidity_imbalance": "Humidity Imbalance", "humidity_trend": "Humidity Trend",
    "device_limitation": "Device Limitation", "geofencing_offline": "Geofencing Offline",
    "api_usage_spike": "API Usage Spike",
}

API_STATUS_DISPLAY_MAP: dict[str, str] = {
    "ok": "OK", "warning": "Warning", "rate_limited": "Rate Limited",
}

CONFIDENCE_DISPLAY_MAP: dict[str, str] = {
    "no_schedule": "No Schedule", "insufficient_data": "Insufficient Data",
    "high": "High", "medium": "Medium", "low": "Low",
    "none": "None", "unknown": "Unknown",
}

TADO_MODE_DISPLAY_MAP: dict[str, str] = {"HOME": "Home", "AWAY": "Away"}

DATA_SOURCE_DISPLAY_MAP: dict[str, str] = {"home_state": "Home State", "zones": "Zones"}


# === Format functions ===
# All follow: format_<name>(value) -> str
# Falsy input -> "Unknown", unmapped -> value.replace("_", " ").title()


def format_zone_type(zone_type: str) -> str:
    """Convert internal zone_type to user-friendly display value."""
    return ZONE_TYPE_DISPLAY_MAP.get(zone_type, zone_type)


def format_window_type(window_type: str) -> str:
    """Convert internal window_type to user-friendly display value.

    Derives from WINDOW_TYPE_REVERSE_MAP in const.py (single source of truth).
    Includes 'passive_house' which was missing from the old sensor.py map.
    """
    return WINDOW_TYPE_REVERSE_MAP.get(window_type, window_type)


def format_comfort_model(comfort_model: str) -> str:
    """Convert internal comfort_model to user-friendly display value."""
    if not comfort_model:
        return "Unknown"
    return COMFORT_MODEL_DISPLAY_MAP.get(comfort_model, comfort_model.title())


def format_insight_type(insight_type: str) -> str:
    """Convert internal insight_type to user-friendly display value."""
    return INSIGHT_TYPE_DISPLAY_MAP.get(
        insight_type, insight_type.replace("_", " ").title()
    )


def format_priority(priority: str) -> str:
    """Convert internal priority to Title Case display value."""
    return priority.title() if priority else "None"


def format_api_status(status: str) -> str:
    """Convert internal API status to user-friendly display value."""
    if not status:
        return "Unknown"
    return API_STATUS_DISPLAY_MAP.get(status, status.replace("_", " ").title())


def format_overlay_type(overlay_type) -> str:
    """Convert internal overlay_type to user-friendly display value.

    Derives from OVERLAY_MODE_REVERSE_MAP in const.py (single source of truth).
    """
    if overlay_type is None:
        return "None"
    return OVERLAY_MODE_REVERSE_MAP.get(
        overlay_type, str(overlay_type).replace("_", " ").title()
    )


def format_confidence(confidence: str) -> str:
    """Convert internal confidence to user-friendly display value."""
    if not confidence:
        return "Unknown"
    return CONFIDENCE_DISPLAY_MAP.get(
        confidence, confidence.replace("_", " ").title()
    )


def format_tado_mode(mode: str) -> str:
    """Convert internal tado mode to user-friendly display value."""
    if not mode:
        return "Unknown"
    return TADO_MODE_DISPLAY_MAP.get(mode, mode.title())


def format_data_source(source: str) -> str:
    """Convert internal data source to user-friendly display value."""
    if not source:
        return "Unknown"
    return DATA_SOURCE_DISPLAY_MAP.get(source, source.replace("_", " ").title())


def format_weather_state(state: str) -> str:
    """Convert internal weather state to user-friendly display value."""
    if not state:
        return "Unknown"
    return WEATHER_STATE_MAP.get(state, state.replace("_", " ").title())
