<p align="center">
  <img width="1280" height="668" alt="Solar-Log Legacy Banner" src="images/banner.png" />
</p>

<h1 align="center">Solar-Log Legacy for Home Assistant</h1>
<p align="center"><b>Local-only integration for legacy Solar-Log devices (firmware &lt; 3.x).</b></p>

<p align="center">
  <a href="#quick-install">Quick Install</a> |
  <a href="#how-it-works">How it Works</a> |
  <a href="#sensors">Sensors</a> |
  <a href="#issues">Issues</a>
</p>

<p align="center">
  <img alt="Version" src="https://img.shields.io/github/v/release/MauroDruwel/SolarlogLegacyHA"/>
  <img alt="License" src="https://img.shields.io/github/license/MauroDruwel/SolarlogLegacyHA"/>
  <img alt="HACS" src="https://img.shields.io/badge/HACS-Custom-orange"/>
</p>

---

> **Your legacy Solar-Log data, directly in Home Assistant. No cloud. No API. Just local JS file parsing.**

---

## Requirements

- **Home Assistant 2023.1+**
- A **legacy Solar-Log** device (firmware < 3.x, e.g. SolarLog 200/300/400/500/600/700)
- Your device must be reachable on your local network

No cloud account. No external dependencies. Just plain HTTP to your Solar-Log.

---

## Quick Install

### Via HACS (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=MauroDruwel&repository=SolarlogLegacyHA)

<details>
<summary>Or manually...</summary>

1. Open HACS -> **Integrations** -> **...** -> **Custom repositories**
2. Add: `https://github.com/MauroDruwel/SolarlogLegacyHA`
3. Search "Solar-Log Legacy" -> **Download**

</details>

### Manual Installation

```sh
cd /config/custom_components
git clone https://github.com/MauroDruwel/SolarlogLegacyHA.git solarlog_legacy
```

### Then...

1. Restart Home Assistant
2. **Settings** -> **Devices & Services** -> **Add Integration** -> "Solar-Log Legacy"
3. Enter your Solar-Log IP address or hostname (default: `http://solar-log`)
4. Done!

---

## Configuration

### Initial Setup

You'll be asked for your **Solar-Log host** (IP address or hostname). No authentication is needed — the device serves data openly on your local network.

The integration validates the connection by fetching `min_cur.js` before saving.

### Options

After setup, you can configure the **poll interval** (how often to fetch live data):

1. Go to **Settings** -> **Devices & Services** -> **Solar-Log Legacy** -> **Configure**
2. Set the scan interval (default: **15 seconds**, range: 10-300s)

> The integration uses three different endpoints with separate schedules:
> - **`min_cur.js`** — live power data, polled at your configured interval (default 15s)
> - **`pc.js?min0`** — yield and voltage history, polled every hour
> - **`base_vars.js`** — system info, polled once per day

---

## How it Works

```
+-----------------+     JS file parsing     +------------------+
|  Home Assistant | <----(HTTP GET)--------> |   Solar-Log 200  |
|   Integration   |    (no auth needed)     |   (firmware 2.x) |
+-----------------+                          +------------------+
```

1. The integration fetches JavaScript variable files from your Solar-Log device
2. It parses JS variable assignments (`var Pac=3249`, `new Array(...)`, etc.)
3. All data is transformed into Home Assistant sensors automatically

No cloud. No API. No scraping. Just HTTP GETs to files your Solar-Log already serves.

---

## Sensors

Once configured, you'll get sensors for your solar installation:

### Power & Energy (matching official HA integration)

| Sensor | Description | Source |
|--------|-------------|--------|
| Power AC | Current AC power output (W) | `min_cur.js` |
| Power DC | Current DC power output (W) | `min_cur.js` |
| Voltage DC | DC voltage (V) | `pc.js?min0` |
| Total Power | Installed peak power (W) | `base_vars.js` |
| Alternator Loss | Power loss (W) | computed |
| Capacity | Capacity (%) | computed |
| Efficiency | Efficiency (%) | computed |
| Last Update | Last data timestamp | `min_cur.js` |
| Yield Day | Today's yield (kWh) | `pc.js?min0` |
| Status | Inverter status | `min_cur.js` + `base_vars.js` |
| Consumption AC | AC consumption (W) | `min_cur.js` |

### Bonus Sensors

| Sensor | Description | Source |
|--------|-------------|--------|
| Error Code | Error code + description | `min_cur.js` + `base_vars.js` |
| Number of Inverters | Number of inverter units | `base_vars.js` |
| Firmware | Firmware version | `base_vars.js` |
| Inverter Model | Inverter model name | `base_vars.js` |
| String {n} Power | Per-string power output (W) | `min_cur.js` |
| String {n} Voltage | Per-string voltage (V) | `pc.js?min0` |
| String {n} Name | Per-string name | `base_vars.js` |

> Per-string sensors are created dynamically based on your actual string configuration. Leading zeros are skipped automatically.

---

## Issues

Something broken? [Open an issue](https://github.com/MauroDruwel/SolarlogLegacyHA/issues) and let's fix it.

## Contributing

PRs are welcome! Let's make this thing even better.

---

*Made with love for old Solar-Log devices that still work perfectly.*
