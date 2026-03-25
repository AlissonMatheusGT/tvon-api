# 🚀 TVON Automation API - Automated IPTV Trial System

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Flask](https://img.shields.io/badge/flask-%23000.svg?style=for-the-badge&logo=flask&logoColor=white)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-2EAD33?style=for-the-badge&logo=Playwright&logoColor=white)
![n8n](https://img.shields.io/badge/n8n-FF6C37?style=for-the-badge&logo=n8n&logoColor=white)

Esta é uma API robusta desenvolvida para automatizar a geração de testes (trials) em múltiplos painéis de IPTV (UFO, SLIM, SHAZAM, TIGER). O sistema foi projetado para operar como o motor de backend de um funil de vendas automatizado, integrando-se perfeitamente com **n8n**, **Typebot** e **WhatsApp Business**.

## 🧠 Arquitetura da Solução

O projeto utiliza uma abordagem de **Web Scraping Avançado** com foco em resiliência e anti-detecção:

* **Engine de Automação:** [Camoufox](https://github.com/ichano/camoufox) (baseado em Playwright) para emular impressões digitais de navegadores reais e evitar bloqueios.
* **Gestão de Sessão:** Roteamento de tráfego via **Proxy Residencial** (DataImpulse) para garantir alta taxa de sucesso nas requisições.
* **Orquestração:** O fluxo de entrada é gerenciado pelo **n8n**, que aciona este backend via requisições REST (POST).
* **Infraestrutura:** Containerizado com **Docker** e gerenciado via **EasyPanel (VPS)**, garantindo deploys contínuos e isolamento de ambiente.

## ✨ Principais Funcionalidades

- [x] **Multi-Painel:** Suporte nativo para múltiplos provedores com seletores dinâmicos.
- [x] **Evasão de Detecção:** Implementação de técnicas SRE para contornar Cloudflare e outros WAFs.
- [x] **Extração Cirúrgica:** Regex avançado para capturar credenciais diretamente do DOM/Modais.
- [x] **Event-Driven Progress:** Sistema de fila (`queue`) para monitoramento de progresso em tempo real.
- [x] **Segurança:** Gestão de credenciais via variáveis de ambiente (`python-dotenv`).

## 🛠️ Tecnologias Utilizadas

* **Linguagem:** Python 3.12+
* **Web Framework:** Flask (Gunicorn em produção)
* **Browser Automation:** Playwright / Camoufox
* **Infra:** Docker, EasyPanel, VPS Linux
* **Workflow:** n8n, Typebot

## 🔐 Segurança e Boas Práticas

Este repositório segue os padrões de segurança da indústria:
- **Zero Hardcoded Secrets:** Todas as credenciais de painéis e proxies são injetadas via Variáveis de Ambiente.
- **Git Hygiene:** Histórico de commits limpo e arquivo `.env` devidamente ignorado via `.gitignore`.
- **Error Handling:** Sistema de *retry* automático para falhas temporárias de rede ou timeout de painéis.

## 🚀 Como Executar (Localmente)

1. Clone o repositório:
   ```bash
   git clone [https://github.com/AlissonMatheusGT/tvon-api.git](https://github.com/AlissonMatheusGT/tvon-api.git)
Instale as dependências:

Bash
pip install -r requirements.txt
Configure o arquivo .env baseado no .env.example.

Execute o script de teste:

Bash
python automations.py
Desenvolvido por Alisson Matheus Solutions Architect & DevOps/SRE Engineer