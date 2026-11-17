"""
REFÚGIO - Contrato de dados compartilhado entre o gateway e a API de teste.

Um único lugar define:
  - as faixas válidas de cada sensor (DHT11 físico e DHT22 do Wokwi);
  - o limiar didático do alerta de calor;
  - a validação da linha JSON enviada pelo Arduino;
  - a validação do corpo recebido pela API (POST /api/medicoes).

Assim o gateway, a API de teste e a documentação usam as mesmas regras.
"""
import json
import math
from datetime import datetime

# Faixas de medição informadas nos datasheets do fabricante (Aosong).
#   DHT11: 0 a 50 °C e 20 a 90 %UR
#   DHT22 (AM2302): -40 a 80 °C e 0 a 100 %UR
FAIXAS = {
    "DHT11": {"temperatura": (0.0, 50.0), "umidade": (20.0, 90.0)},
    "DHT22": {"temperatura": (-40.0, 80.0), "umidade": (0.0, 100.0)},
}

# Limiar DIDÁTICO usado pelo firmware para acender o LED. Não é um critério
# oficial de risco à saúde.
LIMIAR_PADRAO = 32.0

CAMPOS_API = ("pontoId", "temperatura", "umidade", "alerta", "dataHora", "origem")


def eh_numero(valor):
    """True para int/float finitos. bool não conta como número."""
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return False
    return math.isfinite(valor)


def faixa_do_sensor(sensor):
    sensor = (sensor or "").upper()
    if sensor not in FAIXAS:
        raise ValueError(f"sensor desconhecido: {sensor!r} (use DHT11 ou DHT22)")
    return FAIXAS[sensor]


def _checar_valores(temperatura, umidade, alerta, sensor, limiar):
    """Regras comuns às duas validações. Retorna None ou o motivo da recusa."""
    faixa = faixa_do_sensor(sensor)
    tmin, tmax = faixa["temperatura"]
    umin, umax = faixa["umidade"]
    if not (tmin <= temperatura <= tmax):
        return f"temperatura {temperatura} fora da faixa do {sensor} ({tmin} a {tmax} °C)"
    if not (umin <= umidade <= umax):
        return f"umidade {umidade} fora da faixa do {sensor} ({umin} a {umax} %UR)"
    if alerta != (temperatura >= limiar):
        return f"alerta={str(alerta).lower()} inconsistente com {temperatura} °C (limiar {limiar} °C)"
    return None


def classificar_linha_serial(linha, sensor="DHT22", limiar=LIMIAR_PADRAO):
    """
    Classifica uma linha recebida do Arduino.

    Retorna (tipo, dado, detalhe), em que tipo é:
      "status"           -> mensagem de inicialização do firmware
      "falha_sensor"     -> o firmware não conseguiu ler o DHT
      "leitura"          -> leitura válida, pronta para envio
      "linha_invalida"   -> texto que não é JSON
      "formato_invalido" -> JSON válido, mas com estrutura, campos ou tipos errados
      "fora_da_faixa"    -> valores fora da faixa do sensor ou alerta inconsistente
    """
    try:
        dado = json.loads(linha)
    except (json.JSONDecodeError, TypeError):
        return "linha_invalida", None, "não é JSON"

    if not isinstance(dado, dict):
        return "formato_invalido", None, "JSON não é um objeto"

    if "status" in dado:
        return "status", dado, str(dado.get("status"))

    seq = dado.get("seq")
    if isinstance(seq, bool) or not isinstance(seq, int) or seq < 1:
        return "formato_invalido", dado, "campo seq ausente ou não é inteiro positivo"

    if "erro" in dado:
        return "falha_sensor", dado, str(dado["erro"])

    faltando = [c for c in ("temperatura", "umidade", "alerta") if c not in dado]
    if faltando:
        return "formato_invalido", dado, "campos ausentes: " + ", ".join(faltando)
    if not eh_numero(dado["temperatura"]) or not eh_numero(dado["umidade"]):
        return "formato_invalido", dado, "temperatura e umidade devem ser números"
    if not isinstance(dado["alerta"], bool):
        return "formato_invalido", dado, "alerta deve ser true ou false"

    motivo = _checar_valores(dado["temperatura"], dado["umidade"], dado["alerta"], sensor, limiar)
    if motivo:
        return "fora_da_faixa", dado, motivo
    return "leitura", dado, ""


def validar_corpo_api(corpo, sensor="DHT22", limiar=LIMIAR_PADRAO):
    """
    Valida o corpo de POST /api/medicoes.

    Retorna (status_http, mensagem_de_erro). status 201 significa válido.
      400 -> corpo não é objeto, campos ausentes ou tipos incorretos
      422 -> tipos corretos, mas valores fora da faixa ou alerta inconsistente
    """
    if not isinstance(corpo, dict):
        return 400, "o corpo deve ser um objeto JSON"
    faltando = [c for c in CAMPOS_API if c not in corpo]
    if faltando:
        return 400, "campos ausentes: " + ", ".join(faltando)
    if isinstance(corpo["pontoId"], bool) or not isinstance(corpo["pontoId"], int) or corpo["pontoId"] < 1:
        return 400, "pontoId deve ser inteiro positivo"
    if not eh_numero(corpo["temperatura"]) or not eh_numero(corpo["umidade"]):
        return 400, "temperatura e umidade devem ser números"
    if not isinstance(corpo["alerta"], bool):
        return 400, "alerta deve ser true ou false"
    if not isinstance(corpo["origem"], str) or not corpo["origem"].strip():
        return 400, "origem deve ser texto não vazio"
    if not isinstance(corpo["dataHora"], str):
        return 400, "dataHora deve ser texto ISO 8601"
    try:
        datetime.fromisoformat(corpo["dataHora"])
    except ValueError:
        return 400, "dataHora não está em ISO 8601"

    motivo = _checar_valores(corpo["temperatura"], corpo["umidade"], corpo["alerta"], sensor, limiar)
    if motivo:
        return 422, motivo
    return 201, ""
