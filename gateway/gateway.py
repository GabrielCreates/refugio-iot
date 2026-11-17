"""
REFÚGIO - Gateway Serial -> HTTP

Recebe as linhas JSON do Arduino, valida cada uma (contrato.py), acrescenta o
ponto de apoio, a origem e o horário em que o gateway recebeu a linha, envia
por HTTP POST para a API e registra o resultado de cada linha em um CSV.

Fontes de dados (escolha uma):
  python gateway.py                        # Arduino físico na porta Serial do config.json
  python gateway.py --porta COM4           # idem, sobrescrevendo a porta
  python gateway.py --arquivo ARQ.txt      # REPRODUZ leituras exportadas do Wokwi
  python gateway.py --simular              # gera leituras aleatórias (teste de software)

Importante:
  - --arquivo não conversa com o Wokwi em tempo real: apenas relê um arquivo
    com a saída do Serial Monitor. O campo dataHora registra o momento da
    reprodução no gateway, não o momento original da leitura no simulador.
  - --simular testa o software com dados gerados; não mede a precisão nem a
    confiabilidade de um sensor físico.
"""
import argparse
import csv
import json
import os
import random
import sys
import time
from collections import Counter
from datetime import datetime, timezone

import requests

from contrato import LIMIAR_PADRAO, classificar_linha_serial, faixa_do_sensor

BASE = os.path.dirname(os.path.abspath(__file__))
LOG_PADRAO = os.path.join(BASE, "logs", "medicoes_log.csv")

COLUNAS_CSV = ["execucao", "modo", "recebido_em_gateway", "seq", "temperatura",
               "umidade", "alerta", "resultado", "status_http", "tentativas", "detalhe"]

# Contrato HTTP da API de ingestão (o mesmo da API de teste e da API Java proposta)
STATUS_SUCESSO = {201}                        # medição aceita e registrada
# 4xx (400, 401, 404, 422...) = pedido recusado: repetir não adianta.
# 5xx, timeout ou sem conexão = falha temporária: tenta de novo, com limite.


def agora_iso():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def carregar_config(caminho=None):
    if caminho is None:
        caminho = os.path.join(BASE, "config.json")
        if not os.path.exists(caminho):
            caminho = os.path.join(BASE, "config.example.json")
            print("[aviso] config.json não encontrado, usando config.example.json")
    with open(caminho, encoding="utf-8") as f:
        cfg = json.load(f)
    cfg.setdefault("sensor", "DHT22")
    cfg.setdefault("limiar_alerta", LIMIAR_PADRAO)
    cfg.setdefault("tentativas", 3)
    cfg.setdefault("timeout_s", 5)
    cfg.setdefault("baud", 9600)
    faixa_do_sensor(cfg["sensor"])  # falha cedo se o sensor estiver errado
    # O token nunca fica em arquivo nem aparece em log: vem da variável de ambiente.
    cfg["token"] = os.environ.get("REFUGIO_API_TOKEN", "")
    return cfg


# ---------------------------------------------------------------- fontes ---

def linhas_serial(porta, baud):
    try:
        import serial  # pyserial
    except ImportError:
        sys.exit("[erro] pyserial não instalado. Rode: pip install -r requirements.txt")
    with serial.Serial(porta, baud, timeout=5) as conexao:
        print(f"[serial] conectado em {porta} a {baud} baud")
        time.sleep(2)  # o Uno reinicia ao abrir a porta
        conexao.reset_input_buffer()
        while True:
            linha = conexao.readline().decode("utf-8", errors="replace").strip()
            if linha:
                yield linha


def linhas_arquivo(caminho, intervalo_s):
    with open(caminho, encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if linha:
                yield linha
                time.sleep(intervalo_s)


def linhas_simuladas(intervalo_s, semente=None):
    rng = random.Random(semente)
    seq = 0
    while True:
        seq += 1
        if seq % 10 == 0:  # 1 falha de sensor a cada 10 leituras, de propósito
            yield json.dumps({"seq": seq, "erro": "falha_leitura_dht11"})
        else:
            t = round(rng.uniform(24, 36), 1)
            yield json.dumps({"seq": seq, "temperatura": t,
                              "umidade": round(rng.uniform(35, 80), 1),
                              "alerta": t >= LIMIAR_PADRAO})
        time.sleep(intervalo_s)


# ------------------------------------------------------------------ envio ---

def enviar(cfg, medicao, sessao=None):
    """
    Envia uma medição. Retorna (resultado, status_http, tentativas, detalhe).
      enviado       -> HTTP 201
      rejeitado_api -> 4xx do contrato: não repete
      falha_envio   -> 5xx, timeout ou sem conexão após todas as tentativas
    """
    http = sessao or requests
    headers = {"Content-Type": "application/json"}
    if cfg.get("token"):
        headers["Authorization"] = f"Bearer {cfg['token']}"
    maximo = max(1, int(cfg.get("tentativas", 3)))
    ultimo_status, ultimo_detalhe = "", ""
    for tentativa in range(1, maximo + 1):
        try:
            r = http.post(cfg["api_url"], json=medicao, headers=headers,
                          timeout=cfg.get("timeout_s", 5))
        except requests.Timeout:
            ultimo_status, ultimo_detalhe = "", "timeout"
        except requests.ConnectionError:
            ultimo_status, ultimo_detalhe = "", "sem_conexao"
        except requests.RequestException as e:
            ultimo_status, ultimo_detalhe = "", e.__class__.__name__
        else:
            if r.status_code in STATUS_SUCESSO:
                return "enviado", r.status_code, tentativa, ""
            detalhe = _mensagem_erro(r)
            if 400 <= r.status_code < 500:
                return "rejeitado_api", r.status_code, tentativa, detalhe
            ultimo_status, ultimo_detalhe = r.status_code, detalhe  # 5xx: tenta de novo
        print(f"[http] tentativa {tentativa}/{maximo} falhou: {ultimo_detalhe or ultimo_status}")
        if tentativa < maximo:
            time.sleep(1)
    return "falha_envio", ultimo_status, maximo, ultimo_detalhe


def _mensagem_erro(resposta):
    try:
        corpo = resposta.json()
        if isinstance(corpo, dict) and "erro" in corpo:
            return str(corpo["erro"])
    except ValueError:
        pass
    return f"HTTP {resposta.status_code}"


# ------------------------------------------------------------ processamento ---

def processar_linha(linha, cfg, enviar_fn):
    """Processa uma linha e devolve o registro (dict) que vai para o CSV."""
    tipo, dado, detalhe = classificar_linha_serial(linha, cfg["sensor"], cfg["limiar_alerta"])
    recebido = agora_iso()
    reg = {"recebido_em_gateway": recebido, "seq": "", "temperatura": "", "umidade": "",
           "alerta": "", "resultado": tipo, "status_http": "", "tentativas": "", "detalhe": detalhe}
    if isinstance(dado, dict):
        for campo in ("seq", "temperatura", "umidade", "alerta"):
            if campo in dado and not isinstance(dado[campo], (dict, list)):
                reg[campo] = dado[campo]

    if tipo == "leitura":
        medicao = {"pontoId": cfg["ponto_id"], "temperatura": dado["temperatura"],
                   "umidade": dado["umidade"], "alerta": dado["alerta"],
                   "dataHora": recebido, "origem": cfg["dispositivo"]}
        resultado, status, tentativas, det = enviar_fn(cfg, medicao)
        reg.update(resultado=resultado, status_http=status, tentativas=tentativas, detalhe=det)
    return reg


def imprimir(reg, linha):
    r = reg["resultado"]
    if r == "status":
        print(f"[arduino] status: {reg['detalhe']}")
    elif r == "enviado":
        print(f"[ok] seq {reg['seq']}: {reg['temperatura']} °C, {reg['umidade']}% "
              f"alerta={reg['alerta']} -> HTTP {reg['status_http']}")
    elif r == "rejeitado_api":
        print(f"[rejeitado] seq {reg['seq']} -> HTTP {reg['status_http']}: {reg['detalhe']}")
    elif r == "falha_envio":
        print(f"[falha_envio] seq {reg['seq']} não entregue: {reg['detalhe'] or reg['status_http']}")
    elif r == "falha_sensor":
        print(f"[sensor] seq {reg['seq']}: {reg['detalhe']} (nada enviado)")
    else:
        print(f"[{r}] {reg['detalhe']}: {linha[:80]}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Gateway Serial -> HTTP do REFÚGIO")
    fonte = ap.add_mutually_exclusive_group()
    fonte.add_argument("--arquivo", help="reproduz um arquivo com a saída Serial exportada do Wokwi")
    fonte.add_argument("--simular", action="store_true", help="gera leituras aleatórias")
    ap.add_argument("--porta", help="porta Serial (ex.: COM3 ou /dev/ttyACM0)")
    ap.add_argument("--config", help="caminho do arquivo de configuração")
    ap.add_argument("--log", default=LOG_PADRAO, help="CSV de saída (padrão: gateway/logs/medicoes_log.csv)")
    ap.add_argument("--execucao", help="rótulo da execução no CSV (padrão: data-hora + modo)")
    ap.add_argument("--intervalo", type=float, help="segundos entre linhas em --arquivo/--simular")
    ap.add_argument("--semente", type=int, help="semente do --simular, para repetir a sequência")
    ap.add_argument("--max", type=int, default=0, help="para após N linhas (0 = sem limite)")
    args = ap.parse_args(argv)
    cfg = carregar_config(args.config)

    if args.arquivo:
        modo = "arquivo"
        origem = linhas_arquivo(args.arquivo, args.intervalo if args.intervalo is not None
                                else cfg.get("intervalo_reproducao_s", 0.5))
    elif args.simular:
        modo = "simulado"
        origem = linhas_simuladas(args.intervalo if args.intervalo is not None else 2.0, args.semente)
    else:
        modo = "serial"
        origem = linhas_serial(args.porta or cfg["porta_serial"], cfg["baud"])

    execucao = args.execucao or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + modo
    print(f"[gateway] execução {execucao} | modo {modo} | sensor {cfg['sensor']} | "
          f"API {cfg['api_url']} | token {'definido' if cfg['token'] else 'não definido'}")

    os.makedirs(os.path.dirname(os.path.abspath(args.log)), exist_ok=True)
    novo = not os.path.exists(args.log) or os.path.getsize(args.log) == 0
    contagem = Counter()
    sessao = requests.Session()
    with open(args.log, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS_CSV)
        if novo:
            w.writeheader()
        try:
            for n, linha in enumerate(origem, 1):
                reg = processar_linha(linha, cfg, lambda c, m: enviar(c, m, sessao))
                reg.update(execucao=execucao, modo=modo)
                w.writerow(reg)
                f.flush()
                contagem[reg["resultado"]] += 1
                imprimir(reg, linha)
                if args.max and n >= args.max:
                    break
        except KeyboardInterrupt:
            print("\n[gateway] interrompido pelo usuário")
    print(f"[gateway] resumo {execucao}: " + ", ".join(f"{k}={v}" for k, v in sorted(contagem.items())))
    print(f"[gateway] log: {os.path.relpath(args.log)}")
    return contagem


if __name__ == "__main__":
    main()
