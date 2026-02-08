# Smart Comfort Sensors Guide

This guide explains all Smart Comfort sensors in Tado CE, including what they measure, how they're calculated, and how to interpret the values.

## 📊 Overview

Smart Comfort sensors analyze your heating patterns and provide insights into thermal performance. These sensors are **opt-in** and can be enabled in the integration configuration.

**Enable Smart Comfort:**
1. Go to Settings → Devices & Services → Tado CE
2. Click "Configure"
3. Enable "Smart Comfort Analytics"
4. Restart Home Assistant

---

## 🌡️ Thermal Analytics Sensors (v2.0.0+)

These sensors are **always enabled** for zones with TRV devices (VA01, VA02, RU01, RU02). They provide real-time thermal analysis based on heating cycles.

### 1. Thermal Inertia (`_thermal_inertia`)

**What it measures:** Time constant for temperature changes - how quickly your room responds to heating.

**Unit:** Minutes

**Formula:**
```
τ (tau) = time for 63.2% of temperature change to complete
```

**Interpretation:**
- **Low inertia (10-30 min):** Room heats/cools quickly (poor insulation, small room, high air flow)
- **Medium inertia (30-60 min):** Typical for most rooms
- **High inertia (60+ min):** Room heats/cools slowly (good insulation, large thermal mass, thick walls)

**Example:**
- Target: 20°C, Current: 18°C (need to heat 2°C)
- Thermal inertia: 40 minutes
- After 40 minutes: Temperature will reach ~19.3°C (63.2% of 2°C = 1.26°C increase)
- After 80 minutes: Temperature will reach ~19.9°C (86.5% complete)

**Why it's useful:**
- Understand how long preheat needs to be
- Identify insulation issues (very low inertia = heat escaping quickly)
- Optimize heating schedules

---

### 2. Average Heating Rate (`_avg_heating_rate`)

**What it measures:** Average temperature increase per hour when heating is ON.

**Unit:** °C/hour

**Formula:**
```
Heating Rate = Total Temperature Increase / Total Heating Time
```

**Interpretation:**
- **Slow (<0.5°C/h):** Possible issues (undersized radiator, low flow temperature, poor insulation)
- **Normal (0.5-2.0°C/h):** Typical for most rooms
- **Fast (>2.0°C/h):** Small room, oversized radiator, or external heat sources

**Example:**
- Heating turns on at 18.0°C
- After 1 hour of heating: 19.5°C
- Heating rate: **1.5°C/hour**

**Why it's useful:**
- Baseline for heating efficiency calculations
- Detect radiator/boiler issues (rate suddenly drops)
- Calculate preheat time needed

---

### 3. Preheat Time (`_preheat_time`)

**What it measures:** Estimated time needed to preheat room to target temperature.

**Unit:** Minutes

**Formula:**
```
Preheat Time = (Target - Current) / Heating Rate × 60
```

**Interpretation:**
- **0 minutes:** Already at or above target
- **10-30 minutes:** Normal preheat for small temperature difference
- **60+ minutes:** Large temperature difference or slow heating rate

**Example:**
- Current: 18°C, Target: 21°C (need 3°C increase)
- Heating rate: 1.5°C/hour
- Preheat time: **120 minutes** (2 hours)

**Why it's useful:**
- Automatically calculate when to start heating before schedule
- Avoid arriving home to cold room
- Optimize energy usage (don't start too early)

---

### 4. Analysis Confidence (`_analysis_confidence`)

**What it measures:** Confidence score for thermal analysis accuracy.

**Unit:** Percentage (0-100%)

**Formula:**
```
Confidence = min(100%, (Heating Cycles Analyzed / 10) × 100%)
```

**Interpretation:**
- **Low (<50%):** Not enough data yet, estimates may be inaccurate
- **Medium (50-80%):** Reasonable confidence, estimates improving
- **High (>80%):** High confidence, estimates are reliable

**Example:**
- 3 heating cycles analyzed
- Confidence: **30%** (need 7 more cycles for high confidence)

**Why it's useful:**
- Know when thermal analysis is reliable
- Understand if preheat estimates are trustworthy
- Wait for high confidence before using automation

---

### 5. Heating Acceleration (`_heating_acceleration`)

**What it measures:** Rate of change of heating rate (second-order derivative).

**Unit:** °C/hour²

**Formula:**
```
Acceleration = (Current Heating Rate - Previous Heating Rate) / Time Elapsed
```

**Interpretation:**
- **Positive:** Heating rate is increasing (room heating up faster over time)
- **Zero:** Heating rate is constant (steady state)
- **Negative:** Heating rate is decreasing (approaching target, heat loss increasing)

**Example:**
- First hour: Heating rate = 1.0°C/h
- Second hour: Heating rate = 1.5°C/h
- Acceleration: **+0.5°C/h²** (heating getting faster)

**Why it's useful:**
- Detect thermal dynamics (how heating behavior changes over time)
- Identify when room is approaching steady state
- Advanced thermal modeling

---

### 6. Approach Factor (`_approach_factor`)

**What it measures:** How quickly the zone approaches target temperature (percentage of gap closed per hour).

**Unit:** Percentage per hour (%/h)

**Formula:**
```
Approach Factor = (Heating Rate / Temperature Gap) × 100%
```

**Interpretation:**
- **Low (<50%/h):** Slow approach, will take multiple hours to reach target
- **Medium (50-100%/h):** Normal approach, will reach target in 1-2 hours
- **High (>100%/h):** Fast approach, will reach target in less than 1 hour

**Example:**
- Current: 18°C, Target: 20°C (gap = 2°C)
- Heating rate: 1.5°C/h
- Approach factor: **75%/hour** (closes 75% of gap per hour)
- Time to target: ~1.3 hours

**Why it's useful:**
- Predict time to reach target temperature
- Understand heating dynamics
- Optimize preheat timing

---

## 🧠 Smart Comfort Sensors (Opt-in)

These sensors require Smart Comfort Analytics to be enabled in configuration.

### 7. Historical Deviation (`_historical_deviation`)

**What it measures:** Difference between current temperature and 7-day average at the same time of day.

**Unit:** °C

**Formula:**
```
Deviation = Current Temperature - Average(Last 7 Days, Same Hour)
```

**Interpretation:**
- **Negative (e.g., -0.5°C):** Colder than usual at this time
- **Zero:** Same as usual
- **Positive (e.g., +1.0°C):** Warmer than usual at this time

**Example:**
- Current time: 10:00 AM, Temperature: 19.5°C
- Last 7 days at 10:00 AM: Average 20.0°C
- Deviation: **-0.5°C** (half a degree colder than usual)

**Why it's useful:**
- Spot unusual patterns (e.g., "Why is bedroom colder today?")
- Detect issues (window left open, radiator valve stuck)
- Identify if heating schedule needs adjustment

---

### 8. Next Schedule Time (`_next_schedule_time`)

**What it measures:** When the next scheduled temperature change will occur.

**Unit:** Timestamp

**Example:**
- Current time: 10:00 AM
- Next schedule: **6:00 PM** (evening heating starts)

**Why it's useful:**
- Know when heating will change automatically
- Plan manual overrides
- Understand heating schedule

---

### 9. Next Schedule Temperature (`_next_schedule_temp`)

**What it measures:** Target temperature for the next scheduled block.

**Unit:** °C

**Example:**
- Current target: 18°C (day mode)
- Next schedule target: **21°C** (evening mode at 6:00 PM)

**Why it's useful:**
- Preview upcoming temperature changes
- Understand heating schedule
- Plan manual adjustments

---

### 10. Preheat Advisor (`_preheat_advisor`)

**What it measures:** Recommended preheat start time before next schedule.

**Unit:** Minutes before schedule

**Formula:**
```
Preheat Start = Next Schedule Time - Preheat Time Estimate
```

**Interpretation:**
- **0 minutes:** No preheat needed (already at target or heating rate unknown)
- **15-30 minutes:** Normal preheat for small temperature difference
- **60+ minutes:** Large temperature difference or slow heating rate

**Example:**
- Next schedule: 6:00 PM at 21°C
- Current: 18°C (need 3°C increase)
- Preheat time: 120 minutes
- Preheat advisor: **Start heating at 4:00 PM**

**Why it's useful:**
- Automatically calculate when to start heating
- Arrive home to warm room
- Optimize energy usage

---

### 11. Smart Comfort Target (`_smart_comfort_target`)

**What it measures:** Recommended target temperature based on historical patterns and current conditions.

**Unit:** °C

**Formula:**
```
Smart Target = Historical Average + Comfort Adjustment
```

**Interpretation:**
- Suggests optimal temperature based on your past preferences
- Adjusts for time of day, day of week, and season
- Learns from your manual temperature adjustments

**Example:**
- Historical average at this time: 20°C
- You often adjust +1°C on cold days
- Smart target: **21°C**

**Why it's useful:**
- Automatic temperature optimization
- Learn from your preferences
- Reduce manual adjustments

---

## 🔧 Troubleshooting

### "No data" or "Unknown" State

**Possible causes:**
1. **Not enough heating cycles** - Thermal analytics needs 3-5 complete heating cycles to calculate metrics
2. **Heating always on** - Cooling rate needs heating-off periods to calculate
3. **Smart Comfort disabled** - Enable in integration configuration
4. **Zone has no TRV** - Thermal analytics only works with TRV devices (not SU02 Smart Thermostat)

**Solution:**
- Wait 2-3 days for data collection
- Check `data_points` or `cycle_count` attribute to see how much data is available
- Ensure heating turns on/off regularly (not always on or always off)

---

### Inaccurate Values

**Possible causes:**
1. **Low confidence** - Check `_analysis_confidence` sensor
2. **Recent changes** - Moved furniture, changed radiator settings, weather changed
3. **External heat sources** - Solar gain, cooking, people

**Solution:**
- Wait for confidence to reach >80%
- Values will stabilize after 5-10 heating cycles
- Check for external factors affecting temperature

---

### Heating Efficiency >200%

**This is normal!** High efficiency means you're getting free heat from:
- ☀️ Solar gain (sun through windows)
- 🍳 Internal heat sources (cooking, appliances, people)
- 🌡️ Warmer outdoor temperature
- 🪟 Better insulation (windows/doors closed)

**Interpretation:**
- **100%** = Normal heating (as expected)
- **<75%** = Slow heating (possible issue: open window, poor insulation, cold weather)
- **>125%** = Fast heating (external heat sources helping) ✅

---

## 📚 Related Documentation

- [ENTITIES.md](ENTITIES.md) - Complete list of all entities
- [README.md](README.md) - Integration setup and configuration
- [API_REFERENCE.md](API_REFERENCE.md) - Technical API details

---

## 💡 Tips & Best Practices

1. **Wait for high confidence** - Don't trust thermal analysis until confidence >80%
2. **Monitor trends** - Look at changes over days/weeks, not individual readings
3. **Use preheat advisor** - Automate heating start time based on preheat estimates
4. **Check historical deviation** - Spot unusual patterns early
5. **Combine with weather** - High efficiency on sunny days is normal (solar gain)

---

## 🆘 Need Help?

If you have questions about Smart Comfort sensors:
1. Check this guide first
2. Review [GitHub Discussions](https://github.com/hiall-fyi/tado_ce/discussions)
3. Open an [issue](https://github.com/hiall-fyi/tado_ce/issues) if you find a bug

---

**Last Updated:** v2.0.0 (2026-02-08)
