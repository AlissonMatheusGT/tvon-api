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

# 🛡️ PROTEÇÃO DE MEMÓRIA DA VPS
fila_espera = asyncio.Semaphore(2) 

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
    print(f"  [DEBUG] Tentando clicar no dropdown: {selector_dropdown}")
    for iteracao in range(3):
        try:
            await page.locator(selector_dropdown).wait_for(state="visible", timeout=20000)
            await page.locator(selector_dropdown).click(force=True)
            await asyncio.sleep(2) 
            
            itens_encontrados = await page.evaluate("""() => {
                return Array.from(document.querySelectorAll('li.el-select-dropdown__item'))
                            .filter(el => el.offsetParent !== null)
                            .map(el => el.innerText.trim());
            }""")
            print(f"  [DEBUG] Itens lidos na tela (Tentativa {iteracao+1}): {itens_encontrados}")

            encontrou = await page.evaluate(f"""(regexStr) => {{
                let regex = new RegExp(regexStr, 'i');
                let items = Array.from(document.querySelectorAll('li.el-select-dropdown__item')).filter(el => el.offsetParent !== null); 
                for (let el of items) {{
                    if (regex.test(el.innerText)) {{ el.scrollIntoView({{block: 'center'}}); el.click(); return true; }}
                }} return false;
            }}""", regex_busca)
            
            if encontrou: 
                print(f"  [DEBUG] ✅ Sucesso! Encontrou correspondência para '{regex_busca}'")
                await asyncio.sleep(1)
                return True
            else: 
                print(f"  [DEBUG] ❌ Não achou '{regex_busca}'. Fechando menu e tentando de novo...")
                await page.keyboard.press("Escape")
                await asyncio.sleep(1)
        except Exception as e: 
            print(f"  [DEBUG] Erro interno no dropdown: {str(e)}")
    return False

async def abortar_recursos_pesados(route: Route):
    if route.request.resource_type in ["image", "media", "font"]:
        await route.abort()
    else:
        await route.continue_()

async def gerar_teste_iptv_async(nome_cliente: str, servidor_key: str, ver_navegador: bool, max_retries: int = 3):
    cfg = CONFIG_PAINEIS.get(servidor_key.upper())
    if not cfg: return {"sucesso": False, "erro": f"Servidor {servidor_key} não configurado."}

    meu_proxy = {"server": os.getenv("PROXY_SERVER", "http://gw.dataimpulse.com:823"), "username": os.getenv("PROXY_USER", "2b760a6d25e2df346719__cr.br"), "password": os.getenv("PROXY_PASS", "abed057c1ea9b9f1")}

    for tentativa in range(1, max_retries + 1):
        try:
            print(f"🚀 Iniciando geração em {servidor_key} (Tentativa {tentativa})...")
            
            # PREVENÇÃO 3: Forçar Viewport Desktop para garantir que o menu lateral sempre exista
            async with AsyncCamoufox(headless=not ver_navegador, proxy=meu_proxy, geoip=True) as browser:
                page = await browser.new_page()
                
                # ADICIONADO AQUI: Força a tela de desktop
                await page.set_viewport_size({"width": 1366, "height": 768})
                
                if not ver_navegador: await page.route("**/*", abortar_recursos_pesados)
                
                page.set_default_timeout(25000) 
                await page.goto(cfg["url"], wait_until="domcontentloaded", timeout=25000) 
                
                print("  [DEBUG] Tela acessada. Procurando input de senha...")
                await page.locator('input[type="password"]').first.wait_for(state="visible", timeout=20000)
                await page.locator('input[type="text"]:not([type="hidden"])').first.fill(cfg["usuario"])
                await page.locator('input[type="password"]').first.fill(cfg["senha"])
                
                # PREVENÇÃO 2: Aguardar o painel realmente navegar após o login
                await page.locator('#kt_sign_in_submit, button[type="submit"]').first.click()
                await page.wait_for_url("**/dashboard**", timeout=20000)

                try:
                    await page.locator('button:has-text("Ocultar"), button:has-text("Ciente"), .modal-content').first.wait_for(state="visible", timeout=5000)
                    await page.keyboard.press("Escape")
                    botoes_alerta = page.locator('button:has-text("Ocultar"), button:has-text("Ciente"), button:has-text("Entendi")')
                    for i in range(await botoes_alerta.count()):
                        if await botoes_alerta.nth(i).is_visible(): 
                            await botoes_alerta.nth(i).click(force=True)
                except PlaywrightTimeoutError: 
                    pass

                print("  [DEBUG] Login feito. Clicando no menu de clientes...")
                menu = page.locator(cfg['menu_selector']).first
                # Alterado de "attached" para "visible". Se não estiver visível, o clique falha.
                await menu.wait_for(state="visible", timeout=20000)
                await menu.click() # Removido o force=True
                
                print("  [DEBUG] Menu clicado. Aguardando a página de clientes estabilizar...")
                # PREVENÇÃO 1: Remover force=True do Adicionar e garantir que não há overlay
                add_btn = page.locator("button:has-text('Adicionar'), a:has-text('Adicionar')").first
                await add_btn.wait_for(state="visible", timeout=20000)
                
                # Pequeno delay para painéis pesados renderizarem os Event Listeners (Vue/React)
                await asyncio.sleep(1.5) 
                
                # Clica como um humano. Se falhar, o Playwright avisa (ao invés de clicar no vazio)
                await add_btn.click() 
                
                print("  [DEBUG] Botão adicionar clicado! Aguardando a janela modal renderizar...")
                # Adicionamos uma verificação da própria modal/dialog antes de procurar o dropdown
                await page.locator('.modal-dialog:visible, .el-dialog:visible').first.wait_for(state="visible", timeout=15000)
                
                await page.locator(cfg['server_selector']).wait_for(state="visible", timeout=20000)
                
                regex_srv = rf"^\s*{re.escape(cfg['nome_servidor'])}\s*$"
                if not await selecionar_menu_elementui(page, cfg['server_selector'], regex_srv): raise Exception("Servidor não selecionado.")
                if not await selecionar_menu_elementui(page, cfg['plan_selector'], cfg['regex_plano']): raise Exception("Plano não selecionado.")

                print("  [DEBUG] Preenchendo nome...")
                nome_input = page.locator(cfg['nome_selector'])
                await nome_input.wait_for(state="visible")
                await nome_input.fill(nome_cliente)
                await page.locator(cfg['salvar_selector']).click() # Removido o force=True

                print("  [DEBUG] Botão salvar clicado. Extraindo dados...")
                modal_container = page.locator('.modal-body:visible, .el-dialog__body:visible, .swal2-html-container:visible').last
                await modal_container.wait_for(state="visible", timeout=20000)
                
                
                txt = ""
                for _ in range(15):
                    try:
                        caixa_texto = modal_container.locator('.pre, pre, [style*="white-space: pre-wrap"]').first
                        txt = await caixa_texto.inner_text() if await caixa_texto.is_visible() else await modal_container.inner_text()
                    except Exception:
                        txt = await modal_container.inner_text()
                    if "Usu" in txt or "User" in txt or "Login" in txt or "Senha" in txt: break
                    await asyncio.sleep(1)
                
                u_iptv, p_iptv = extract_credentials_robust(txt)
                if u_iptv and len(u_iptv) >= 3:
                    print(f"✅ Sucesso! Usuário: {u_iptv}")
                    return {"sucesso": True, "stdout": txt, "user": u_iptv, "pass": p_iptv}
                else: raise Exception("Falha na extração das credenciais (painel demorou).")

        except Exception as e:
            print(f"⚠️ Erro na iteração {tentativa}: {str(e)}")
            try:
                nome_foto = f"debug_erro_{servidor_key}_tent_{tentativa}.png"
                await page.screenshot(path=nome_foto, full_page=True)
                print(f"  [DEBUG] 📸 Foto do erro salva no arquivo: {nome_foto}")
            except: pass
            
            if tentativa == max_retries: return {"sucesso": False, "erro": str(e), "stdout": ""}
            await asyncio.sleep(1.5)

@app.post("/gerar-teste-ufo")
async def api_gerar_teste(payload: TesteRequest):
    async with fila_espera: 
        resultado = await gerar_teste_iptv_async(nome_cliente=payload.nome_cliente, servidor_key=payload.servidor_key, ver_navegador=payload.ver_navegador)
    if not resultado.get("sucesso"): raise HTTPException(status_code=500, detail=resultado.get("erro"))
    return resultado

if __name__ == "__main__":
    uvicorn.run("automations:app", host="0.0.0.0", port=8000)