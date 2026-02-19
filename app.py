#!/usr/bin/env python3
"""Lightweight Streamlit UI for latest weather sample."""

from __future__ import annotations

import json
import os
from pathlib import Path

import streamlit as st

DATA_FILE = Path(os.getenv("WEATHER_OUT", "/tmp/weather/latest.json"))
REFRESH_SECONDS = int(os.getenv("WEATHER_UI_REFRESH", "2"))

st.set_page_config(page_title="Pi Weather", layout="centered")
st.title("Raspberry Pi Weather Station")
st.caption("Temperature, humidity, and pressure from USB weather station")

if "last_good" not in st.session_state:
    st.session_state.last_good = None

try:
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    st.session_state.last_good = data
except Exception:
    data = st.session_state.last_good

if data:
    col1, col2, col3 = st.columns(3)
    col1.metric("Temperature (°C)", f"{data['temperature_c']:.1f}")
    col2.metric("Humidity (%)", f"{data['humidity_pct']:.1f}")
    col3.metric("Pressure (hPa)", f"{data['pressure_hpa']:.1f}")
    st.caption(f"Last update (UTC): {data['ts']}")
else:
    st.info("Waiting for data from collector...")

st.caption(f"Auto refresh: every {REFRESH_SECONDS}s")
st.markdown(f"<meta http-equiv='refresh' content='{REFRESH_SECONDS}'>", unsafe_allow_html=True)
