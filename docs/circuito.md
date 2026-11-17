# Circuito do protótipo

O mesmo firmware funciona em dois cenários. A diferença é o sensor e a linha `#define SIMULACAO_WOKWI`.

| Cenário | Sensor | `SIMULACAO_WOKWI` | Situação |
|---|---|---|---|
| Simulação no Wokwi | DHT22 (o Wokwi não oferece DHT11) | **ativa** (como está no repositório) | Testado no Wokwi |
| Arduino físico | DHT11 | **comentada**: `// #define SIMULACAO_WOKWI` | Montagem descrita abaixo |

> Antes de gravar no Arduino físico com DHT11, comente a linha `#define SIMULACAO_WOKWI` no início de `arduino/refugio_dht11/refugio_dht11.ino`. Se ela ficar ativa, a biblioteca usa o protocolo do DHT22 e as leituras do DHT11 falham ou saem erradas.

## Componentes

| Qtd | Componente | Função |
|---|---|---|
| 1 | Arduino Uno R3 | Lê o sensor, aplica o limiar, aciona o LED e envia JSON pela Serial |
| 1 | DHT11 (físico) ou DHT22 (Wokwi) | Temperatura e umidade relativa |
| 1 | LED vermelho 5 mm | Indicador local de calor (aceso com temperatura ≥ 32 °C) |
| 1 | Resistor 220 Ω | Limita a corrente do LED |
| 1 | Protoboard e jumpers | Montagem física |
| 1 | Cabo USB A-B | Alimentação do Uno e comunicação Serial com o PC gateway |

## Características dos sensores (datasheets do fabricante)

| | DHT11 | DHT22 (AM2302) |
|---|---|---|
| Faixa de temperatura | 0 a 50 °C | -40 a 80 °C |
| Faixa de umidade | 20 a 90 %UR | 0 a 100 %UR |
| Precisão | ±2 °C, ±5 %UR | < ±0,5 °C, ±2 %UR (máx. ±5 %UR) |
| Resolução | 1 °C, 1 %UR | 0,1 °C, 0,1 %UR |
| Intervalo entre leituras | mais de 2 s (manual Aosong) | média de 2 s |

O firmware lê a cada **2 s**, o que atende os dois sensores (no DHT11 físico, se aparecerem falhas de leitura frequentes, aumente `INTERVALO_MS` para 2500). O gateway e a API usam essas faixas para recusar valores impossíveis (`gateway/contrato.py`). A faixa aplicada depende do campo `sensor` em `gateway/config.json` (`DHT22` para o Wokwi, `DHT11` para o físico).

Fontes: [DHT11 – datasheet Aosong (versão traduzida)](https://ece-classes.usc.edu/ee459/library/datasheets/DHT11.pdf) · [DHT11 – manual Aosong](https://openlab.citytech.cuny.edu/cet4711/files/2018/05/DHT11.pdf) · [DHT22 – datasheet Aosong](https://cdn.sparkfun.com/assets/f/7/d/9/c/DHT22.pdf) · [Wokwi – referência do DHT22](https://docs.wokwi.com/parts/wokwi-dht22)

## Pinagem de cada sensor

A ordem física dos pinos **muda entre o sensor puro e os módulos**. Confira sempre a serigrafia (`+`, `-`, `S`/`OUT`/`DATA`) da peça que vocês tiverem.

**DHT22 no Wokwi** (pinos do componente `wokwi-dht22`):

| Pino Wokwi | Função | Ligação |
|---|---|---|
| VCC | Alimentação | Arduino 5V |
| SDA | Dados | Arduino D2 |
| NC | Não conectado | — |
| GND | Terra | Arduino GND |

O modelo do Wokwi não precisa de resistor de pull-up.

**Sensor puro de 4 pinos (DHT11 ou DHT22)**, contando da esquerda para a direita com a grade virada para você, conforme os datasheets:

| Pino | Função | Ligação |
|---|---|---|
| 1 | VDD | Arduino 5V |
| 2 | DATA | Arduino D2 e resistor de pull-up para 5V (circuito típico do datasheet) |
| 3 | NC | — |
| 4 | GND | Arduino GND |

**Módulo de 3 pinos (placa com o sensor)**: normalmente já traz o pull-up, mas a ordem varia de fabricante para fabricante (`+ OUT -`, `S + -` etc.). Ligue pelo rótulo impresso: `+`/VCC → 5V, `OUT`/`S`/DATA → D2, `-`/GND → GND.

## Ligações do LED

| De | Para |
|---|---|
| Arduino D8 | Resistor 220 Ω |
| Resistor 220 Ω | Ânodo do LED (perna longa) |
| Cátodo do LED (perna curta) | Arduino GND |

## Esquema

```
              +----------------------+
 Sensor VCC --| 5V                   |
 Sensor DATA--| D2               USB |=====> PC gateway (Serial 9600 baud, JSON)
 Sensor GND --| GND                  |
              |                   D8 |--[220 Ω]--|>|-- GND   (LED)
              |     Arduino Uno      |
              +----------------------+
```

## Arquivo do Wokwi

`wokwi/diagram.json` contém exatamente estas ligações (DHT22 em D2, LED com resistor em D8). As temperaturas iniciais são 27 °C e 60 %UR. As bibliotecas estão em `wokwi/libraries.txt`.
