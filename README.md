# Raspberry Pi USB Weather Station (Ubuntu + Streamlit)

This project runs on a Raspberry Pi with Ubuntu and reads USB weather-station data, then displays temperature, humidity, and pressure in a lightweight Streamlit dashboard.

## What this includes

- `collector.py`: reads station data from USB serial, writes latest sample to JSON.
- `app.py`: Streamlit dashboard that displays the latest values.
- `install.sh`: installs system + Python dependencies and creates a virtual environment.
- `requirements.txt`: minimal Python dependencies.

## 1) Install from terminal (Ubuntu on Raspberry Pi)

```bash
cd ~/weather-dashboard
# or: git clone <your-repo-url> ~/weather-dashboard && cd ~/weather-dashboard
chmod +x install.sh
./install.sh
```

This installs:

- `python3-venv`, `python3-pip`, `python3-serial`, `usbutils`
- Python venv in `.venv`
- Streamlit + pyserial

## 2) Identify your USB weather station device

Plug in the weather station and run:

```bash
ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
lsusb
sudo dmesg | tail -n 50
```

Use the detected serial path as `WEATHER_PORT` (example: `/dev/ttyUSB0`).

## 3) Quick run (manual)

Terminal 1 (collector):

```bash
cd ~/weather-dashboard
source .venv/bin/activate
WEATHER_PORT=/dev/ttyUSB0 python collector.py
```

Terminal 2 (web UI):

```bash
cd ~/weather-dashboard
source .venv/bin/activate
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

Then open:

- `http://<pi-ip>:8501`

## 4) Data format notes

The collector currently supports simple line formats like:

- `T=23.4,H=56.1,P=1012.8`
- `temperature=23.4,humidity=56.1,pressure=1012.8`

If your station outputs a different format, run with raw logging:

```bash
WEATHER_PORT=/dev/ttyUSB0 WEATHER_LOG_RAW=1 python collector.py
```

Then share a few sample lines and update `parse_line(...)` in `collector.py`.

## 5) Run at boot (optional)

Create systemd service for collector:

```bash
sudo tee /etc/systemd/system/weather-collector.service >/dev/null <<'UNIT'
[Unit]
Description=USB Weather Collector
After=network.target

[Service]
User=$USER
WorkingDirectory=%h/weather-dashboard
Environment=WEATHER_PORT=/dev/ttyUSB0
ExecStart=%h/weather-dashboard/.venv/bin/python %h/weather-dashboard/collector.py
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
UNIT
```

Create systemd service for Streamlit:

```bash
sudo tee /etc/systemd/system/weather-ui.service >/dev/null <<'UNIT'
[Unit]
Description=Weather Streamlit UI
After=network.target weather-collector.service

[Service]
User=$USER
WorkingDirectory=%h/weather-dashboard
ExecStart=%h/weather-dashboard/.venv/bin/streamlit run %h/weather-dashboard/app.py --server.address 0.0.0.0 --server.port 8501
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
UNIT
```

Enable + start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now weather-collector weather-ui
sudo systemctl status weather-collector --no-pager
sudo systemctl status weather-ui --no-pager
```

## 6) Lightweight tips

- Keep only latest sample (already done via `/tmp/weather/latest.json`).
- Poll every 1s (default); raise to 2–5s for lower CPU.
- Use Ubuntu Server image (no desktop) on Pi for minimal overhead.
