#!/usr/bin/env python3
"""USB weather-station collector.

Reads serial data from WEATHER_PORT and writes latest parsed sample to JSON.
Supports both compact CSV lines (e.g. T=23.4,H=56.1,P=1012.8)
and AMWS-style multiline frames with keys like TA/BA/RH.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

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
        "ta": "temperature",  # AMWS ambient temperature
        "h": "humidity",
        "hum": "humidity",
        "humidity": "humidity",
        "rh": "humidity",  # AMWS relative humidity
        "p": "pressure",
        "pres": "pressure",
        "pressure": "pressure",
        "ba": "pressure",  # AMWS barometric pressure
    }
    normalized: Dict[str, str] = {}
    for key, value in payload.items():
        clean_key = key.strip().lower()
        if clean_key in alias:
            normalized[alias[clean_key]] = value.strip()
    return normalized


def _build_sample(payload: Dict[str, str]) -> dict:
    data = _normalize_keys(payload)
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "temperature_c": float(data["temperature"]),
        "humidity_pct": float(data["humidity"]),
        "pressure_hpa": float(data["pressure"]),
    }


def parse_line(line: str) -> dict:
    """Parse compact line format like T=23.4,H=56.1,P=1012.8."""
    chunks = [x.strip() for x in line.split(",") if "=" in x]
    kv = dict(chunk.split("=", 1) for chunk in chunks)
    return _build_sample(kv)


def parse_amws_frame(lines: list[str]) -> dict:
    """Parse AMWS multiline payload and extract TA, RH, BA values.

    Example lines include: TA:22.4, BA:1001.90, RH:50
    """
    kv: Dict[str, str] = {}
    for line in lines:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        kv[key.strip()] = value.strip().split(":", 1)[0]
    return _build_sample(kv)


def write_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    tmp.replace(path)


def _try_parse_single(raw: str) -> Optional[dict]:
    try:
        return parse_line(raw)
    except Exception:
        return None


def main() -> None:
    print(f"[collector] reading {PORT} @ {BAUD}, writing {OUT_FILE}")
    frame: list[str] = []

    with serial.Serial(PORT, BAUD, timeout=2) as ser:
        while True:
            raw = ser.readline().decode(errors="ignore").strip()
            if not raw:
                continue

            if LOG_RAW:
                print(f"[raw] {raw}")

            single_sample = _try_parse_single(raw)
            if single_sample:
                write_atomic(OUT_FILE, single_sample)
                print(f"[ok] {single_sample}")
                time.sleep(POLL_SLEEP_S)
                continue

            frame.append(raw)

            # AMWS packets commonly terminate with '~'.
            if raw == "~":
                try:
                    sample = parse_amws_frame(frame)
                    write_atomic(OUT_FILE, sample)
                    print(f"[ok] {sample}")
                except Exception as exc:
                    print(f"[skip] frame parse failed: {exc}")
                finally:
                    frame.clear()

            # Prevent unbounded growth if frame end marker is missing.
            if len(frame) > 300:
                frame = frame[-50:]

            time.sleep(POLL_SLEEP_S)


if __name__ == "__main__":
    main()
