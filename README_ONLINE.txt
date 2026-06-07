EIROX PRICING - ONLINE PRODUÇÃO

Esta versão foi preparada para rodar online com aparência mais profissional.

Arquivos incluídos:
- dashboard_pricing.py
- requirements.txt
- .streamlit/config.toml
- Procfile
- runtime.txt
- executar_dashboard_online_local.bat

O que foi ajustado:
- Modo dark configurado no Streamlit
- Logs do Streamlit reduzidos para error
- Menu superior oculto
- Footer oculto
- Botão Deploy oculto
- Toolbar ocultada
- Configuração pronta para Streamlit Cloud / Render / Railway

IMPORTANTE:
Os logs de build da plataforma podem aparecer apenas para você como administrador.
Para o usuário final do app, normalmente eles não aparecem após o app carregar.

Como publicar:
1. Envie estes arquivos para o GitHub.
2. No Streamlit Cloud, selecione dashboard_pricing.py como arquivo principal.
3. Garanta que Analise_Pricing.xlsx, pricing_utils.py e logo eirox.png estejam no repositório.
4. Faça deploy.

Execução local:
- Clique em executar_dashboard_online_local.bat
