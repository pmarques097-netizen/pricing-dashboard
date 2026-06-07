@echo off
cd /d "%~dp0"
echo Instalando/validando dependencias...
python -m pip install -r requirements.txt
echo.
echo Iniciando Eirox Dark Enterprise Premium...
streamlit run "dashboard_pricing_dark_enterprise_premium.py"
pause
