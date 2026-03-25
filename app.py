import sys
import os
sys.path.append(os.getcwd())

from flask import Flask, request, jsonify
import queue
import threading
from automations import gerar_teste_iptv

# Capturando o erro de forma segura
try:
    from tvon.automations import gerar_teste_iptv
except Exception as err:
    mensagem_erro = str(err)
    print(f"ERRO REAL DE IMPORTACAO: {mensagem_erro}")
    def gerar_teste_iptv(*args, **kwargs):
        q = args[-1]
        from dataclasses import dataclass
        @dataclass
        class ErrorEvent:
            kind: str = "error"
            payload: str = ""
            message: str = ""
        q.put(ErrorEvent(kind="error", payload=f"Falha ao carregar o automations.py: {mensagem_erro}", message="Erro"))

app = Flask(__name__)

@app.route("/gerar-teste-ufo", methods=["POST"])
def gerar_teste_ufo():
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
    
    # Timeout de 230 segundos para o n8n ter tempo de resposta
    t.join(timeout=230)

    final_payload = None
    erro_detalhado = None

    # Consumir a fila para pegar o resultado final
    while not q.empty():
        try:
            ev = q.get_nowait()
            if hasattr(ev, "kind"):
                if ev.kind == "credential_found":
                    # CORREÇÃO AQUI: Pegando 'stdout' que é o que o automations.py envia
                    final_payload = ev.payload
                elif ev.kind == "error":
                    erro_detalhado = str(ev.payload) if ev.payload else getattr(ev, 'message', 'Erro desconhecido')
        except queue.Empty:
            break

    if final_payload:
        # Retorna o JSON completo com user, pass e o texto original
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
