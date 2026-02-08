# Tado CE Features Guide

Complete guide to all Tado CE exclusive features, configurations, and usage scenarios.

## 📑 Table of Contents

1. [Thermal Analytics](#-thermal-analytics)
2. [Smart Comfort Analytics](#-smart-comfort-analytics)
3. [Enhanced Mold Risk Assessment](#-enhanced-mold-risk-assessment)
4. [Adaptive Smart Polling](#-adaptive-smart-polling)
5. [Heating Cycle Detection](#-heating-cycle-detection)
6. [Configuration Scenarios](#-configuration-scenarios)
7. [Troubleshooting](#-troubleshooting)

---

## 🔥 Thermal Analytics

**Available:** v2.0.0+ | **Requirement:** TRV devices (VA01, VA02, RU01, RU02) | **Always Enabled**

Thermal Analytics provides real-time analysis of your heating system's thermal performance based on complete heating cycles.

### Sensors

| Sensor | Unit | Description |
|--------|------|-------------|
| `_thermal_inertia` | minutes | Time constant for temperature changes |
| `_avg_heating_rate` | °C/hour | Average heating rate when heating is ON |
| `_preheat_time` | minutes | Estimated time to reach target temperature |
| `_analysis_confidence` | % | Confidence score for thermal analysis |
| `_heating_acceleration` | °C/h² | Rate of change of heating rate |
| `_approach_factor` | %/hour | How quickly zone approaches target |

### Configuration

**No configuration needed** - Thermal Analytics is automatically enabled for zones with TRV devices.

**Why TRV-only?**
- TRV devices report heating power (0-100%)
- Smart Thermostats (SU02) don't report heating power
- Heating power is essential for accurate thermal analysis

### Usage Scenarios

#### Scenario 1: Optimize Preheat Timing

**Goal:** Start heating before you arrive home so room is warm when you get there.

**Setup:**
1. Check `_preheat_time` sensor for your zone
2. Create automation to start heating X minutes before schedule

**Example Automation:**
```yaml
automation:
  - alias: "Bedroom Preheat"
    trigger:
      - platform: time
        at: "17:30:00"  # 30 min before 6pm schedule
    condition:
      - condition: numeric_state
        entity_id: sensor.bedroom_preheat_time
        above: 20  # Only preheat if needed
    action:
      - service: climate.set_temperature
        target:
          entity_id: climate.bedroom
        data:
          temperature: 21
```

**Tips:**
- Wait for `_analysis_confidence` > 80% before trusting preheat estimates
- Preheat time adjusts automatically based on current temperature
- Use `_preheat_advisor` sensor for recommended start time

---

#### Scenario 2: Detect Insulation Issues

**Goal:** Identify rooms with poor insulation or heat loss.

**Indicators:**
- **Low thermal inertia (<20 min)** - Heat escapes quickly
- **Low heating rate (<0.5°C/h)** - Struggling to heat up
- **High approach factor (>150%/h)** - Temperature fluctuates rapidly

**Example:**
```
Living Room:
  Thermal Inertia: 15 minutes ⚠️ (very low)
  Heating Rate: 0.4°C/hour ⚠️ (slow)
  → Possible issue: Window seal broken, door gap, poor wall insulation
```

**Action:**
1. Check for drafts around windows/doors
2. Verify radiator valve is fully open
3. Check boiler flow temperature
4. Consider insulation improvements

---

#### Scenario 3: Compare Room Performance

**Goal:** Understand which rooms heat efficiently and which don't.

**Comparison Table:**

| Room | Thermal Inertia | Heating Rate | Confidence | Status |
|------|----------------|--------------|------------|--------|
| Living Room | 45 min | 1.2°C/h | 95% | ✅ Normal |
| Bedroom | 35 min | 1.5°C/h | 90% | ✅ Good |
| Bathroom | 15 min | 0.6°C/h | 85% | ⚠️ Poor insulation |
| Kitchen | 60 min | 0.8°C/h | 80% | ✅ High thermal mass |

**Interpretation:**
- Bathroom: Low inertia + slow heating = insulation issue
- Kitchen: High inertia + moderate heating = good (thermal mass from appliances)

---

## 🧠 Smart Comfort Analytics

**Available:** v1.9.0+ | **Requirement:** None | **Opt-in Configuration**

Smart Comfort Analytics learns from your heating patterns and provides predictive insights.

### Sensors

| Sensor | Unit | Description |
|--------|------|-------------|
| `_historical_deviation` | °C | Difference from 7-day average at same time |
| `_next_schedule_time` | timestamp | When next schedule change occurs |
| `_next_schedule_temp` | °C | Target temperature for next schedule |
| `_preheat_advisor` | minutes | Recommended preheat start time |
| `_smart_comfort_target` | °C | AI-recommended target temperature |

### Configuration

**Enable Smart Comfort:**
1. Go to Settings → Devices & Services → Tado CE
2. Click "Configure"
3. Enable "Smart Comfort Analytics"
4. Restart Home Assistant

### Usage Scenarios

#### Scenario 1: Detect Unusual Patterns

**Goal:** Get notified when temperature is abnormal.

**Setup:**
```yaml
automation:
  - alias: "Alert: Room Colder Than Usual"
    trigger:
      - platform: numeric_state
        entity_id: sensor.bedroom_historical_deviation
        below: -2.0  # 2°C colder than usual
    action:
      - service: notify.mobile_app
        data:
          message: "Bedroom is 2°C colder than usual - check for open windows"
```

**Use Cases:**
- Window left open
- Radiator valve stuck
- Heating schedule not working
- Boiler issue

---

#### Scenario 2: Automatic Preheat

**Goal:** Use AI to calculate optimal preheat start time.

**Setup:**
```yaml
automation:
  - alias: "Smart Preheat Before Schedule"
    trigger:
      - platform: template
        value_template: >
          {{ now().timestamp() >= 
             (state_attr('sensor.bedroom_next_schedule_time', 'timestamp') - 
              (states('sensor.bedroom_preheat_advisor') | int * 60)) }}
    action:
      - service: climate.set_temperature
        target:
          entity_id: climate.bedroom
        data:
          temperature: "{{ states('sensor.bedroom_next_schedule_temp') }}"
```

**Benefits:**
- No manual calculation needed
- Adjusts automatically based on current conditions
- Learns from your heating patterns

---

#### Scenario 3: Energy Optimization

**Goal:** Reduce heating when room is warmer than usual.

**Setup:**
```yaml
automation:
  - alias: "Reduce Heating When Warmer Than Usual"
    trigger:
      - platform: numeric_state
        entity_id: sensor.living_room_historical_deviation
        above: 1.0  # 1°C warmer than usual
    condition:
      - condition: state
        entity_id: climate.living_room
        state: "heat"
    action:
      - service: climate.set_temperature
        target:
          entity_id: climate.living_room
        data:
          temperature: >
            {{ state_attr('climate.living_room', 'temperature') - 0.5 }}
```

**Use Cases:**
- Solar gain (sunny day)
- Extra people in room
- Cooking/appliances generating heat

---

## 💧 Enhanced Mold Risk Assessment

**Available:** v2.0.0+ | **Requirement:** Outdoor temperature sensor | **Always Enabled**

Enhanced Mold Risk uses surface temperature calculation to accurately detect cold spots where mold can grow.

### Configuration

**Window Type Settings:**

| Window Type | U-Value (W/m²K) | Description | Mold Risk |
|-------------|-----------------|-------------|-----------|
| Single Pane | 5.0 | Old single-glazed windows | ⚠️ High |
| Double Pane | 2.7 | Standard double-glazed (default) | ⚠️ Medium |
| Triple Pane | 1.0 | Modern triple-glazed | ✅ Low |
| Passive House | 0.8 | High-performance windows | ✅ Very Low |

**Configure Window Type:**
1. Go to Settings → Devices & Services → Tado CE
2. Click "Configure"
3. Select "Mold Risk Window Type"
4. Choose your window type
5. Restart Home Assistant

**Configure Outdoor Temperature Source:**
1. Go to Settings → Devices & Services → Tado CE
2. Click "Configure"
3. Select "Outdoor Temperature Entity"
4. Choose your weather integration's temperature sensor
5. Restart Home Assistant

### Thresholds

**Mold Risk Levels:**

| Risk Level | Surface RH | Color | Action Required |
|------------|-----------|-------|-----------------|
| Low | <60% | 🟢 Green | None - safe |
| Medium | 60-70% | 🟡 Yellow | Monitor - increase ventilation |
| High | 70-80% | 🟠 Orange | Action needed - increase heating |
| Critical | >80% | 🔴 Red | Urgent - mold growth likely |

**Surface Temperature Calculation:**
```
T_surface = T_indoor - (T_indoor - T_outdoor) × U / (U + 8)

Where:
  U = Window U-value (W/m²K)
  8 = Interior surface heat transfer coefficient (W/m²K)
```

### Usage Scenarios

#### Scenario 1: Prevent Mold Growth

**Goal:** Get alerted when mold risk is high.

**Setup:**
```yaml
automation:
  - alias: "Alert: High Mold Risk"
    trigger:
      - platform: numeric_state
        entity_id: sensor.bedroom_mold_risk
        above: 70  # High risk threshold
        for:
          minutes: 30  # Sustained for 30 minutes
    action:
      - service: notify.mobile_app
        data:
          title: "⚠️ High Mold Risk in Bedroom"
          message: >
            Mold risk: {{ states('sensor.bedroom_mold_risk') }}%
            Surface temp: {{ state_attr('sensor.bedroom_mold_risk', 'surface_temperature') }}°C
            Action: Increase heating or open window for ventilation
```

---

#### Scenario 2: Automatic Ventilation

**Goal:** Open smart window when mold risk is high and outdoor humidity is low.

**Setup:**
```yaml
automation:
  - alias: "Auto Ventilation for Mold Prevention"
    trigger:
      - platform: numeric_state
        entity_id: sensor.bathroom_mold_risk
        above: 75
    condition:
      - condition: numeric_state
        entity_id: sensor.outdoor_humidity
        below: 60  # Only ventilate if outdoor air is dry
    action:
      - service: cover.open_cover
        target:
          entity_id: cover.bathroom_window
      - delay:
          minutes: 15
      - service: cover.close_cover
        target:
          entity_id: cover.bathroom_window
```

---

#### Scenario 3: Optimize Window Type Selection

**Goal:** Understand if window upgrade is worth it.

**Comparison:**

| Scenario | Indoor | Outdoor | Single Pane | Double Pane | Triple Pane |
|----------|--------|---------|-------------|-------------|-------------|
| Winter | 20°C | 0°C | 12.0°C (⚠️ 85% RH) | 15.4°C (⚠️ 72% RH) | 17.8°C (✅ 58% RH) |
| Cold Day | 20°C | 5°C | 14.5°C (⚠️ 78% RH) | 16.7°C (⚠️ 65% RH) | 18.5°C (✅ 55% RH) |
| Mild Day | 20°C | 10°C | 16.5°C (⚠️ 68% RH) | 17.8°C (✅ 58% RH) | 19.0°C (✅ 52% RH) |

**Interpretation:**
- Single pane: High mold risk even on mild days
- Double pane: Medium risk in winter, acceptable in mild weather
- Triple pane: Low risk in all conditions

**ROI Calculation:**
- Upgrade from single to double: ~40% reduction in mold risk
- Upgrade from double to triple: ~20% reduction in mold risk
- Consider upgrade if mold risk frequently >70%

---

## 📊 Adaptive Smart Polling

**Available:** v2.0.0+ | **Requirement:** None | **Always Enabled**

Adaptive Smart Polling automatically adjusts API polling interval based on remaining quota and time until reset.

### How It Works

**Formula:**
```
Interval = (Time Until Reset / Remaining Calls) / Safety Buffer

Where:
  Safety Buffer = 0.90 (keep 10% reserve)
  Min Interval = 5 minutes
  Max Interval = 120 minutes
```

### Configuration

**Polling Interval Options:**

| Mode | Description | When to Use |
|------|-------------|-------------|
| Adaptive (Recommended) | Auto-adjusts based on quota | Default - works for all quota tiers |
| Custom Interval | Fixed interval (e.g., 10 min) | Override when you want consistent polling |

**Set Custom Interval:**
1. Go to Settings → Devices & Services → Tado CE
2. Click "Configure"
3. Enable "Custom Polling Interval"
4. Set interval (5-120 minutes)
5. Restart Home Assistant

**Note:** Adaptive polling can override custom interval if quota is low.

### Usage Scenarios

#### Scenario 1: High Quota Tier (5000+ calls/day)

**Situation:**
- Quota: 5000 calls/day
- Remaining: 4500 calls
- Time until reset: 12 hours

**Adaptive Calculation:**
```
Interval = (12h × 60min) / (4500 / 0.90) = 720 / 5000 = 0.14 minutes
Clamped to MIN_INTERVAL = 5 minutes
```

**Result:** Polls every 5 minutes (maximum frequency)

**Benefits:**
- Near real-time updates
- Never runs out of quota
- Automatically slows down if usage spikes

---

#### Scenario 2: Low Quota Tier (100 calls/day)

**Situation:**
- Quota: 100 calls/day
- Remaining: 50 calls
- Time until reset: 12 hours

**Adaptive Calculation:**
```
Interval = (12h × 60min) / (50 / 0.90) = 720 / 55.5 = 13 minutes
```

**Result:** Polls every 13 minutes

**Benefits:**
- Distributes calls evenly across remaining time
- Prevents running out of quota
- Automatically speeds up after reset

---

#### Scenario 3: Quota Running Low

**Situation:**
- Quota: 500 calls/day
- Remaining: 10 calls (⚠️ low!)
- Time until reset: 6 hours

**Adaptive Calculation:**
```
Interval = (6h × 60min) / (10 / 0.90) = 360 / 11.1 = 32 minutes
```

**Result:** Polls every 32 minutes (slowed down to conserve quota)

**Benefits:**
- Prevents rate limiting
- Ensures some updates until reset
- Automatically speeds up after reset

---

#### Scenario 4: Custom Interval Override

**Situation:**
- You want consistent 10-minute polling
- Quota: 200 calls/day
- Remaining: 150 calls

**Setup:**
1. Enable "Custom Polling Interval" = 10 minutes
2. Adaptive polling monitors quota
3. If quota drops below safe threshold, adaptive overrides custom interval

**Result:**
- Normal: Polls every 10 minutes (custom)
- Low quota: Polls every 20+ minutes (adaptive override)

**Benefits:**
- Predictable polling when quota is healthy
- Automatic protection when quota is low

---

## 🔄 Heating Cycle Detection

**Available:** v2.0.0+ | **Requirement:** TRV devices | **Always Enabled**

Heating Cycle Detection identifies complete heating cycles (heating ON → target reached → heating OFF) for accurate thermal analysis.

### Configuration

**Cycle Detection Thresholds:**

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| Min Cycle Duration | 10 min | 5-30 min | Minimum time for valid cycle |
| Max Cycle Duration | 4 hours | 1-8 hours | Maximum time before timeout |
| Temperature Tolerance | 0.3°C | 0.1-0.5°C | How close to target = "reached" |
| Heating Power Threshold | 5% | 1-10% | Minimum power to consider "heating" |

**Adjust Thresholds (Advanced):**

These are hardcoded in `heating_cycle_coordinator.py` but can be modified if needed:

```python
# In heating_cycle_coordinator.py
MIN_CYCLE_DURATION = 600  # 10 minutes (in seconds)
MAX_CYCLE_DURATION = 14400  # 4 hours (in seconds)
TEMP_TOLERANCE = 0.3  # °C
HEATING_POWER_THRESHOLD = 5  # %
```

### Usage Scenarios

#### Scenario 1: Monitor Heating Efficiency

**Goal:** Track how many cycles complete successfully vs timeout.

**Check Attributes:**
```yaml
sensor.bedroom_thermal_inertia:
  attributes:
    cycle_count: 15  # Total cycles analyzed
    timeout_count: 2  # Cycles that timed out
    success_rate: 87%  # (15-2)/15 = 87%
```

**Interpretation:**
- High success rate (>90%): Heating system working well
- Low success rate (<70%): Possible issues (target too high, slow heating, frequent interruptions)

---

#### Scenario 2: Detect Heating Issues

**Goal:** Get alerted when heating cycles fail frequently.

**Setup:**
```yaml
automation:
  - alias: "Alert: Heating Cycles Failing"
    trigger:
      - platform: state
        entity_id: sensor.bedroom_analysis_confidence
    condition:
      - condition: template
        value_template: >
          {{ state_attr('sensor.bedroom_thermal_inertia', 'timeout_count') | int > 5 }}
    action:
      - service: notify.mobile_app
        data:
          title: "⚠️ Heating Issue Detected"
          message: >
            {{ state_attr('sensor.bedroom_thermal_inertia', 'timeout_count') }} 
            heating cycles timed out. Check radiator valve and boiler.
```

---

## 🎯 Configuration Scenarios

### Scenario 1: Small Apartment (1-2 rooms)

**Profile:**
- Quota: 100-200 calls/day
- Zones: 1-2 heating zones
- Features needed: Basic monitoring

**Recommended Configuration:**
```yaml
Adaptive Polling: Enabled (default)
Smart Comfort: Disabled (save quota)
Weather Sensors: Disabled (save quota)
Mold Risk: Enabled (important for small spaces)
Window Type: Double Pane (typical)
```

**Expected API Usage:**
- ~80-120 calls/day
- Polling interval: ~15-20 minutes

---

### Scenario 2: Large House (5+ rooms)

**Profile:**
- Quota: 500-5000 calls/day
- Zones: 5-10 heating zones
- Features needed: Full analytics

**Recommended Configuration:**
```yaml
Adaptive Polling: Enabled (default)
Smart Comfort: Enabled (useful for multiple zones)
Weather Sensors: Enabled (solar gain affects large houses)
Mold Risk: Enabled
Window Type: Per-zone (mix of double/triple pane)
Outdoor Temp: Weather integration
```

**Expected API Usage:**
- ~300-800 calls/day
- Polling interval: ~5-10 minutes

---

### Scenario 3: Energy Optimization Focus

**Profile:**
- Goal: Minimize energy usage
- Zones: Any
- Features needed: Preheat, efficiency tracking

**Recommended Configuration:**
```yaml
Adaptive Polling: Enabled
Smart Comfort: Enabled (for preheat advisor)
Thermal Analytics: Monitor closely
Automations:
  - Preheat before schedule (avoid heating too early)
  - Reduce heating when warmer than usual
  - Alert on low heating efficiency
```

**Key Sensors to Monitor:**
- `_preheat_time` - Optimize start time
- `_historical_deviation` - Detect free heat
- `_avg_heating_rate` - Track efficiency trends

---

### Scenario 4: Mold Prevention Focus

**Profile:**
- Goal: Prevent mold in high-risk areas (bathroom, basement)
- Zones: High-humidity zones
- Features needed: Mold risk monitoring

**Recommended Configuration:**
```yaml
Mold Risk: Enabled
Window Type: Accurate setting (affects calculation)
Outdoor Temp: Required (weather integration)
Automations:
  - Alert when mold risk >70%
  - Auto-ventilation when safe
  - Increase heating in high-risk zones
```

**Key Sensors to Monitor:**
- `_mold_risk` - Primary indicator
- `surface_temperature` (attribute) - Cold spot detection
- `temperature_source` (attribute) - Verify using surface estimation

---

## 🔧 Troubleshooting

### Issue: Thermal Analytics Shows "Unknown"

**Possible Causes:**
1. Zone doesn't have TRV device (only SU02 Smart Thermostat)
2. Not enough heating cycles collected (need 3-5 cycles)
3. HeatingCycleCoordinator not initialized

**Solution:**
1. Check if zone has TRV: Look for VA01, VA02, RU01, RU02 in device list
2. Wait 2-3 days for data collection
3. Check HA logs for coordinator warnings
4. Verify `cycle_count` attribute > 0

---

### Issue: Mold Risk Always Shows "Room Temperature"

**Possible Causes:**
1. Outdoor temperature entity not configured
2. Outdoor temperature sensor unavailable
3. Window type not set

**Solution:**
1. Configure outdoor temperature entity in integration settings
2. Verify outdoor sensor is working: Check `sensor.outdoor_temperature`
3. Set window type in integration settings
4. Check `temperature_source` attribute - should show "surface_estimation"

---

### Issue: Adaptive Polling Too Slow

**Possible Causes:**
1. Low remaining quota
2. Custom interval set too high
3. Many zones consuming quota

**Solution:**
1. Check `sensor.tado_ce_api_usage` - how many calls remaining?
2. Disable custom interval to use pure adaptive
3. Disable optional features (weather, smart comfort) to save quota
4. Consider upgrading Tado subscription for higher quota

---

### Issue: Smart Comfort Sensors Not Appearing

**Possible Causes:**
1. Smart Comfort not enabled in configuration
2. Integration not restarted after enabling

**Solution:**
1. Go to Settings → Devices & Services → Tado CE → Configure
2. Enable "Smart Comfort Analytics"
3. Restart Home Assistant
4. Wait 5 minutes for sensors to appear

---

## 📚 Related Documentation

- [SMART_COMFORT_GUIDE.md](SMART_COMFORT_GUIDE.md) - Detailed Smart Comfort sensor explanations
- [ENTITIES.md](ENTITIES.md) - Complete entity list
- [README.md](README.md) - Installation and setup
- [API_REFERENCE.md](API_REFERENCE.md) - Technical API details

---

**Last Updated:** v2.0.0 (2026-02-08)
