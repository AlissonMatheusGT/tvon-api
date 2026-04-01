import asyncio
import os
import re
import uvicorn
from typing import Tuple, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from camoufox.async_api import AsyncCamoufox
from playwright.async_api import TimeoutError as PlaywrightTimeoutError, Route
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="TVON - API de Automação de Testes IPTV")

fila_espera = asyncio.Semaphore(5) 

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
    },
    "ADAM": {
        "url": "https://paineladamplay.com/#/sign-in",
        "usuario": os.getenv("ADAM_USER"),
        "senha": os.getenv("ADAM_PASS"),
        "server_selector": 'div[data-test="server_id"] .el-select__wrapper',
        "plan_selector": 'div[data-test="package_id"] .el-select__wrapper',
        "nome_selector": 'input[data-test="name"]',
        "salvar_selector": 'button[type="submit"]',
        "menu_selector": 'a[href="#/customers"]',
        "nome_servidor": "AdamPlay",
        "regex_plano": r"TESTE GRÁTIS | 12 HORAS | COMPLETO"
    },
    "SPARK": {
        "url": "https://sparkpainel.top/#/dashboard",
        "usuario": os.getenv("SPARK_USER"),
        "senha": os.getenv("SPARK_PASS"),
        "server_selector": 'div[data-test="server_id"] .el-select__wrapper',
        "plan_selector": 'div[data-test="package_id"] .el-select__wrapper',
        "nome_selector": 'input[data-test="name"]',
        "salvar_selector": 'button[type="submit"]',
        "menu_selector": 'a[href="#/customers"]',
        "nome_servidor": "SPARK",
        "regex_plano": r"3 Horas Completo"
    },
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
    }
}

class TesteRequest(BaseModel):
    nome_cliente: str
    servidor_key: str
    ver_navegador: bool = False

def extract_credentials_robust(text: str) -> Tuple[Optional[str], Optional[str]]:
    clean_text = text.replace("*", "")
    u_match = re.search(r"(?:Usuário|User|Login)[^a-zA-Z0-9]+([a-zA-Z0-9]+)", clean_text, re.IGNORECASE)
    p_match = re.search(r"(?:Senha|Password|Pass)[^a-zA-Z0-9]+([a-zA-Z0-9]+)", clean_text, re.IGNORECASE)
    return (u_match.group(1) if u_match else None), (p_match.group(1) if p_match else None)

async def selecionar_menu_elementui(page, selector_dropdown: str, regex_busca: str) -> bool:
    for _ in range(3):
        try:
            await page.locator(selector_dropdown).click(force=True)
            await asyncio.sleep(1)
            
            encontrou = await page.evaluate(f"""(regexStr) => {{
                let regex = new RegExp(regexStr, 'i');
                let items = Array.from(document.querySelectorAll('li.el-select-dropdown__item')).filter(el => el.offsetParent !== null); 
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

async def abortar_recursos_pesados(route: Route):
    if route.request.resource_type in ["image", "media"]:
        await route.abort()
    else:
        await route.continue_()

async def gerar_teste_iptv_async(nome_cliente: str, servidor_key: str, ver_navegador: bool, max_retries: int = 3):
    cfg = CONFIG_PAINEIS.get(servidor_key.upper())
    if not cfg:
        return {"sucesso": False, "erro": f"Servidor {servidor_key} não configurado na API."}

    meu_proxy = {
        "server": os.getenv("PROXY_SERVER", "http://gw.dataimpulse.com:823"), 
        "username": os.getenv("PROXY_USER", "2b760a6d25e2df346719__cr.br"), 
        "password": os.getenv("PROXY_PASS", "abed057c1ea9b9f1")
    }

    for tentativa in range(1, max_retries + 1):
        try:
            print(f"🚀 Iniciando geração em {servidor_key} (Tentativa {tentativa})...")
            
            async with AsyncCamoufox(headless=not ver_navegador, proxy=meu_proxy, geoip=True) as browser:
                page = await browser.new_page()
                
                if not ver_navegador:
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
                    print(f"✅ Sucesso! Usuário: {u_iptv}")
                    return {"sucesso": True, "stdout": txt, "user": u_iptv, "pass": p_iptv}
                else:
                    raise Exception("Falha na extração heurística das credenciais.")

        except Exception as e:
            print(f"⚠️ Erro na iteração {tentativa}: {str(e)}")
            if tentativa == max_retries:
                return {"sucesso": False, "erro": str(e), "stdout": ""}
            await asyncio.sleep(2)

@app.post("/gerar-teste-ufo")
async def api_gerar_teste(payload: TesteRequest):
    async with fila_espera: 
        resultado = await gerar_teste_iptv_async(
            nome_cliente=payload.nome_cliente,
            servidor_key=payload.servidor_key,
            ver_navegador=payload.ver_navegador
        )
        
    if not resultado.get("sucesso"):
        raise HTTPException(status_code=500, detail=resultado.get("erro"))
        
    return resultado

if __name__ == "__main__":
    uvicorn.run("automations:app", host="0.0.0.0", port=8000)