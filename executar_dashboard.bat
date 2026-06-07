@echo off
cd /d "%~dp0"
echo Instalando/validando dependencias...
python -m pip install -r requirements.txt
echo.
echo Iniciando Eirox Pricing...
streamlit run "dashboard_pricing.py"
pause
