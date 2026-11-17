"""
REFÚGIO - API de teste (local) do endpoint de ingestão de medições.

Substitui a API Java/Spring Boot proposta para que o gateway possa ser testado
sem nuvem e sem banco. Usa o MESMO contrato de validação do gateway (contrato.py).

ATENÇÃO: os dados ficam somente em memória. Ao encerrar a API, tudo se perde.
Isto NÃO é persistência em PostgreSQL.

Rotas:
  POST /api/medicoes          -> 201 (aceita) | 400 | 401 | 422
  GET  /api/medicoes?limite=N -> últimas N medições (padrão 20, máximo 200)
  GET  /api/medicoes/ultima   -> última medição (404 se não houver)
  GET  /api/saude             -> estado da API e quantidade em memória

Uso:
  python mock_api.py                         # http://127.0.0.1:8080 (só este PC)
  python mock_api.py --host 0.0.0.0          # aceita conexões da rede local
  python mock_api.py --falhas-503 2          # responde 503 nos 2 primeiros POSTs (teste de reenvio)
Se a variável REFUGIO_API_TOKEN estiver definida ao iniciar, os POSTs exigem
"Authorization: Bearer <token>".
"""
import argparse
import json
import os
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from contrato import LIMIAR_PADRAO, faixa_do_sensor, validar_corpo_api

BASE = os.path.dirname(os.path.abspath(__file__))


class Estado:
    def __init__(self, sensor="DHT22", limiar=LIMIAR_PADRAO, token="", falhas_503=0):
        faixa_do_sensor(sensor)
        self.sensor, self.limiar, self.token = sensor, limiar, token
        self.falhas_503 = falhas_503
        self.medicoes = []
        self.trava = threading.Lock()


def criar_handler(estado, verbose=True):
    class Handler(BaseHTTPRequestHandler):
        def _resp(self, code, corpo):
            dados = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(dados)))
            self.end_headers()
            self.wfile.write(dados)

        def do_POST(self):
            if urlparse(self.path).path != "/api/medicoes":
                return self._resp(404, {"erro": "rota não encontrada"})
            if estado.token and self.headers.get("Authorization") != f"Bearer {estado.token}":
                return self._resp(401, {"erro": "token ausente ou inválido"})
            with estado.trava:
                if estado.falhas_503 > 0:
                    estado.falhas_503 -= 1
                    return self._resp(503, {"erro": "indisponível (falha simulada)"})
            try:
                tamanho = int(self.headers.get("Content-Length", 0))
                corpo = json.loads(self.rfile.read(tamanho).decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                return self._resp(400, {"erro": "JSON inválido"})
            status, erro = validar_corpo_api(corpo, estado.sensor, estado.limiar)
            if status != 201:
                if verbose:
                    print(f"[api] HTTP {status}: {erro}")
                return self._resp(status, {"erro": erro})
            with estado.trava:
                registro = dict(corpo, id=len(estado.medicoes) + 1,
                                recebidoEm=datetime.now(timezone.utc).isoformat(timespec="milliseconds"))
                estado.medicoes.append(registro)
            if verbose:
                print(f"[api] 201 medição {registro['id']}: {corpo['temperatura']} °C / "
                      f"{corpo['umidade']}% alerta={str(corpo['alerta']).lower()}")
            self._resp(201, {"id": registro["id"]})

        def do_GET(self):
            url = urlparse(self.path)
            with estado.trava:
                medicoes = list(estado.medicoes)
            if url.path == "/api/medicoes":
                try:
                    limite = int(parse_qs(url.query).get("limite", ["20"])[0])
                except ValueError:
                    return self._resp(400, {"erro": "limite deve ser inteiro"})
                limite = max(1, min(limite, 200))
                return self._resp(200, medicoes[-limite:])
            if url.path == "/api/medicoes/ultima":
                if not medicoes:
                    return self._resp(404, {"erro": "nenhuma medição recebida"})
                return self._resp(200, medicoes[-1])
            if url.path == "/api/saude":
                return self._resp(200, {"status": "ok", "armazenamento": "memoria",
                                        "sensor": estado.sensor, "medicoes": len(medicoes)})
            self._resp(404, {"erro": "rota não encontrada"})

        def log_message(self, *args):
            pass

    return Handler


def criar_servidor(host="127.0.0.1", porta=8080, verbose=True, **kw):
    estado = Estado(**kw)
    servidor = ThreadingHTTPServer((host, porta), criar_handler(estado, verbose))
    return servidor, estado


def main():
    cfg_path = os.path.join(BASE, "config.json")
    if not os.path.exists(cfg_path):
        cfg_path = os.path.join(BASE, "config.example.json")
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)

    ap = argparse.ArgumentParser(description="API de teste do REFÚGIO (dados em memória)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--porta", type=int, default=8080)
    ap.add_argument("--sensor", default=cfg.get("sensor", "DHT22"))
    ap.add_argument("--falhas-503", type=int, default=0)
    args = ap.parse_args()

    servidor, estado = criar_servidor(args.host, args.porta, sensor=args.sensor.upper(),
                                      limiar=cfg.get("limiar_alerta", LIMIAR_PADRAO),
                                      token=os.environ.get("REFUGIO_API_TOKEN", ""),
                                      falhas_503=args.falhas_503)
    print(f"API de teste em http://{args.host}:{args.porta}/api/medicoes | sensor {estado.sensor} | "
          f"token {'exigido' if estado.token else 'não exigido'} | dados SÓ em memória (Ctrl+C para sair)")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print(f"\n[api] encerrada; {len(estado.medicoes)} medições descartadas (memória)")


if __name__ == "__main__":
    main()
