# Roteiro de demonstração (cerca de 10 minutos)

Tudo neste roteiro funciona hoje. Onde algo é proposta, a fala diz isso.

## Antes de começar (preparar no PC da apresentação)

1. Abrir a simulação: https://wokwi.com/projects/480550298121861121. Conferir se abre sem login; se não abrir, recriar o projeto pelos passos do README, seção 7.
2. Terminal 1, na pasta `gateway`: `py mock_api.py` (Windows) ou `python3 mock_api.py` (Linux). Deixar aberto.
3. Terminal 2, na pasta `gateway`, pronto para rodar o gateway.
4. Abrir `docs/arquitetura_demonstrada.png`, `docs/arquitetura_proposta.png` e `docs/testes.md`.

## Sequência

| # | Tempo | Etapa | O que mostrar ou fazer | O que falar |
|---|---|---|---|---|
| 1 | 1 min | Problema e proposta | README, seção 2 | Idosos e pedestres não sabem as condições dos pontos de apoio no calor. O REFÚGIO mede temperatura e umidade no ponto e avisa localmente com um LED. |
| 2 | 1 min | Leitura do sensor | Wokwi: Start e Serial Monitor | Uma linha JSON a cada 2 s, com `seq`, temperatura, umidade e alerta. Leitura com `millis()`, sem `delay`. |
| 3 | 1 min | LED normal e em alerta | Clicar no DHT22: 27 °C → 35 °C → 25 °C | O LED acende com 32 °C ou mais. O limiar é didático, não é critério oficial de saúde. |
| 4 | 1 min | Falha do sensor | Parar, apagar o fio SDA → D2 e iniciar de novo | O firmware envia `"erro":"falha_leitura_dht11"`, apaga o LED e não inventa valor. |
| 5 | 2 min | Gateway enviando à API | Terminal 2: `py gateway.py --arquivo ..\evidencias\wokwi_2026-11-13\saida_wokwi.txt` | O gateway reproduz as linhas exportadas do Wokwi; não é ligação em tempo real. Cada linha é validada; a API responde 201. |
| 6 | 1 min | Consulta das medições | Navegador: `http://localhost:8080/api/medicoes?limite=5` | A API de teste guarda só em memória. Na proposta, seria a API Java com PostgreSQL. |
| 7 | 1 min | Entradas inválidas | `py gateway.py --arquivo ..\evidencias\execucao_2026-11-17\entradas_teste_gateway.txt --intervalo 0.3` | Texto que não é JSON, tipos errados, umidade 150, alerta incoerente: tudo é recusado com motivo e nada é enviado. |
| 8 | 1 min | Rede | Os dois diagramas | Demonstrado: localhost, tudo no mesmo PC. Proposto: USB/Serial → PC gateway → roteador → Internet (HTTPS) → API na Azure → PostgreSQL; o app consulta a API. O Uno não tem Wi-Fi, por isso precisa do gateway. |
| 9 | 1 min | Testes, resultados e limitações | `docs/testes.md` | 18 testes automatizados, 11 verificações do firmware e 7 cenários executados. No Wokwi, 31,9 °C apaga e 32,0 °C acende o LED. Sem reenvio de leituras perdidas. |

## Plano B (se algo falhar ao vivo)

- **Wokwi fora do ar:** mostrar os prints em `evidencias/wokwi_2026-11-17/`.
- **Porta 8080 ocupada:** `py mock_api.py --porta 8081` e ajustar `api_url` no `config.json`.
- **Para mostrar a API caindo:** encerrar o Terminal 1 (Ctrl+C) e rodar o gateway de novo. Ele faz 3 tentativas e registra `falha_envio`.

## Perguntas prováveis

| Pergunta | Resposta curta |
|---|---|
| Por que DHT11 e não um sensor melhor? | Custo baixo, temperatura e umidade num só sensor e um único pino. A limitação é ±2 °C. Em produção, o DHT22 ou o SHT31 seriam opções. |
| Por que gateway e não Wi-Fi direto? | O Uno não tem Wi-Fi. Em produção, ESP32 (Wi-Fi) ou LoRaWAN para pontos sem rede. |
| E se a Internet cair? | O gateway tenta 3 vezes e registra `falha_envio` no CSV. Hoje não reenvia depois; seria preciso uma fila local. |
| A leitura é em tempo real com o Wokwi? | Não. O Wokwi não expõe a Serial ao PC; o modo `--arquivo` reproduz o que foi exportado. Com o Arduino físico, o modo Serial é em tempo real. |
| Como saber se o dado é confiável? | Faixa do datasheet, tipos e coerência do alerta são verificados no gateway e na API. Mesmo assim, o sensor mede só o ponto onde está. |
