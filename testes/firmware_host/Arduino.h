// Arduino.h mínimo para compilar o firmware no PC (teste de lógica, não é hardware).
#pragma once
#include <cmath>
#include <cstdio>
#include <string>
using std::isnan;

#define HIGH 1
#define LOW 0
#define OUTPUT 1
// Mesmo comportamento do round() do Arduino AVR (macro que devolve long)
#define round(x) ((x) >= 0 ? (long)((x) + 0.5) : (long)((x) - 0.5))

extern unsigned long g_millis;
extern int g_pinos[20];
inline unsigned long millis() { return g_millis; }
inline void pinMode(int, int) {}
inline void digitalWrite(int pino, int valor) { g_pinos[pino] = valor; }

struct SerialFake {
  std::string saida;
  void begin(long) {}
  void print(const char* s) { saida += s; }
  void print(unsigned long v) { saida += std::to_string(v); }
  void print(float v, int casas) {            // Serial.print(float, casas)
    char buf[32]; snprintf(buf, sizeof buf, "%.*f", casas, (double)v); saida += buf;
  }
  void println(const char* s) { saida += s; saida += "\n"; }
};
extern SerialFake Serial;
