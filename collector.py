#!/usr/bin/env python3
"""USB weather-station collector.

Reads serial lines from WEATHER_PORT and writes latest parsed sample to JSON.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

import serial

PORT = os.getenv("WEATHER_PORT", "/dev/ttyUSB0")
BAUD = int(os.getenv("WEATHER_BAUD", "9600"))
POLL_SLEEP_S = float(os.getenv("WEATHER_POLL_SLEEP", "1.0"))
OUT_FILE = Path(os.getenv("WEATHER_OUT", "/tmp/weather/latest.json"))
LOG_RAW = os.getenv("WEATHER_LOG_RAW", "0") == "1"


def _normalize_keys(payload: Dict[str, str]) -> Dict[str, str]:
    alias = {
        "t": "temperature",
        "temp": "temperature",
        "temperature": "temperature",
        "h": "humidity",
        "hum": "humidity",
        "humidity": "humidity",
        "p": "pressure",
        "pres": "pressure",
        "pressure": "pressure",
    }
    normalized: Dict[str, str] = {}
    for key, value in payload.items():
        clean_key = key.strip().lower()
        if clean_key in alias:
            normalized[alias[clean_key]] = value.strip()
    return normalized


def parse_line(line: str) -> dict:
    """Parse line format like T=23.4,H=56.1,P=1012.8."""
    chunks = [x.strip() for x in line.split(",") if "=" in x]
    kv = dict(chunk.split("=", 1) for chunk in chunks)
    data = _normalize_keys(kv)
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "temperature_c": float(data["temperature"]),
        "humidity_pct": float(data["humidity"]),
        "pressure_hpa": float(data["pressure"]),
    }


def parse_mws_message(message: str) -> dict:
    """Parse AMWS/MWS multiline payload ending with SND.

    Expected fields:
    - TA:<temp_c>
    - RH:<humidity_pct>
    - BA:<pressure_hpa>
    """
    values: Dict[str, str] = {}
    for raw_line in message.splitlines():
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().upper()
        value = value.strip()
        if key in {"TA", "RH", "BA"}:
            values[key] = value

    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "temperature_c": float(values["TA"]),
        "humidity_pct": float(values["RH"]),
        "pressure_hpa": float(values["BA"]),
    }


def write_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    tmp.replace(path)


def main() -> None:
    print(f"[collector] reading {PORT} @ {BAUD}, writing {OUT_FILE}")
    with serial.Serial(PORT, BAUD, timeout=2) as ser:
        mws_buffer: list[str] = []
        while True:
            raw = ser.readline().decode(errors="ignore").strip()
            if not raw:
                continue

            if LOG_RAW:
                print(f"[raw] {raw}")

            try:
                if raw == "SND":
                    message = "\n".join(mws_buffer)
                    mws_buffer.clear()
                    sample = parse_mws_message(message)
                elif mws_buffer or raw.startswith("MWS"):
                    mws_buffer.append(raw)
                    time.sleep(POLL_SLEEP_S)
                    continue
                else:
                    sample = parse_line(raw)
                write_atomic(OUT_FILE, sample)
                print(f"[ok] {sample}")
            except Exception as exc:  # keep collector resilient
                print(f"[skip] parse failed: {exc}")

            time.sleep(POLL_SLEEP_S)


if __name__ == "__main__":
    main()
