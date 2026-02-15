# Roadmap

Feature requests and planned improvements for Tado CE.

For completed features, see [CHANGELOG.md](CHANGELOG.md).

---

## Future Consideration

Features under consideration - need more community feedback or technical research.

**Per-Zone Configuration** (v2.1.0 Target):

Design Direction (2026-02-14, Updated):

1. **Options Flow Restructure** - 4 sections in order:
   ```
   ▼ Global Settings (最常用)
     Outdoor Temp Entity: [sensor.outdoor_temp]
     Hot Water Timer: [60] min
     ☐ Test Mode
   
   ▼ Zone Features (控制 zone entities 顯示，新用戶預設 OFF)
     ☐ Zone Diagnostics (battery, connection, heating power)
     ☐ Device Controls (child lock, early start)
     ☐ Boost Buttons
     ☐ Environment Sensors (mold risk, comfort level)
     ☐ Thermal Analytics
     ☐ Zone Configuration ← 開咗先有 per-zone settings entities
   
   ▼ Opt-In Features (額外 API calls)
     ☑ Weather Sensors
     ☑ Mobile Devices
     ☑ Schedule Calendar
     ...
   
   ▼ Polling & API (進階設定)
     ...
   ```

2. **Zone Device Controls** - Per-zone settings as entities (需要開 "Zone Configuration")
   ```
   Living Room (Zone Device)
   └─ Configuration:
       ├─ select.living_room_heating_type (Radiator/UFH)
       ├─ number.living_room_ufh_buffer (0-60 min, 只有 UFH 先顯示)
       ├─ switch.living_room_adaptive_preheat
       ├─ select.living_room_smart_comfort_mode (none/light/moderate/aggressive)
       └─ number.living_room_window_u_value (W/m²K)
   ```

3. **Migration** - Auto-migrate from global settings:
   - `ufh_zones` → `select.{zone}_heating_type`
   - `ufh_buffer_minutes` → `number.{zone}_ufh_buffer`
   - `adaptive_preheat_zones` → `switch.{zone}_adaptive_preheat`
   - `mold_risk_window_type` → `number.{zone}_window_u_value`
   - `smart_comfort_mode` → `select.{zone}_smart_comfort_mode`
   - Remove "Tado CE Exclusive" section (settings moved to Zone Device Controls)

4. **Benefits**:
   - Sleeker Options UI - only global toggles
   - Per-zone settings in zone device (more intuitive)
   - Automation support - entity-based settings
   - Reduced entity clutter for new users

Future consideration:
- **Per-Zone Overlay Mode** - Different overlay modes per zone

**Mold Risk Enhancements** ([#90](https://github.com/hiall-fyi/tado_ce/issues/90)):
- **Global Surface Temp Offset** - Optional offset for users with laser thermometer measurements

**API Management:**
- **Call Priority System** - Configurable weighting for different call types (e.g., zoneStates every 10 min, weather every 30 min). Requires significant coordinator architecture changes. Low priority - current adaptive polling handles most use cases.

**Environment Sensors** ([#64](https://github.com/hiall-fyi/tado_ce/issues/64)):
- **Indoor Air Quality (IAQ)** - Air quality score per zone (requires additional sensors)
- **Air Comfort** - Similar to Tado app's comfort visualization

**Hub Controls Migration:**
- **Quota Reserve Toggle** - Move `quota_reserve_enabled` from Config Options to Hub Controls for runtime toggle without reload
- **Test Mode Toggle** - Move `test_mode_enabled` from Config Options to Hub Controls for easier debugging
- **Benefit**: Allows automation control (e.g., "disable quota reserve when API remaining > 50") and faster toggling without entering Config Options
- **Note**: Waiting for community feedback on use cases before implementation

**Open Window Detection** ([#106](https://github.com/hiall-fyi/tado_ce/issues/106)):
- **Per-Zone Temperature Sensor Override** - Allow selecting any HA temperature sensor (HomeKit, Zigbee, etc.) per zone for faster updates
- **Rapid Temp Drop Detection** - Custom open window detection with configurable threshold (e.g., >2°C drop in 15 min)
- **Note**: Requires testing HomeKit sensor behavior (update frequency, reliability) before implementation

**Other:**
- Apply for HACS default repository inclusion
- Max Flow Temperature control (requires OpenTherm, [#15](https://github.com/hiall-fyi/tado_ce/issues/15))
- Combi boiler mode - hide timers/schedules for on-demand hot water ([#15](https://github.com/hiall-fyi/tado_ce/issues/15))

**Local API (Experimental):**
- **Local-first, cloud-fallback** - Use local API when available, fall back to cloud. Requires community help to test across different Tado hardware versions. See [Discussion #29](https://github.com/hiall-fyi/tado_ce/discussions/29).
- **Hybrid mode** - Configurable per-feature (e.g., local for reads, cloud for writes)

**Multi-Home Support:**
- **Multi-home preference in config flow** - New users asked "Plan to add multiple homes?" to enable home_id prefix
- **Allow multiple integration entries** - Each entry for a different home
- **Thread-safe home_id handling** - Replace global `_current_home_id` with per-entry context (current architecture uses global state that would conflict with multiple homes)
- **Per-home async_api client** - Change from singleton to per-entry client instances
- **Multi-home setup guide** - Documentation for users with multiple properties
- **Note**: Multi-home infrastructure (per-home data files, device identifiers) is already in place. Remaining work is primarily refactoring global state to per-entry context. Estimated 12-17 hours of work.

---

## Migration Design

All migrations are cumulative - users can upgrade directly from any version (e.g., v1.6.0 → v2.0.0) and all intermediate migrations will be applied automatically. Each migration step is idempotent (safe to run multiple times).

Entity IDs remain stable throughout migration if entity `unique_id` is unchanged.
