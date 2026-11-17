// DHT.h falso: devolve os valores definidos pelo teste.
#pragma once
#include <cmath>
#define DHT11 11
#define DHT22 22
extern float g_temp, g_umid;
extern int g_tipo_dht;
class DHT {
 public:
  DHT(int, int tipo) { g_tipo_dht = tipo; }
  void begin() {}
  float readTemperature() { return g_temp; }
  float readHumidity() { return g_umid; }
};
