# Métricas recalculadas do log original (13/11/2026)

Calculadas com `python gateway/metricas.py evidencias/gateway_2026-11-13/medicoes_log.csv`.

O log de 13/11 não tem coluna de execução. O script separa execuções quando a `seq` diminui. Por isso:

- `antiga-1` reúne o **T5** (reprodução do Wokwi, seq 1–39, 39 envios com HTTP 201) e o **T6** (API desligada, seq 40–41, 2 falhas de envio). São duas execuções diferentes que não podem ser separadas pela seq. Considerando só o T5, a taxa de entrega foi 39/39.
- `antiga-2` é o **T8** (modo `--simular`, 60 linhas).
- O formato antigo não registra o modo, por isso aparece `?`.

| Métrica | `antiga-1` | `antiga-2` |
|---|---|---|
| Modo | ? | ? |
| Linhas processadas (sem status) | 41 | 60 |
| Leituras válidas | 41 | 54 |
| Falhas de sensor | 0 | 6 |
| Recusadas no gateway | 0 | 0 |
| Enviadas com sucesso (HTTP 201) | 39 | 54 |
| Rejeitadas pela API (4xx) | 0 | 0 |
| Falhas de envio | 2 | 0 |
| Taxa de entrega | 39/41 = 95.1% | 54/54 = 100.0% |
| Intervalo entre linhas (média / mín / máx) | 0.62 / 0.00 / 4.00 s | 2.00 / 2.00 / 2.00 s |
| Temperatura (mín / média / máx) | 25.0 / 27.6 / 35.0 °C | 24.2 / 30.2 / 35.4 °C |
| Leituras válidas com alerta | 6 | 18 |
