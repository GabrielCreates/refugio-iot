// Teste de LÓGICA do firmware no PC: compila o .ino real com Arduino.h/DHT.h falsos.
// Não substitui o teste no Wokwi nem no hardware (não testa tempo real, fiação ou sensor).
#include "Arduino.h"
unsigned long g_millis = 0;
int g_pinos[20] = {0};
float g_temp = 27.0f, g_umid = 60.0f;
int g_tipo_dht = 0;
SerialFake Serial;
#include "../../arduino/refugio_dht11/refugio_dht11.ino"

static int falhas = 0, total = 0;
static void checar(bool ok, const char* nome, const std::string& obtido) {
  total++;
  if (!ok) falhas++;
  printf("[%s] %s\n       saída: %s\n", ok ? "PASSOU" : "FALHOU", nome, obtido.c_str());
}
// Avança o tempo e executa o loop; devolve a última linha impressa.
static std::string ciclo(float t, float u, unsigned long avancar_ms = 2000) {
  g_temp = t; g_umid = u;
  Serial.saida.clear();
  g_millis += avancar_ms;
  loop();
  std::string s = Serial.saida;
  if (!s.empty() && s.back() == '\n') s.pop_back();
  return s;
}

int main() {
  setup();
  std::string s0 = Serial.saida; s0.pop_back();
  checar(s0 == "{\"status\":\"iniciado\",\"dispositivo\":\"REFUGIO-UNO-01\"}", "F1 linha de status ao ligar", s0);
  checar(g_tipo_dht == DHT22, "F2 SIMULACAO_WOKWI ativa seleciona DHT22", g_tipo_dht == DHT22 ? "DHT22" : "outro");

  std::string s = ciclo(27.0f, 60.0f, 500);
  checar(s.empty(), "F3 antes de 2 s não lê (sem delay bloqueante)", s.empty() ? "(nada)" : s);

  s = ciclo(27.0f, 60.0f, 1500);
  checar(s == "{\"seq\":1,\"temperatura\":27.0,\"umidade\":60.0,\"alerta\":false}" && g_pinos[8] == LOW,
         "F4 leitura normal 27 °C: JSON correto, LED apagado", s);

  s = ciclo(31.9f, 60.0f);
  checar(s.find("\"alerta\":false") != std::string::npos && g_pinos[8] == LOW, "F5 31,9 °C: abaixo do limiar, LED apagado", s);

  s = ciclo(32.0f, 60.0f);
  checar(s.find("\"temperatura\":32.0") != std::string::npos && s.find("\"alerta\":true") != std::string::npos
         && g_pinos[8] == HIGH, "F6 exatamente 32,0 °C: alerta e LED aceso (>=)", s);

  s = ciclo(31.96f, 60.0f);
  checar(s.find("\"temperatura\":32.0") != std::string::npos && s.find("\"alerta\":true") != std::string::npos,
         "F7 31,96 °C arredonda para 32,0 e alerta coerente com o valor enviado", s);

  s = ciclo(35.0f, 60.0f);
  checar(s.find("\"alerta\":true") != std::string::npos && g_pinos[8] == HIGH, "F8 35 °C: LED aceso", s);

  s = ciclo(25.0f, 60.0f);
  checar(s.find("\"alerta\":false") != std::string::npos && g_pinos[8] == LOW, "F9 volta a 25 °C: LED apaga", s);

  ciclo(35.0f, 60.0f);  // acende antes da falha
  s = ciclo(NAN, NAN);
  checar(s.find("\"erro\":\"falha_leitura_dht11\"") != std::string::npos && g_pinos[8] == LOW,
         "F10 sensor desconectado (NaN): linha de erro e LED apagado", s);

  s = ciclo(27.0f, 60.0f);
  checar(s.rfind("{\"seq\":9,", 0) == 0, "F11 seq continua após a falha (9ª tentativa de leitura)", s);

  printf("\nResultado: %d de %d verificações passaram.\n", total - falhas, total);
  return falhas == 0 ? 0 : 1;
}
