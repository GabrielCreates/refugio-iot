# Evidências

Organizadas por data e ambiente, para não misturar cenários. Critérios e análise em [`../docs/testes.md`](../docs/testes.md).

## `wokwi_2026-11-17/`: circuito simulado com o código atual

| Arquivo | Conteúdo |
|---|---|
| `w1_leitura_normal.png` | W1: 27 °C, `alerta:false`, LED apagado |
| `w2_calor_led_aceso.png` | W2: de 27 °C para 35 °C (seq 15), LED aceso |
| `w3_retorno_led_apagado.png` | W3: de 35 °C para 25 °C (seq 22), LED apagado |
| `w4_sensor_desconectado.png` | W4: SDA removido, `falha_leitura_dht11`, LED apagado |
| `w5_32_0_led_aceso.png` | W5: exatamente 32,0 °C, `alerta:true`, LED aceso |
| `w5_31_9_led_apagado.png` | W5: 31,9 °C, `alerta:false`, LED apagado |
| `saida_wokwi_w1_w2_w3.txt` | Serial Monitor da execução W1–W3 (seq 1–48) |
| `saida_wokwi_w4_w5.txt` | Serial Monitor das execuções W4 e W5 |

## `wokwi_2026-11-13/`: circuito simulado (versão anterior do firmware)

| Arquivo | Conteúdo |
|---|---|
| `circuito_wokwi.png` | Circuito no Wokwi com o Serial Monitor (mesma imagem de `t1_monitor_serial.png`) |
| `t1_monitor_serial.png` | W1: leitura normal a 27 °C, `alerta:false`, LED apagado |
| `t2_led_aceso.png` | W2: 35 °C, `alerta:true`, LED aceso |
| `t3_led_apagado.png` | W3: volta a 25 °C, LED apagado |
| `t4_erro_sensor.png` | W4: fio SDA removido, `"erro":"falha_leitura_dht11"` |
| `saida_wokwi.txt` | Linhas copiadas do Serial Monitor (seq 1–39), usadas no modo `--arquivo` |

## `gateway_2026-11-13/`: execuções originais do gateway (versão anterior)

| Arquivo | Conteúdo |
|---|---|
| `t5_gateway_api.txt` | T5: reprodução da `saida_wokwi.txt`, 39 × HTTP 201 |
| `t6_api_offline.txt` | T6: API desligada, 2 leituras com `sem_conexao` |
| `t7_validacao.txt` | T7: API de teste recusando umidade 150 (422) e campos ausentes (400) |
| `t8_estabilidade.txt` | T8: 60 linhas em `--simular` |
| `medicoes_log.csv` | Log no formato antigo (T5, T6 e T8) |
| `metricas_recalculadas.md` | Métricas do log antigo pelo script `metricas.py` |

## `execucao_2026-11-17/`: execuções com a versão atual (localhost)

| Arquivo | Conteúdo |
|---|---|
| `E0_testes_automatizados.txt` | 18 testes `unittest` e 11 verificações do firmware no PC |
| `E1_reproducao_wokwi.txt` | Reprodução da `saida_wokwi.txt` para a API de teste |
| `E2_entradas_de_teste.txt` | Entradas inválidas e de fronteira (31,9 / 32,0 / 32,1 °C) |
| `entradas_teste_gateway.txt` | Arquivo de entrada do E2, montado à mão (não é saída do Wokwi) |
| `E3_consulta_api.txt` | Consultas GET à API de teste |
| `E4_api_desligada.txt` | Gateway sem API: 3 tentativas por leitura e `falha_envio` |
| `E5_api_503_temporario.txt` | HTTP 503 nas 2 primeiras tentativas e entrega na 3ª |
| `E6_validacao_api.txt` | Respostas 201, 400, 401 e 422 da API de teste |
| `E7_estabilidade_simulada.txt` | 60 linhas aleatórias a cada 2 s |
| `api_terminal_*.txt` | Saída do terminal da API de teste em cada cenário |
| `medicoes_log.csv` | Log das execuções E1, E2, E4, E5 e E7 (coluna `execucao`) |
| `metricas.md` | Métricas por execução |
