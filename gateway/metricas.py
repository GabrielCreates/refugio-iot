"""
REFÚGIO - Cálculo de métricas a partir do CSV do gateway.

Cada execução é calculada separadamente, para não misturar cenários
(reprodução do Wokwi, dados simulados, API desligada etc.).

Uso:
  python metricas.py ../evidencias/execucao_2026-11-17/medicoes_log.csv
  python metricas.py ARQUIVO.csv --saida metricas.md

Também lê o formato antigo do log (13/11/2026, colunas recebido_em ... obs).
Nesse formato não há coluna de execução: uma nova execução é detectada quando
a sequência (seq) volta a diminuir.
"""
import argparse
import csv
import statistics
import sys
from collections import OrderedDict
from datetime import datetime

LEITURA_VALIDA = {"enviado", "rejeitado_api", "falha_envio"}
RECUSADA_GATEWAY = {"linha_invalida", "formato_invalido", "fora_da_faixa"}


def _normalizar_antigo(linhas):
    """Converte o formato de 13/11 para o atual e separa execuções pela seq."""
    saida, execucao, seq_anterior = [], 1, None
    for r in linhas:
        seq = int(r["seq"]) if r.get("seq") else None
        if seq is not None and seq_anterior is not None and seq < seq_anterior:
            execucao += 1
        if seq is not None:
            seq_anterior = seq
        status = r.get("status_http", "")
        if r.get("obs") == "linha_invalida":
            resultado = "linha_invalida"
        elif r.get("obs"):
            resultado = "falha_sensor"
        elif status == "201":
            resultado = "enviado"
        elif status and status.isdigit() and 400 <= int(status) < 500:
            resultado = "rejeitado_api"
        else:
            resultado = "falha_envio"
        saida.append({"execucao": f"antiga-{execucao}", "modo": "?",
                      "recebido_em_gateway": r["recebido_em"], "seq": r.get("seq", ""),
                      "temperatura": r.get("temperatura", ""), "alerta": r.get("alerta", ""),
                      "resultado": resultado, "status_http": status})
    return saida


def carregar(caminho):
    with open(caminho, encoding="utf-8", newline="") as f:
        linhas = list(csv.DictReader(f))
    if linhas and "execucao" not in linhas[0]:
        linhas = _normalizar_antigo(linhas)
    grupos = OrderedDict()
    for r in linhas:
        grupos.setdefault(r["execucao"], []).append(r)
    return grupos


def _bool(valor):
    return str(valor).strip().lower() == "true"


def calcular(registros):
    regs = [r for r in registros if r["resultado"] != "status"]
    validas = [r for r in regs if r["resultado"] in LEITURA_VALIDA]
    enviados = sum(1 for r in regs if r["resultado"] == "enviado")
    tempos = [datetime.fromisoformat(r["recebido_em_gateway"]) for r in regs]
    intervalos = [(b - a).total_seconds() for a, b in zip(tempos, tempos[1:])]
    temps = [float(r["temperatura"]) for r in validas]
    m = OrderedDict()
    m["Modo"] = regs[0]["modo"] if regs else "-"
    m["Linhas processadas (sem status)"] = len(regs)
    m["Leituras válidas"] = len(validas)
    m["Falhas de sensor"] = sum(1 for r in regs if r["resultado"] == "falha_sensor")
    m["Recusadas no gateway"] = sum(1 for r in regs if r["resultado"] in RECUSADA_GATEWAY)
    m["Enviadas com sucesso (HTTP 201)"] = enviados
    m["Rejeitadas pela API (4xx)"] = sum(1 for r in regs if r["resultado"] == "rejeitado_api")
    m["Falhas de envio"] = sum(1 for r in regs if r["resultado"] == "falha_envio")
    m["Taxa de entrega"] = (f"{enviados}/{len(validas)} = {100 * enviados / len(validas):.1f}%"
                            if validas else "sem leituras válidas")
    if intervalos:
        m["Intervalo entre linhas (média / mín / máx)"] = (
            f"{statistics.mean(intervalos):.2f} / {min(intervalos):.2f} / {max(intervalos):.2f} s")
    else:
        m["Intervalo entre linhas (média / mín / máx)"] = "-"
    m["Temperatura (mín / média / máx)"] = (
        f"{min(temps):.1f} / {statistics.mean(temps):.1f} / {max(temps):.1f} °C" if temps else "-")
    m["Leituras válidas com alerta"] = sum(1 for r in validas if _bool(r["alerta"]))
    return m


def tabela_markdown(caminho):
    grupos = carregar(caminho)
    nomes = list(grupos)
    resultados = [calcular(grupos[n]) for n in nomes]
    linhas = ["| Métrica | " + " | ".join(f"`{n}`" for n in nomes) + " |",
              "|---|" + "---|" * len(nomes)]
    for chave in resultados[0]:
        linhas.append(f"| {chave} | " + " | ".join(str(r[chave]) for r in resultados) + " |")
    return "\n".join(linhas)


def main():
    ap = argparse.ArgumentParser(description="Métricas do log do gateway REFÚGIO")
    ap.add_argument("csv")
    ap.add_argument("--saida", help="grava a tabela em um arquivo Markdown")
    args = ap.parse_args()
    texto = tabela_markdown(args.csv)
    if args.saida:
        with open(args.saida, "w", encoding="utf-8") as f:
            f.write(texto + "\n")
    sys.stdout.reconfigure(encoding="utf-8")
    print(texto)


if __name__ == "__main__":
    main()
