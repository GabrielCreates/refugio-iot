"""
Testes automatizados do contrato, do gateway e da API de teste.

Rodar a partir da raiz do repositório:
  python -m unittest discover -s testes -v

Os testes de integração sobem a API de teste em 127.0.0.1 (porta livre
escolhida pelo sistema) e fazem requisições HTTP reais. Nada sai do PC.
"""
import json
import os
import sys
import threading
import time
import unittest

import requests

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gateway"))

from contrato import classificar_linha_serial, validar_corpo_api  # noqa: E402
from gateway import enviar, processar_linha  # noqa: E402
from mock_api import criar_servidor  # noqa: E402


def corpo_valido(**alteracoes):
    corpo = {"pontoId": 1, "temperatura": 27.0, "umidade": 60.0, "alerta": False,
             "dataHora": "2026-11-17T12:00:00.000+00:00", "origem": "REFUGIO-UNO-01"}
    corpo.update(alteracoes)
    return corpo


class TesteLinhaSerial(unittest.TestCase):
    """Classificação das linhas que chegam do Arduino (gateway)."""

    def tipo(self, linha, sensor="DHT22"):
        return classificar_linha_serial(linha, sensor)[0]

    def test_leitura_normal(self):
        self.assertEqual(self.tipo('{"seq":1,"temperatura":27.0,"umidade":60.0,"alerta":false}'), "leitura")

    def test_limiar_31_9_32_0_32_1(self):
        self.assertEqual(self.tipo('{"seq":1,"temperatura":31.9,"umidade":60,"alerta":false}'), "leitura")
        self.assertEqual(self.tipo('{"seq":2,"temperatura":32.0,"umidade":60,"alerta":true}'), "leitura")
        self.assertEqual(self.tipo('{"seq":3,"temperatura":32.1,"umidade":60,"alerta":true}'), "leitura")

    def test_alerta_inconsistente(self):
        self.assertEqual(self.tipo('{"seq":1,"temperatura":32.0,"umidade":60,"alerta":false}'), "fora_da_faixa")

    def test_status_e_falha_de_sensor(self):
        self.assertEqual(self.tipo('{"status":"iniciado","dispositivo":"REFUGIO-UNO-01"}'), "status")
        self.assertEqual(self.tipo('{"seq":7,"erro":"falha_leitura_dht11"}'), "falha_sensor")

    def test_linha_que_nao_e_json(self):
        self.assertEqual(self.tipo("Simulation started"), "linha_invalida")
        self.assertEqual(self.tipo('{"seq":1,"temperatura":27.0'), "linha_invalida")

    def test_json_com_formato_inesperado(self):
        self.assertEqual(self.tipo("[1,2,3]"), "formato_invalido")
        self.assertEqual(self.tipo('{"temperatura":27,"umidade":60,"alerta":false}'), "formato_invalido")
        self.assertEqual(self.tipo('{"seq":1,"umidade":60,"alerta":false}'), "formato_invalido")

    def test_tipos_incorretos(self):
        self.assertEqual(self.tipo('{"seq":1,"temperatura":"27","umidade":60,"alerta":false}'), "formato_invalido")
        self.assertEqual(self.tipo('{"seq":1,"temperatura":27,"umidade":60,"alerta":"false"}'), "formato_invalido")
        self.assertEqual(self.tipo('{"seq":true,"temperatura":27,"umidade":60,"alerta":false}'), "formato_invalido")

    def test_faixas_diferentes_por_sensor(self):
        frio = '{"seq":1,"temperatura":-5.0,"umidade":60,"alerta":false}'
        self.assertEqual(self.tipo(frio, "DHT22"), "leitura")
        self.assertEqual(self.tipo(frio, "DHT11"), "fora_da_faixa")
        umido = '{"seq":1,"temperatura":25,"umidade":95,"alerta":false}'
        self.assertEqual(self.tipo(umido, "DHT22"), "leitura")
        self.assertEqual(self.tipo(umido, "DHT11"), "fora_da_faixa")
        self.assertEqual(self.tipo('{"seq":1,"temperatura":25,"umidade":150,"alerta":false}'), "fora_da_faixa")


class TesteContratoApi(unittest.TestCase):
    """Validação do corpo de POST /api/medicoes (API de teste)."""

    def test_valido(self):
        self.assertEqual(validar_corpo_api(corpo_valido())[0], 201)

    def test_campos_ausentes_400(self):
        corpo = corpo_valido()
        del corpo["umidade"]
        self.assertEqual(validar_corpo_api(corpo)[0], 400)

    def test_tipo_incorreto_400(self):
        self.assertEqual(validar_corpo_api(corpo_valido(temperatura="27"))[0], 400)
        self.assertEqual(validar_corpo_api(corpo_valido(alerta=0))[0], 400)
        self.assertEqual(validar_corpo_api(corpo_valido(dataHora="ontem"))[0], 400)

    def test_fora_da_faixa_422(self):
        self.assertEqual(validar_corpo_api(corpo_valido(umidade=150))[0], 422)
        self.assertEqual(validar_corpo_api(corpo_valido(temperatura=90, alerta=True))[0], 422)


class BaseIntegracao(unittest.TestCase):
    kwargs_servidor = {}

    def setUp(self):
        self.servidor, self.estado = criar_servidor("127.0.0.1", 0, verbose=False, **self.kwargs_servidor)
        self.porta = self.servidor.server_address[1]
        self.url = f"http://127.0.0.1:{self.porta}/api/medicoes"
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()
        self.cfg = {"api_url": self.url, "ponto_id": 1, "dispositivo": "REFUGIO-UNO-01",
                    "sensor": "DHT22", "limiar_alerta": 32.0, "tentativas": 3, "timeout_s": 2, "token": ""}

    def tearDown(self):
        if not getattr(self, "encerrado", False):
            self.servidor.shutdown()
            self.servidor.server_close()


class TesteIntegracao(BaseIntegracao):

    def test_envio_e_consulta(self):
        reg = processar_linha('{"seq":1,"temperatura":32.0,"umidade":55.5,"alerta":true}', self.cfg, enviar)
        self.assertEqual((reg["resultado"], reg["status_http"], reg["tentativas"]), ("enviado", 201, 1))
        ultima = requests.get(self.url + "/ultima", timeout=2).json()
        self.assertEqual((ultima["temperatura"], ultima["alerta"], ultima["origem"]), (32.0, True, "REFUGIO-UNO-01"))
        lista = requests.get(self.url + "?limite=5", timeout=2).json()
        self.assertEqual(len(lista), 1)
        saude = requests.get(f"http://127.0.0.1:{self.porta}/api/saude", timeout=2).json()
        self.assertEqual(saude["armazenamento"], "memoria")

    def test_linhas_invalidas_nao_sao_enviadas(self):
        for linha in ("lixo", '{"seq":2,"erro":"falha_leitura_dht11"}',
                      '{"seq":3,"temperatura":"x","umidade":60,"alerta":false}'):
            processar_linha(linha, self.cfg, enviar)
        self.assertEqual(len(self.estado.medicoes), 0)

    def test_rejeicao_da_api_nao_repete(self):
        # Gateway configurado como DHT22 e API como DHT11: -5 °C passa no gateway e a API recusa (422)
        self.estado.sensor = "DHT11"
        reg = processar_linha('{"seq":1,"temperatura":-5.0,"umidade":60,"alerta":false}', self.cfg, enviar)
        self.assertEqual((reg["resultado"], reg["status_http"], reg["tentativas"]), ("rejeitado_api", 422, 1))

    def test_api_desligada(self):
        self.servidor.shutdown()
        self.servidor.server_close()
        self.encerrado = True
        inicio = time.monotonic()
        reg = processar_linha('{"seq":1,"temperatura":27.0,"umidade":60,"alerta":false}', self.cfg, enviar)
        duracao = time.monotonic() - inicio
        self.assertEqual((reg["resultado"], reg["tentativas"], reg["detalhe"]), ("falha_envio", 3, "sem_conexao"))
        self.assertLess(duracao, 10)


class TesteReenvioApos503(BaseIntegracao):
    kwargs_servidor = {"falhas_503": 2}

    def test_503_e_depois_201(self):
        reg = processar_linha('{"seq":1,"temperatura":27.0,"umidade":60,"alerta":false}', self.cfg, enviar)
        self.assertEqual((reg["resultado"], reg["status_http"], reg["tentativas"]), ("enviado", 201, 3))


class TesteToken(BaseIntegracao):
    kwargs_servidor = {"token": "segredo-de-teste"}

    def test_sem_token_401_e_com_token_201(self):
        reg = processar_linha('{"seq":1,"temperatura":27.0,"umidade":60,"alerta":false}', self.cfg, enviar)
        self.assertEqual((reg["resultado"], reg["status_http"]), ("rejeitado_api", 401))
        self.cfg["token"] = "segredo-de-teste"
        reg = processar_linha('{"seq":2,"temperatura":27.0,"umidade":60,"alerta":false}', self.cfg, enviar)
        self.assertEqual(reg["resultado"], "enviado")
        self.assertNotIn("segredo", json.dumps(reg))  # o token não vai para o log


if __name__ == "__main__":
    unittest.main()
