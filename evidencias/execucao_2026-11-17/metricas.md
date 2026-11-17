# Métricas das execuções de 17/11/2026

Calculadas com `python gateway/metricas.py evidencias/execucao_2026-11-17/medicoes_log.csv`. Cada coluna é uma execução separada (coluna `execucao` do CSV).

- **Taxa de entrega** = envios com HTTP 201 ÷ leituras válidas (leituras aprovadas pelo gateway e enviadas à API).
- **Intervalo entre linhas** = diferença entre os horários em que o gateway processou linhas consecutivas. No modo `arquivo`, reflete o `--intervalo` da reprodução, não o intervalo original do Wokwi (2 s).
- Todas as execuções usaram a API de teste em `127.0.0.1` (mesmo computador). Nenhuma atravessou roteador, Internet ou Azure.

| Métrica | `E1-reproducao-wokwi` | `E2-entradas-de-teste` | `E4-api-desligada` | `E5-api-503-temporario` | `E7-estabilidade-simulada` |
|---|---|---|---|---|---|
| Modo | arquivo | arquivo | arquivo | arquivo | simulado |
| Linhas processadas (sem status) | 39 | 16 | 3 | 3 | 60 |
| Leituras válidas | 39 | 6 | 3 | 3 | 54 |
| Falhas de sensor | 0 | 1 | 0 | 0 | 6 |
| Recusadas no gateway | 0 | 9 | 0 | 0 | 0 |
| Enviadas com sucesso (HTTP 201) | 39 | 6 | 0 | 3 | 54 |
| Rejeitadas pela API (4xx) | 0 | 0 | 0 | 0 | 0 |
| Falhas de envio | 0 | 0 | 3 | 0 | 0 |
| Taxa de entrega | 39/39 = 100.0% | 6/6 = 100.0% | 0/3 = 0.0% | 3/3 = 100.0% | 54/54 = 100.0% |
| Intervalo entre linhas (média / mín / máx) | 0.50 / 0.50 / 0.50 s | 0.20 / 0.20 / 0.20 s | 2.50 / 2.50 / 2.51 s | 1.51 / 0.50 / 2.51 s | 2.00 / 2.00 / 2.01 s |
| Temperatura (mín / média / máx) | 25.0 / 27.8 / 35.0 °C | 25.0 / 29.3 / 32.1 °C | 27.0 / 27.0 / 27.0 °C | 27.0 / 27.0 / 27.0 °C | 24.6 / 30.4 / 35.8 °C |
| Leituras válidas com alerta | 6 | 2 | 0 | 0 | 19 |
