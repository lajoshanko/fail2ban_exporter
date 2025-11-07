

# Fail2ban Exporter for Home Assistant

A custom Home Assistant integration that exposes metrics from a Fail2ban Prometheus Exporter as sensors.
It allows you to monitor Fail2ban jails, active bans, and login failures directly from Home Assistant.

⸻

## Requirements

This integration depends on the [Fail2ban Prometheus Exporter](https://github.com/hctrdev/fail2ban-prometheus-exporter) by @hctrdev.

The Docker image was originally designed for Prometheus and Grafana, but this integration allows Home Assistant to directly consume its metrics.

The exporter must be running and reachable from your Home Assistant instance.


## Host Installation
Docker Run Example
``` bash
docker run -d \
  --name fail2ban-exporter \
  -p 9191:9191 \
  -v /var/run/fail2ban:/var/run/fail2ban:ro \
  hctrdev/fail2ban-prometheus-exporter
```

Docker Compose Example
```
version: "3"
services:
  fail2ban-exporter:
    image: hctrdev/fail2ban-prometheus-exporter
    container_name: fail2ban-exporter
    restart: unless-stopped
    ports:
      - "9191:9191"
    volumes:
      - /var/run/fail2ban:/var/run/fail2ban:ro
```

By default, the exporter provides metrics at:
```
http://<your_host>:9191/metrics
```



## HA Installation

### Option 1: Manual Installation
  1.	Copy the fail2ban_exporter folder into your Home Assistant custom_components directory:
```
/config/custom_components/fail2ban_exporter/
```

  2.	Restart Home Assistant.

### Option 2: HACS (Recommended)
1.  In Home Assistant, open HACS → Integrations → 3-dot menu → Custom repositories.
2.	Add your GitHub repository URL and select Integration as the category.
3.	Search for Fail2ban Exporter and install it.
4.	Restart Home Assistant.

⸻

## Configuration
  1.	In Home Assistant, go to Settings → Devices & Services → Add Integration.
  2.	Search for Fail2ban Exporter.
  3.	Enter the exporter URL (for example: http://10.10.0.1:9191/metrics).
  4.	Save and finish setup.

The integration will automatically discover all active jails and create sensors for each jail’s metrics.

⸻

### Available Sensors

Only metrics prefixed with f2b_ are processed and exposed.

Sensor Name	Description
<jail> Currently Banned IPs	Number of IPs currently banned
<jail> Total Banned IPs	Total number of bans since startup
<jail> Current Failures	Ongoing login failures
<jail> Ban Time	Ban duration in seconds
Global Active Jails	Number of defined jails
Global Exporter Up	Exporter health status





Would you like me to add a Troubleshooting section at the end with the most common errors (e.g., exporter not reachable, “unknown” sensor values, etc.)? It’s often helpful for GitHub users.
