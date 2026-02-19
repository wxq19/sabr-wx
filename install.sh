#!/usr/bin/env bash
set -euo pipefail

sudo apt-get update
sudo apt-get install -y python3-venv python3-pip python3-serial usbutils

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "Install complete."
echo "Next:"
echo "  1) source .venv/bin/activate"
echo "  2) WEATHER_PORT=/dev/ttyUSB0 python collector.py"
echo "  3) streamlit run app.py --server.address 0.0.0.0 --server.port 8501"
