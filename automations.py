import asyncio
import os
import re
from dataclasses import dataclass
from typing import Dict, Any, Tuple, Optional
from camoufox.async_api import AsyncCamoufox # Mudança crucial para API
from playwright.async_api import TimeoutError as PlaywrightTimeoutError, Route
from dotenv import load_dotenv

load_dotenv()

@dataclass
class ProgressEvent:
    percent: int
    message: str
    kind: str = "info"
    payload: Any = None

CONFIG_PAINEIS = {
    # (Mantenha o seu dicionário CONFIG_PAINEIS exatamente como estava)
    "TOPCINE": {
        "url": "https://tv-top-cine.sigmab.pro/#/sign-in",
        "usuario": os.getenv("TOPCINE_USER"),
        "senha": os.getenv("TOPCINE_PASS"),
        "server_selector": 'div[data-test="server_id"] .el-select__wrapper',
        "plan_selector": 'div[data-test="package_id"] .el-select__wrapper',
        "nome_selector": 'input[data-test="name"]',
        "salvar_selector": 'button[type="submit"]',
        "menu_selector": 'a[href="#/customers"]',
        "nome_servidor": "Top Cine Revo",
        "regex_plano": r"Teste - completo c/ adultos 6h"
    },
    # Adicione os outros aqui...
}

def extract_credentials_robust(text: str) -> Tuple[Optional[str], Optional[str]]:
    clean_text = text.replace("*", "")
    u_match = re.search(r"(?:Usuário|User|Login)[^a-zA-Z0-9]+([a-zA-Z0-9]+)", clean_text, re.IGNORECASE)
    p_match = re.search(r"(?:Senha|Password|Pass)[^a-zA-Z0-9]+([a-zA-Z0-9]+)", clean_text, re.IGNORECASE)
    return (u_match.group(1) if u_match else None), (p_match.group(1) if p_match else None)

# Refatorado para Asyncio
async def selecionar_menu_elementui(page, selector_dropdown: str, regex_busca: str) -> bool:
    for _ in range(3):
        try:
            await page.locator(selector_dropdown).click(force=True)
            await asyncio.sleep(1) # Substituindo time.sleep
            
            encontrou = await page.evaluate(f"""(regexStr) => {{
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
                await asyncio.sleep(1) 
                return True
            else:
                await page.keyboard.press("Escape") 
                await asyncio.sleep(1)
        except Exception:
            pass
    return False

# Interceptador Assíncrono para a "Dieta da VPS"
async def abortar_recursos_pesados(route: Route):
    if route.request.resource_type in ["image", "media", "font", "stylesheet"]:
        await route.abort()
    else:
        await route.continue_()

async def gerar_teste_iptv_async(nome_cliente: str, servidor_key: str, ver_navegador: bool, max_retries: int = 3):
    cfg = CONFIG_PAINEIS.get(servidor_key.upper())
    if not cfg:
        return {"sucesso": False, "erro": "Servidor não configurado"}

    meu_proxy = {
        "server": "http://gw.dataimpulse.com:823", 
        "username": "2b760a6d25e2df346719__cr.br", 
        "password": "abed057c1ea9b9f1"
    }

    for tentativa in range(1, max_retries + 1):
        try:
            # Aqui mora a mágica da performance e da API
            async with AsyncCamoufox(headless=not ver_navegador, proxy=meu_proxy, geoip=True) as browser:
                page = await browser.new_page()
                
                # A Dieta da VPS ativada! Vai poupar muita RAM.
                await page.route("**/*", abortar_recursos_pesados)
                
                page.set_default_timeout(30000) 
                
                await page.goto(cfg["url"], wait_until="domcontentloaded") 
                
                await page.locator('input[type="password"]').wait_for(state="visible", timeout=20000)
                await page.locator('input[type="text"]:not([type="hidden"])').first.fill(cfg["usuario"])
                await page.locator('input[type="password"]').fill(cfg["senha"])
                await page.locator('#kt_sign_in_submit').click()

                try:
                    await page.locator('button:has-text("Ocultar"), button:has-text("Ciente"), button:has-text("Entendi"), .modal-content').first.wait_for(state="attached", timeout=3500)
                    await page.keyboard.press("Escape")
                    botoes_alerta = page.locator('button:has-text("Ocultar"), button:has-text("Ciente"), button:has-text("Entendi"), button[title="Dispensar alerta"], button:has-text("OK"), button:has-text("FECHAR")')
                    count = await botoes_alerta.count()
                    for i in range(count):
                        if await botoes_alerta.nth(i).is_visible():
                            await botoes_alerta.nth(i).click(force=True)
                except PlaywrightTimeoutError:
                    pass

                menu = page.locator(cfg['menu_selector']).first
                await menu.wait_for(state="visible")
                await menu.click(force=True)
                
                add_btn = page.locator("button:has-text('Adicionar'), a:has-text('Adicionar')").first
                await add_btn.wait_for(state="visible")
                await add_btn.click(force=True)
                
                regex_srv = rf"^\s*{re.escape(cfg['nome_servidor'])}\s*$"
                if not await selecionar_menu_elementui(page, cfg['server_selector'], regex_srv): 
                    raise Exception("Servidor não selecionado.")

                if not await selecionar_menu_elementui(page, cfg['plan_selector'], cfg['regex_plano']): 
                    raise Exception("Plano não selecionado.")

                nome_input = page.locator(cfg['nome_selector'])
                await nome_input.wait_for(state="visible")
                await nome_input.fill(nome_cliente)
                
                await page.locator(cfg['salvar_selector']).click(force=True)

                modal_container = page.locator('.modal-body:visible, .el-dialog__body:visible, .swal2-html-container:visible').last
                await modal_container.wait_for(state="visible", timeout=30000)
                await asyncio.sleep(3)
                
                try:
                    caixa_texto = modal_container.locator('.pre, pre, [style*="white-space: pre-wrap"]').first
                    await caixa_texto.wait_for(state="visible", timeout=2000)
                    txt = await caixa_texto.inner_text()
                except PlaywrightTimeoutError:
                    txt = await modal_container.inner_text()
                
                u_iptv, p_iptv = extract_credentials_robust(txt)

                if u_iptv and len(u_iptv) >= 3:
                    # Retorno limpo para a sua API devolver ao n8n
                    return {"sucesso": True, "stdout": txt, "user": u_iptv, "pass": p_iptv}
                else:
                    raise Exception("Falha na extração heurística.")

        except Exception as e:
            print(f"Tentativa {tentativa} falhou: {str(e)}")
            if tentativa == max_retries:
                return {"sucesso": False, "erro": str(e), "stdout": ""}
            await asyncio.sleep(2)

# =========================================================
# EXEMPLO DE COMO CHAMAR ISSO NA SUA API (FASTAPI)
# =========================================================
# @app.post("/gerar-teste-ufo")
# async def api_gerar_teste(payload: RequestPayload):
#     resultado = await gerar_teste_iptv_async(
#         nome_cliente=payload.nome_cliente,
#         servidor_key=payload.servidor_key,
#         ver_navegador=False # Sempre False em produção!
#     )
#     return resultado