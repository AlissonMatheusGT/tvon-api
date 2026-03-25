import sys
import os
sys.path.append(os.getcwd())

from flask import Flask, request, jsonify
import queue
import threading

# Importação direta, já que os arquivos estão na mesma pasta
try:
    from automations import gerar_teste_iptv
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