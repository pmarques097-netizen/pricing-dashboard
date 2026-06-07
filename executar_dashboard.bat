@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt
streamlit run dashboard_pricing.py --server.headless true --logger.level error
pause
