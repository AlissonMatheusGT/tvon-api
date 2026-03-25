import sys
import os
import re
import time
import queue
from dataclasses import dataclass
from typing import Dict, Any, Tuple, Optional
from camoufox.sync_api import Camoufox
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

@dataclass
class ProgressEvent:
    """
    Representa um evento de progresso durante o fluxo de automação.

    Attributes:
        percent (int): Percentual de conclusão da operação atual (0-100).
        message (str): Descrição do status atual ou etapa do fluxo.
        kind (str): Categoria do evento (ex: 'info', 'warning', 'error', 'credential_found').
            O valor default é 'info'.
        payload (Any): Estrutura de dados adicional contendo informações extraídas ou embutidas
            (ex: credenciais, logs estendidos). O valor default é None.
    """
    percent: int
    message: str
    kind: str = "info"
    payload: Any = None

# Mapeamento de configuração para os diferentes endpoints gerenciados.
# Cada entrada contém propriedades essenciais de parametrização de ambiente, 
# credenciais de acesso e seletores do DOM para interfaceamento via Playwright.
CONFIG_PAINEIS = {
    "UFO": {
        "url": "https://ufoplay.sigmab.pro/#/sign-in",
        "usuario": os.getenv("UFO_USER"),
        "senha": os.getenv("UFO_PASS"),
        "server_selector": 'div[data-test="server_id"] .el-select__wrapper',
        "plan_selector": 'div[data-test="package_id"] .el-select__wrapper',
        "nome_selector": 'input[data-test="name"]',
        "salvar_selector": 'button[type="submit"]',
        "menu_selector": 'a[href="#/customers"]',
        "nome_servidor": "UFO PLAY",
        "regex_plano": r"6 HORAS TESTE COM" 
    },
    "SLIM": {
        "url": "https://painelslim.site/#/sign-in",
        "usuario": os.getenv("SLIM_USER"),
        "senha": os.getenv("SLIM_PASS"),
        "server_selector": 'div[data-test="server_id"] .el-select__wrapper',
        "plan_selector": 'div[data-test="package_id"] .el-select__wrapper',
        "nome_selector": 'input[data-test="name"]',
        "salvar_selector": 'button[type="submit"]',
        "menu_selector": 'a[href="#/customers"]',
        "nome_servidor": "IPTV",
        "regex_plano": r"TESTE 12 HORAS"
    },
    "SHAZAM": {
        "url": "https://shazamplay.com/#/sign-in",
        "usuario": os.getenv("SHAZAM_USER"),
        "senha": os.getenv("SHAZAM_PASS"),
        "server_selector": 'div[data-test="server_id"] .el-select__wrapper',
        "plan_selector": 'div[data-test="package_id"] .el-select__wrapper',
        "nome_selector": 'input[data-test="name"]',
        "salvar_selector": 'button[type="submit"]',
        "menu_selector": 'a[href="#/customers"]',
        "nome_servidor": "SHAZAM-PLAY",
        "regex_plano": r"12 HORAS"
    },
    "TIGER": {
        "url": "https://marinhoserver.click/#/sign-in",
        "usuario": os.getenv("TIGER_USER"),
        "senha": os.getenv("TIGER_PASS"),
        "server_selector": 'div[data-test="server_id"] .el-select__wrapper',
        "plan_selector": 'div[data-test="package_id"] .el-select__wrapper',
        "nome_selector": 'input[data-test="name"]',
        "salvar_selector": 'button[type="submit"]',
        "menu_selector": 'a[href="#/customers"]',
        "nome_servidor": "TIGRE AGILE PREMIUM", 
        "regex_plano": r"TESTE TIGER PREMIUM PADRÃO"
    }
}

def extract_credentials_robust(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extrai instâncias originais de credenciais (usuário e senha) a partir de blocos de texto brutos
    utilizando heurísticas baseadas em expressões regulares.

    O algoritmo realiza uma varredura independente de formatação estrutural no texto fornecido,
    identificando padrões comuns de declaração de credenciais de acesso para a plataforma.

    Args:
        text (str): String com texto bruto capturado do DOM (ex: corpo de modais de confirmação).

    Returns:
        Tuple[Optional[str], Optional[str]]: Representação em tupla contendo validação de (usuário, senha).
        Retorna (None, None) caso as assinaturas padrão de credenciais não sejam identificadas no payload.
    """
    clean_text = text.replace("*", "")
    u_match = re.search(r"(?:Usuário|User|Login)[^a-zA-Z0-9]+([a-zA-Z0-9]+)", clean_text, re.IGNORECASE)
    p_match = re.search(r"(?:Senha|Password|Pass)[^a-zA-Z0-9]+([a-zA-Z0-9]+)", clean_text, re.IGNORECASE)
    u = u_match.group(1) if u_match else None
    p = p_match.group(1) if p_match else None
    return u, p

def selecionar_menu_elementui(page, selector_dropdown: str, regex_busca: str) -> bool:
    """
    Executa a seleção programática de um elemento em menu dropdown de componentes reativos (Element UI/Vue.js)
    utilizando injeção de script avaliativo de ambiente e matching computacional via expressões regulares.

    A rotina encapsula um mecanismo embutido de redundância orientada a polling passivo (retry-policy) nativo 
    para mitigar Race Conditions e flutuações de renderização do backend assíncrono.

    Args:
        page (playwright.sync_api.Page): Instância ativa de contexto da navegação do worker Playwright.
        selector_dropdown (str): Caminho localizador CSS do contêiner root ou gatilho do componente.
        regex_busca (str): Expressão regular configurada para matcheamento estrito contra a representação textual do nó-alvo.

    Returns:
        bool: Retorna True em caso de localização direta e respectivo dispatch do evento click com sucesso;
        False ao esgotar iterativamente o limitador do threshold recursivo.
    """
    for _ in range(3):
        try:
            page.locator(selector_dropdown).click(force=True)
            # Sistemas construtos com Element UI operam sob camada de transition states.
            # Este timeout fixado implementa supressor de offset desregulando falsos bindings visuais temporários.
            time.sleep(1) 
            
            # Executa runtime context bridge na V8 engine localizando e consumindo nós filhos.
            encontrou = page.evaluate(f"""(regexStr) => {{
                let regex = new RegExp(regexStr, 'i');
                let items = Array.from(document.querySelectorAll('li.el-select-dropdown__item'))
                                 .filter(el => el.offsetParent !== null); 
                for (let el of items) {{
                    if (regex.test(el.innerText)) {{
                        el.scrollIntoView({{block: 'center'}});
                        el.click();
                        return true;
                    }}
                }}
                return false;
            }}""", regex_busca)
            
            if encontrou:
                time.sleep(1) 
                return True
            else:
                page.keyboard.press("Escape") 
                time.sleep(1)
        except Exception:
            pass
    return False

def gerar_teste_iptv(nome_cliente: str, servidor_key: str, ver_navegador: bool, slot_destino: str, q: queue.Queue, max_retries: int = 3):
    """
    Orquestra o circuito end-to-end de alocação de acesso e onboarding automatizado para instâncias IPTV,
    estruturado sobre uma base Headless Chrome rodando Camoufox Engine para ofuscação de fingerprints.

    Implementa um runtime focado em prever anomalias transacionais, envolvendo bypass sistemático em alertas 
    contextuais do frontend, injeção cirúrgica nos seletores estáticos do DOM de sub-packages, e extração refinada.

    Args:
        nome_cliente (str): String identificadora requerida para associar ao tenant dinâmico a ser gerado.
        servidor_key (str): Chave enumerada referenciando indexações configuracionais em CONFIG_PAINEIS.
        ver_navegador (bool): Booleano indicando inibição arquitetural para runtime de instâncias em interface gráfica ativa.
        slot_destino (str): Variável relacional pass-through de roteamento (preservada para interfaces de telemetria externa).
        q (queue.Queue): Fila multi-thread (thread-safe) para telemetria e emissão de eventos assíncronos (ProgressEvent).
        max_retries (int, optional): Fator limitante para recuperação perante crashes nativos do alvo (Self-Healing). Padrão assume 3 tentativas.

    Returns:
        None: A função atua assincronamente através de postagem sequencial de chunks e payloads de estado no buffer `q`.
    """
    cfg = CONFIG_PAINEIS.get(servidor_key.upper())
    if not cfg:
        q.put(ProgressEvent(100, "Erro Crítico", kind="error", payload=f"Parâmetros de configuração ausentes para o namespace especificado: {servidor_key}."))
        return

    # Implementação tática de túnelhamento via rede proxy privada, objetivando pulverizar requests com
    # anonimização geo-direcional, reduzindo drasticamente pontos de bloqueio algorítmico impostos pelo WAF (Anti-Bot Pattern).
    meu_proxy = {
        "server": "http://gw.dataimpulse.com:823", 
        "username": "2b760a6d25e2df346719__cr.br", 
        "password": "abed057c1ea9b9f1"
    }

    # Bloco recursivo desenhado para fail-over imediato de threads em cenários de falha transacional da infraestrutura de rede externa.
    for tentativa in range(1, max_retries + 1):
        try:
            msg_tentativa = f" (Tentativa {tentativa}/{max_retries})" if tentativa > 1 else ""
            q.put(ProgressEvent(10, f"Iniciando {servidor_key.upper()}{msg_tentativa}..."))
            
            with Camoufox(headless=not ver_navegador, proxy=meu_proxy, geoip=True) as browser:
                page = browser.new_page()
                page.set_default_timeout(30000) 
                
                q.put(ProgressEvent(20, "Estabelecendo handshake TCP/TLS e despachando payload de autenticação inicial da sessão..."))
                page.goto(cfg["url"], wait_until="domcontentloaded") 
                
                page.locator('input[type="password"]').wait_for(state="visible", timeout=20000)
                page.locator('input[type="text"]:not([type="hidden"])').first.fill(cfg["usuario"])
                page.locator('input[type="password"]').fill(cfg["senha"])
                page.locator('#kt_sign_in_submit').click()

                q.put(ProgressEvent(30, "Executando varredura DOM e supressão hierárquica de modais informativos intrusivos ao pipeline..."))
                try:
                    page.locator('button:has-text("Ocultar"), button:has-text("Ciente"), button:has-text("Entendi"), .modal-content').first.wait_for(state="attached", timeout=3500)
                    page.keyboard.press("Escape")
                    botoes_alerta = page.locator('button:has-text("Ocultar"), button:has-text("Ciente"), button:has-text("Entendi"), button[title="Dispensar alerta"], button:has-text("OK"), button:has-text("FECHAR")')
                    for i in range(botoes_alerta.count()):
                        if botoes_alerta.nth(i).is_visible():
                            botoes_alerta.nth(i).click(force=True)
                except PlaywrightTimeoutError:
                    pass

                q.put(ProgressEvent(40, "Acionando deep links estáticos e instanciando formulários SPA de alocação de infraestrutura..."))
                menu = page.locator(cfg['menu_selector']).first
                menu.wait_for(state="visible")
                menu.click(force=True)
                
                add_btn = page.locator("button:has-text('Adicionar'), a:has-text('Adicionar')").first
                add_btn.wait_for(state="visible")
                add_btn.click(force=True)
                
                q.put(ProgressEvent(60, "Parametrizando constraints de Infraestrutura (Edge Servers e Sub-Packages)..."))
                
                regex_srv = rf"^\s*{re.escape(cfg['nome_servidor'])}\s*$"
                sucesso_srv = selecionar_menu_elementui(page, cfg['server_selector'], regex_srv)
                if not sucesso_srv: raise Exception(f"Servidor não selecionado.")

                sucesso_plano = selecionar_menu_elementui(page, cfg['plan_selector'], cfg['regex_plano'])
                if not sucesso_plano: raise Exception(f"Plano não selecionado.")

                q.put(ProgressEvent(80, "Consolidando propriedades e processando commit do endpoint via requisição AJAX mutante..."))
                nome_input = page.locator(cfg['nome_selector'])
                nome_input.wait_for(state="visible")
                nome_input.fill(nome_cliente)
                
                page.locator(cfg['salvar_selector']).click(force=True)

                # -------------------------------------------------------------------------
                # Fase de Pipeline: Interceptação e Parsing de DOM para Captura de Sessão
                # -------------------------------------------------------------------------
                q.put(ProgressEvent(90, "Rotina de parsing serial e extração segura de credenciais ativada..."))
                
                # Resolução de escopo do Node Tree: Foca diretamente e com rigor taxonômico estrito
                # em contêineres atrelados a modais ativados por overlays de foreground.
                modal_container = page.locator('.modal-body:visible, .el-dialog__body:visible, .swal2-html-container:visible').last
                modal_container.wait_for(state="visible", timeout=30000)
                
                # Gap programado de sincronização algorítmica. (Mitigação de Race Conditions via pooling passivo compensatório ao AJAX load delay).
                time.sleep(3)
                
                try:
                    # Injeção sandbox guiada por pseudo-elementos estruturais para extrair a matriz textual 
                    # do núcleo formatado. Suprime poluição visual da árvore em favor de processamento de máquina limpo.
                    caixa_texto = modal_container.locator('.pre, pre, [style*="white-space: pre-wrap"]').first
                    caixa_texto.wait_for(state="visible", timeout=2000)
                    txt = caixa_texto.inner_text()
                except PlaywrightTimeoutError:
                    # Rota de redundância estocástica: extração completa da área legível por fall-back quando a formatação standard diverge na plataforma.
                    txt = modal_container.inner_text()
                
                u_iptv, p_iptv = extract_credentials_robust(txt)

                # Controle final de sanidade nos vetores para proteção estrutural e validação pós-parsing.
                if u_iptv and len(u_iptv) >= 3:
                    q.put(ProgressEvent(100, "Processamento de Alocação Concluído com Sucesso do Pipeline", kind="credential_found", payload={"user": u_iptv, "pass": p_iptv, "stdout": txt}))
                    return
                else:
                    raise Exception(f"Exception Analítica: As expressões lógicas heurísticas restaram comprometidas sobre a extração base: {txt[:100]}...")
                # -------------------------------------------------------------------------

        except Exception as e:
            q.put(ProgressEvent(80, f"Exceção capturada na thread de roteamento (Iteração {tentativa}): {str(e)}", kind="warning"))
            if tentativa == max_retries:
                q.put(ProgressEvent(100, "Crash Estrutural / Esgotamento de Retry Policy", kind="error", payload=f"Target {servidor_key} excedeu o limite arquitetural de tolerância ({max_retries} max attempts). Trace Dump: {str(e)}"))
                return
            time.sleep(2)
