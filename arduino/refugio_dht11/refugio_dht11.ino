/*
 * REFÚGIO - Protótipo IoT (Global Solution 2026/2 - CitizenTech)
 * Arduino Uno + DHT11 (circuito físico) ou DHT22 (simulação no Wokwi) + LED
 *
 * - Lê temperatura e umidade a cada 2 segundos, sem delay() bloqueante
 * - Acende o LED quando a temperatura é >= 32 °C (limiar DIDÁTICO, não é
 *   critério oficial de risco à saúde) e apaga abaixo disso
 * - Envia cada leitura pela Serial (USB, 9600 baud) como UM objeto JSON por linha:
 *     {"seq":12,"temperatura":27.0,"umidade":61.0,"alerta":false}
 *     {"seq":13,"erro":"falha_leitura_dht11"}            (falha de leitura)
 *   "seq" começa em 1 a cada reinício e identifica a ordem das tentativas de
 *   leitura. A identificação do ponto (REFUGIO-UNO-01) é enviada na linha de
 *   status ao ligar e acrescentada pelo gateway em cada medição.
 *
 * Biblioteca: "DHT sensor library" (Adafruit) + "Adafruit Unified Sensor"
 */

#include <DHT.h>

// O Wokwi (simulador) não tem DHT11, só DHT22. Para simular, deixe a linha
// abaixo ativa. ANTES do upload para um Arduino físico com DHT11, comente-a
// (// #define SIMULACAO_WOKWI); caso contrário a biblioteca usará o protocolo do DHT22.
#define SIMULACAO_WOKWI

#define PINO_DHT      2       // pino de dados do sensor
#ifdef SIMULACAO_WOKWI
  #define TIPO_DHT    DHT22
#else
  #define TIPO_DHT    DHT11
#endif
#define PINO_LED      8       // LED indicador (com resistor de 220 ohms)
#define LIMIAR_TEMP   32.0    // °C - limiar didático de calor
#define INTERVALO_MS  2000    // datasheets: DHT22 exige >= 2 s entre leituras; 2 s atende os dois sensores

DHT dht(PINO_DHT, TIPO_DHT);
unsigned long ultimaLeitura = 0;
unsigned long sequencia = 0;

void setup() {
  Serial.begin(9600);
  pinMode(PINO_LED, OUTPUT);
  digitalWrite(PINO_LED, LOW);
  dht.begin();
  Serial.println("{\"status\":\"iniciado\",\"dispositivo\":\"REFUGIO-UNO-01\"}");
}

void loop() {
  if (millis() - ultimaLeitura < INTERVALO_MS) return;
  ultimaLeitura = millis();
  sequencia++;

  float umidade = dht.readHumidity();
  float temperatura = dht.readTemperature();

  // Falha de leitura (sensor desconectado ou com defeito)
  if (isnan(umidade) || isnan(temperatura)) {
    digitalWrite(PINO_LED, LOW);
    Serial.print("{\"seq\":");
    Serial.print(sequencia);
    Serial.println(",\"erro\":\"falha_leitura_dht11\"}");
    return;
  }

  // Arredonda para 1 casa ANTES de comparar: assim o valor enviado no JSON e o
  // valor usado para o alerta são o mesmo (ex.: 31.96 vira 32.0 e acende o LED).
  temperatura = round(temperatura * 10.0) / 10.0;
  umidade = round(umidade * 10.0) / 10.0;

  bool alerta = temperatura >= LIMIAR_TEMP;
  digitalWrite(PINO_LED, alerta ? HIGH : LOW);

  // Exemplo: {"seq":12,"temperatura":27.0,"umidade":61.0,"alerta":false}
  Serial.print("{\"seq\":");
  Serial.print(sequencia);
  Serial.print(",\"temperatura\":");
  Serial.print(temperatura, 1);
  Serial.print(",\"umidade\":");
  Serial.print(umidade, 1);
  Serial.print(",\"alerta\":");
  Serial.print(alerta ? "true" : "false");
  Serial.println("}");
}
