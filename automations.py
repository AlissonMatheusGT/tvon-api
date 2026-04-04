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

fila_espera = asyncio.Semaphore(1) 

CONFIG_PAINEIS = {
    "UFO": { "url": "https://ufoplay.sigmab.pro/#/sign-in", "usuario": os.getenv("UFO_USER"), "senha": os.getenv("UFO_PASS"), "server_selector": 'div[data-test="server_id"] .el-select__wrapper', "plan_selector": 'div[data-test="package_id"] .el-select__wrapper', "nome_selector": 'input[data-test="name"]', "salvar_selector": 'button[type="submit"]', "menu_selector": 'a[href="#/customers"]', "nome_servidor": "UFO PLAY", "regex_plano": r"6 HORAS TESTE COM" },
    "SLIM": { "url": "https://painelslim.site/#/sign-in", "usuario": os.getenv("SLIM_USER"), "senha": os.getenv("SLIM_PASS"), "server_selector": 'div[data-test="server_id"] .el-select__wrapper', "plan_selector": 'div[data-test="package_id"] .el-select__wrapper', "nome_selector": 'input[data-test="name"]', "salvar_selector": 'button[type="submit"]', "menu_selector": 'a[href="#/customers"]', "nome_servidor": "IPTV", "regex_plano": r"TESTE 12 HORAS" },
    "SHAZAM": { "url": "https://shazamplay.com/#/sign-in", "usuario": os.getenv("SHAZAM_USER"), "senha": os.getenv("SHAZAM_PASS"), "server_selector": 'div[data-test="server_id"] .el-select__wrapper', "plan_selector": 'div[data-test="package_id"] .el-select__wrapper', "nome_selector": 'input[data-test="name"]', "salvar_selector": 'button[type="submit"]', "menu_selector": 'a[href="#/customers"]', "nome_servidor": "SHAZAM-PLAY", "regex_plano": r"12 HORAS" },
    "TIGER": { "url": "https://marinhoserver.click/#/sign-in", "usuario": os.getenv("TIGER_USER"), "senha": os.getenv("TIGER_PASS"), "server_selector": 'div[data-test="server_id"] .el-select__wrapper', "plan_selector": 'div[data-test="package_id"] .el-select__wrapper', "nome_selector": 'input[data-test="name"]', "salvar_selector": 'button[type="submit"]', "menu_selector": 'a[href="#/customers"]', "nome_servidor": "TIGRE AGILE PREMIUM", "regex_plano": r"TESTE TIGER PREMIUM PADRÃO" },
    "ADAM": { "url": "https://paineladamplay.com/#/sign-in", "usuario": os.getenv("ADAM_USER"), "senha": os.getenv("ADAM_PASS"), "server_selector": 'div[data-test="server_id"] .el-select__wrapper', "plan_selector": 'div[data-test="package_id"] .el-select__wrapper', "nome_selector": 'input[data-test="name"]', "salvar_selector": 'button[type="submit"]', "menu_selector": 'a[href="#/customers"]', "nome_servidor": "AdamPlay", "regex_plano": r"TESTE GRÁTIS | 12 HORAS | COMPLETO" },
    "SPARK": { "url": "https://sparkpainel.top/#/dashboard", "usuario": os.getenv("SPARK_USER"), "senha": os.getenv("SPARK_PASS"), "server_selector": 'div[data-test="server_id"] .el-select__wrapper', "plan_selector": 'div[data-test="package_id"] .el-select__wrapper', "nome_selector": 'input[data-test="name"]', "salvar_selector": 'button[type="submit"]', "menu_selector": 'a[href="#/customers"]', "nome_servidor": "SPARK", "regex_plano": r"3 Horas Completo" },
    "TOPCINE": { "url": "https://tv-top-cine.sigmab.pro/#/sign-in", "usuario": os.getenv("TOPCINE_USER"), "senha": os.getenv("TOPCINE_PASS"), "server_selector": 'div[data-test="server_id"] .el-select__wrapper', "plan_selector": 'div[data-test="package_id"] .el-select__wrapper', "nome_selector": 'input[data-test="name"]', "salvar_selector": 'button[type="submit"]', "menu_selector": 'a[href="#/customers"]', "nome_servidor": "Top Cine Revo", "regex_plano": r"Teste - completo c/ adultos 6h" }
}

class TesteRequest(BaseModel):
    nome_cliente: str
    servidor_key: str
    ver_navegador: bool = False

def extract_credentials_robust(text: str) -> Tuple[Optional[str], Optional[str]]:
    clean_text = re.sub(r'[*_`]', '', text) 
    u_match = re.search(r"(?:Usu[aá]rio|Username|User|Login)\s*[:➤-]?\s*(?:name|nome)?\s*[:➤-]?\s*([a-zA-Z0-9_]{3,})", clean_text, re.IGNORECASE)
    p_match = re.search(r"(?:Senha|Password|Pass\s*word|Pass)\s*[:➤-]?\s*([a-zA-Z0-9_]{3,})", clean_text, re.IGNORECASE)
    return (u_match.group(1) if u_match else None), (p_match.group(1) if p_match else None)

async def selecionar_menu_elementui(page, selector_dropdown: str, regex_busca: str) -> bool:
    for iteracao in range(3):
        try:
            await page.locator(selector_dropdown).wait_for(state="visible", timeout=20000)
            await page.locator(selector_dropdown).click(force=True)
            await asyncio.sleep(1.5) 
            itens_encontrados = await page.evaluate("""() => {
                return Array.from(document.querySelectorAll('li.el-select-dropdown__item')).filter(el => el.offsetParent !== null).map(el => el.innerText.trim());
            }""")
            encontrou = await page.evaluate(f"""(regexStr) => {{
                let regex = new RegExp(regexStr, 'i');
                let items = Array.from(document.querySelectorAll('li.el-select-dropdown__item')).filter(el => el.offsetParent !== null); 
                for (let el of items) {{ if (regex.test(el.innerText)) {{ el.scrollIntoView({{block: 'center'}}); el.click(); return true; }} }} return false;
            }}""", regex_busca)
            if encontrou: return True
            else: await page.keyboard.press("Escape"); await asyncio.sleep(1)
        except Exception: pass
    return False

async def gerar_teste_iptv_async(nome_cliente: str, servidor_key: str, ver_navegador: bool, max_retries: int = 3):
    cfg = CONFIG_PAINEIS.get(servidor_key.upper())
    if not cfg: return {"sucesso": False, "erro": f"Servidor {servidor_key} não configurado."}

    url_do_proxy = os.getenv("PROXY_URL")
    meu_proxy = None
    if url_do_proxy:
        try:
            clean = url_do_proxy.replace("http://", "").replace("https://", "")
            auth, addr = clean.split("@")
            user, pwd = auth.split(":")
            meu_proxy = {"server": f"http://{addr}", "username": user, "password": pwd}
        except Exception: meu_proxy = {"server": url_do_proxy}

    for tentativa in range(1, max_retries + 1):
        try:
            print(f"🚀 Iniciando geração em {servidor_key} (Tentativa {tentativa})...")
            async with AsyncCamoufox(headless=not ver_navegador, proxy=meu_proxy, geoip=True) as browser:
                page = await browser.new_page()
                await page.set_viewport_size({"width": 1366, "height": 768})
                
                # ⚡ VOLTOU PARA DOMCONTENTLOADED (IGUAL AO v7) PARA MAIS VELOCIDADE
                page.set_default_timeout(35000) 
                await page.goto(cfg["url"], wait_until="domcontentloaded", timeout=35000) 
                
                print("  [DEBUG] Tela acessada. Procurando input de senha...")
                await page.locator('input[type="password"]').first.wait_for(state="visible", timeout=25000)
                await page.locator('input[type="text"]:not([type="hidden"])').first.fill(cfg["usuario"])
                await page.locator('input[type="password"]').first.fill(cfg["senha"])
                await page.locator('#kt_sign_in_submit, button[type="submit"]').first.click()

                # 🩺 VOLTOU A LÓGICA DE LIMPEZA GENTIL (DO v7) + FORÇA BRUTA
                try:
                    await asyncio.sleep(2)
                    botoes_alerta = page.locator('button:has-text("Ocultar"), button:has-text("Ciente"), button:has-text("Entendi")')
                    for i in range(await botoes_alerta.count()):
                        if await botoes_alerta.nth(i).is_visible(): await botoes_alerta.nth(i).click(force=True)
                    await page.evaluate("""() => { document.querySelectorAll('.modal, .modal-backdrop, .el-overlay').forEach(el => el.remove()); }""")
                except: pass

                print("  [DEBUG] Login feito. Clicando no menu de clientes...")
                menu = page.locator(cfg['menu_selector']).first
                await menu.wait_for(state="attached", timeout=20000)
                await menu.click(force=True) 
                
                print("  [DEBUG] Menu clicado. Aguardando botão adicionar...")
                add_btn = page.locator("button:has-text('Adicionar'), a:has-text('Adicionar')").first
                await add_btn.wait_for(state="attached", timeout=20000)
                await add_btn.click(force=True) 
                
                print("  [DEBUG] Botão adicionar clicado! Selecionando servidor...")
                await page.locator(cfg['server_selector']).wait_for(state="visible", timeout=20000)
                
                regex_srv = rf"^\s*{re.escape(cfg['nome_servidor'])}\s*$"
                if not await selecionar_menu_elementui(page, cfg['server_selector'], regex_srv): raise Exception("Servidor não selecionado.")
                if not await selecionar_menu_elementui(page, cfg['plan_selector'], cfg['regex_plano']): raise Exception("Plano não selecionado.")

                print("  [DEBUG] Preenchendo nome...")
                nome_input = page.locator(cfg['nome_selector'])
                await nome_input.wait_for(state="visible")
                await nome_input.fill(nome_cliente)
                await page.locator(cfg['salvar_selector']).click(force=True) 

                print("  [DEBUG] Extraindo dados...")
                txt, u_iptv, p_iptv = "", None, None
                for _ in range(20): 
                    try:
                        containers = page.locator('.swal2-html-container, .el-message-box__content, .el-dialog__body, .modal-body, pre, .toast-message')
                        for i in range(await containers.count()):
                            cont = containers.nth(i)
                            if await cont.is_visible():
                                temp_txt = await cont.inner_text()
                                u_test, p_test = extract_credentials_robust(temp_txt)
                                if u_test and len(u_test) >= 3: txt, u_iptv, p_iptv = temp_txt, u_test, p_test; break
                    except Exception: pass
                    if u_iptv: break
                    await asyncio.sleep(1) 
                
                if u_iptv:
                    print(f"✅ Sucesso! Usuário: {u_iptv}")
                    return {"sucesso": True, "stdout": txt, "user": u_iptv, "pass": p_iptv}
                else: raise Exception("Falha na extração final.")

        except Exception as e:
            print(f"⚠️ Erro na iteração {tentativa}: {str(e)}")
            if tentativa == max_retries: return {"sucesso": False, "erro": str(e), "stdout": ""}
            await asyncio.sleep(2)

@app.post("/gerar-teste-ufo")
async def api_gerar_teste(payload: TesteRequest):
    async with fila_espera: 
        resultado = await gerar_teste_iptv_async(nome_cliente=payload.nome_cliente, servidor_key=payload.servidor_key, ver_navegador=payload.ver_navegador)
    if not resultado.get("sucesso"): raise HTTPException(status_code=500, detail=resultado.get("erro"))
    return resultado

if __name__ == "__main__":
    uvicorn.run("automations:app", host="0.0.0.0", port=8000)