@echo off
cd /d C:\Users\Comercial\Desktop\Pricing

REM E-mails que receberão aviso quando alguém fizer login
set LOGIN_EMAIL_DESTINO=pmarques097@gmail.com,paulomarquesintedados@gmail.com

REM Dados do e-mail remetente
set SMTP_HOST=smtp.gmail.com
set SMTP_PORT=465
set SMTP_USER=pmarques097@gmail.com

REM IMPORTANTE:
REM Coloque abaixo a SENHA DE APP do Gmail, não a senha normal do e-mail.
set SMTP_PASSWORD=eipzydnkmjzygrze

streamlit run dashboard_pricing.py

pause
