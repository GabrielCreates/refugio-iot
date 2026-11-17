# Testes e resultados

Separamos os testes pelo ambiente em que rodaram, porque cada um mostra uma coisa diferente:

- **Wokwi:** o firmware e o LED funcionando no Arduino simulado.
- **Lógica do firmware no PC:** o código `.ino` real compilado com um Arduino "falso", para conferir o JSON e o LED em cada temperatura.
- **Gateway e API de teste:** o envio, a validação e as respostas HTTP, tudo em `localhost`.
- **Modo `--simular`:** a estabilidade do software com dados aleatórios. Esse modo não mede a precisão de um sensor de verdade.

## Critérios

- Uma leitura é válida quando os números estão dentro da faixa do sensor. DHT22: -40 a 80 °C e 0 a 100 %UR. DHT11: 0 a 50 °C e 20 a 90 %UR.
- O alerta (LED aceso e `"alerta":true`) acontece com temperatura de 32,0 °C ou mais.
- Para o gateway, só o HTTP 201 conta como envio com sucesso. Respostas 4xx não são repetidas. Em 5xx, timeout ou sem conexão, ele tenta até 3 vezes.
- Uma linha inválida, uma falha do sensor ou a API fora do ar não podem travar o gateway, e tudo deve ficar registrado no CSV.

As regras ficam em `gateway/contrato.py` e são as mesmas no gateway e na API.

## Wokwi (17/11, código atual)

Colocamos o código atual no projeto do Wokwi e rodamos os testes abaixo. A temperatura foi mudada pelo controle do sensor durante a simulação ou direto no `diagram.json`, quando precisávamos de um valor exato.

| Teste | O que fizemos | Resultado | Print |
|---|---|---|---|
| W1 – leitura normal | 27 °C | `alerta:false`, LED apagado | `w1_leitura_normal.png` |
| W2 – calor | De 27 para 35 °C | Na seq 15, `alerta:true` e LED aceso | `w2_calor_led_aceso.png` |
| W3 – volta ao normal | De 35 para 25 °C | Na seq 22, `alerta:false` e LED apagado | `w3_retorno_led_apagado.png` |
| W4 – sensor desconectado | Tiramos o fio SDA → D2 | `"erro":"falha_leitura_dht11"`, LED apagado | `w4_sensor_desconectado.png` |
| W5 – exatamente 32,0 °C | `"temperature": "32"` | `alerta:true`, LED aceso | `w5_32_0_led_aceso.png` |
| W5 – 31,9 °C | `"temperature": "31.9"` | `alerta:false`, LED apagado | `w5_31_9_led_apagado.png` |

Os prints estão em `evidencias/wokwi_2026-11-17/`, junto com a saída do Serial Monitor (`saida_wokwi_w1_w2_w3.txt` e `saida_wokwi_w4_w5.txt`). Os prints da primeira versão, de 13/11, continuam em `evidencias/wokwi_2026-11-13/`. A `saida_wokwi.txt` daquela execução é a que usamos no modo `--arquivo`.

## Lógica do firmware no PC

O arquivo `testes/firmware_host/teste_firmware.cpp` compila o `.ino` com versões falsas do `Arduino.h` e do `DHT.h`. As 11 verificações passaram:

- Ao ligar, o firmware envia a mensagem de status. Com `SIMULACAO_WOKWI` ativo, usa o DHT22.
- Ele não faz leitura antes de 2 s, porque não usa `delay`.
- A 27 °C, gera o JSON certo, com o LED apagado.
- A 31,9 °C, o LED fica apagado. A 32,0 °C, acende. A 31,96 °C, o valor é arredondado para 32,0 e o alerta acompanha.
- A 35 °C, o LED acende. Ao voltar para 25 °C, apaga.
- Com o sensor desconectado (NaN), gera a linha de erro e apaga o LED. Depois disso, a `seq` continua contando normalmente.

## Gateway e API de teste (17/11)

Os logs estão em `evidencias/execucao_2026-11-17/`.

- **E1 – leituras do Wokwi:** reenviamos as 39 leituras da `saida_wokwi.txt` e as 39 receberam HTTP 201.
- **E2 – entradas inválidas:** montamos à mão um arquivo com casos de erro. As 6 leituras válidas foram enviadas, incluindo 31,9, 32,0 e 32,1 °C. As outras foram recusadas com o motivo e não foram enviadas: texto que não é JSON, campo faltando, número escrito como texto, umidade 150, temperatura 85 e alerta que não bate com a temperatura. A falha de sensor também ficou registrada.
- **E3 – consulta:** `GET /api/medicoes` e `/api/medicoes/ultima` devolveram as medições recebidas.
- **E4 – API desligada:** cada leitura teve 3 tentativas e ficou como `falha_envio`. O gateway não travou e terminou em 8,2 s.
- **E5 – erro temporário:** com a API respondendo 503 nas duas primeiras vezes, a leitura foi entregue na 3ª tentativa.
- **E6 – validação da API:** a API respondeu 401 sem token, 201 para o dado válido, 422 fora da faixa ou com alerta incoerente e 400 para campo faltando, tipo errado ou JSON quebrado.
- **E7 – estabilidade:** com `--simular`, foram 60 leituras a cada 2 s, cerca de 2 minutos. As 54 válidas foram entregues. As outras 6 foram falhas de sensor geradas de propósito.
- **Testes automatizados:** `python -m unittest discover -s testes -v`, 18 de 18 passando.

## Métricas

Calculamos as métricas com `python gateway/metricas.py evidencias/execucao_2026-11-17/medicoes_log.csv`. A tabela completa está em `evidencias/execucao_2026-11-17/metricas.md`.

| | E1 Wokwi | E2 inválidas | E4 API desligada | E5 503 | E7 simulado |
|---|---|---|---|---|---|
| Leituras válidas | 39 | 6 | 3 | 3 | 54 |
| Enviadas (HTTP 201) | 39 | 6 | 0 | 3 | 54 |
| Taxa de entrega | 100% | 100% | 0% | 100% | 100% |
| Temperatura mín / média / máx (°C) | 25,0 / 27,8 / 35,0 | 25,0 / 29,3 / 32,1 | 27,0 | 27,0 | 24,6 / 30,4 / 35,8 |
| Leituras com alerta | 6 | 2 | 0 | 0 | 19 |

A taxa de entrega é o número de envios com 201 dividido pelo número de leituras válidas. No E1, o intervalo foi de 0,5 s porque é a velocidade da reprodução; no Wokwi, as leituras acontecem a cada 2 s.

## Próximos testes (Arduino físico e rede local)

- **Arduino com DHT11:** montar conforme `docs/circuito.md`, comentar `#define SIMULACAO_WOKWI`, gravar a placa e repetir W1 a W4 aquecendo o sensor com a mão.
- **Gateway lendo a Serial:** fechar o Monitor Serial e rodar `python gateway.py --porta COM3`, com a API de teste ligada.
- **Rede local:** rodar `python mock_api.py --host 0.0.0.0` em um PC e, no outro, colocar no `api_url` o IP do primeiro (por exemplo, `http://192.168.0.10:8080/api/medicoes`), liberando a porta 8080 no firewall.

## Limitações

- O modo `--arquivo` reenvia a saída copiada do Wokwi; ele não fica conectado em tempo real. O `dataHora` enviado à API é a hora da reprodução.
- Leituras que falharem depois das 3 tentativas ficam só no CSV. Não há fila nem reenvio automático.
- Com a API fora do ar, cada leitura segura o gateway durante as tentativas. Na Serial, as linhas se acumulam e chegam atrasadas.
- A API de teste guarda os dados só na memória.
- O DHT11 tem precisão de ±2 °C e mede só o lugar onde está instalado. O limite de 32 °C foi escolhido para o protótipo.
