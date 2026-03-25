import sys
import os
sys.path.append(os.getcwd())

from flask import Flask, request, jsonify
import queue
import threading

# Resolução de dependências do módulo core com fallback estrito de injeção defensiva (Defensive Programming).
# Garante a integridade parcial de boot do gateway da aplicação mesmo frente a falhas de parser no builder Headless.
try:
    from automations import gerar_teste_iptv
except Exception as err:
    mensagem_erro = str(err)
    print(f"Stacktrace de falha na resolução de módulos nativos do kernel: {mensagem_erro}")
    def gerar_teste_iptv(*args, **kwargs):
        q = args[-1]
        from dataclasses import dataclass
        @dataclass
        class ErrorEvent:
            kind: str = "error"
            payload: str = ""
            message: str = ""
        q.put(ErrorEvent(kind="error", payload=f"Falha ao carregar o automations.py: {mensagem_erro}", message="Erro"))

# Instância WSGI root designada para vinculação pass-through com Application Servers robustos (ex: Gunicorn).
app = Flask(__name__)

@app.route("/gerar-teste-ufo", methods=["POST"])
def gerar_teste_ufo():
    """
    Endpoint/Webhook para orquestração assíncrona do serviço de provisioning de instâncias IPTV.

    Consome payloads de entrada HTTP POST (padronizados por motores de automação orquestrada como n8n)
    e comissiona a rotina profunda do framework Headless (Camoufox) via injeção de uma thread não-bloqueante genérica,
    impondo sincronização forçada baseada em Strict Timeouts.

    Returns:
        tuple[flask.Response, int]: Envelope JSON portando status estrutural das propriedades (success states
        e payloads descriptografados) atrelado diretamente aos HTTP Headers base de confirmação da transação.
    """
    data = request.get_json(force=True, silent=True) or {}
    
    nome_cliente = data.get("nome_cliente", "CELULAR_TESTE")
    servidor_key = data.get("servidor_key", "UFO")

    q = queue.Queue()
    t = threading.Thread(
        target=gerar_teste_iptv,
        args=(nome_cliente, servidor_key, False, servidor_key, q),
        daemon=True
    )
    t.start()
    
    # Limitação limitadora de TTL (Time-To-Live) injetada garantindo a sincronia global contra timeouts 
    # de fluxos externos acoplados à API Gateway do projeto (threshold de instâncias n8n).
    t.join(timeout=230)

    final_payload = None
    erro_detalhado = None

    # Loop de drenagem do barramento de eventos/telemetria para resgate retrospectivo do State Component nativo.
    while not q.empty():
        try:
            ev = q.get_nowait()
            if hasattr(ev, "kind"):
                if ev.kind == "credential_found":
                    final_payload = ev.payload
                elif ev.kind == "error":
                    erro_detalhado = str(ev.payload) if ev.payload else getattr(ev, 'message', 'Erro desconhecido')
        except queue.Empty:
            break

    if final_payload:
        # Devolve interface de resposta acoplando diretamente os chaves atreladas em ambiente seguro.
        return jsonify({
            "sucesso": True, 
            "user": final_payload.get("user"),
            "pass": final_payload.get("pass"),
            "stdout": final_payload.get("stdout")
        }), 200
    else:
        return jsonify({
            "sucesso": False, 
            "stdout": "", 
            "erro": erro_detalhado or "O robô não retornou dados (Timeout ou Falha Silenciosa)"
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)