import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

import locais


def resposta_falsa(corpo: dict):
    """Imita o objeto devolvido por urllib.request.urlopen."""
    resposta = mock.MagicMock()
    resposta.read.return_value = json.dumps(corpo).encode("utf-8")
    resposta.__enter__.return_value = resposta
    resposta.__exit__.return_value = False
    return resposta


def erro_http(codigo: int):
    return urllib.error.HTTPError("http://x", codigo, "erro", {}, None)


ELEMENTOS = [
    {"type": "node", "id": 1, "lat": -15.8, "lon": -47.9, "tags": {"name": "Farmácia A"}},
    {"type": "way", "id": 2, "center": {"lat": -15.81, "lon": -47.91}, "tags": {}},
    {"type": "node", "id": 3, "lat": -15.9, "lon": -47.95},
    {"type": "relation", "id": 4},  # sem posicao
]


class TestConversao(unittest.TestCase):
    def test_no_usa_lat_lon_e_way_usa_center(self):
        resultado = locais.elementos_para_locais(ELEMENTOS)
        self.assertEqual(len(resultado), 3)  # a relation sem posicao some
        self.assertEqual(resultado[0], {"lat": -15.8, "lon": -47.9, "nome": "Farmácia A", "osm": "node/1"})
        self.assertEqual((resultado[1]["lat"], resultado[1]["lon"]), (-15.81, -47.91))
        self.assertEqual(resultado[1]["osm"], "way/2")

    def test_sem_nome_vira_none(self):
        self.assertIsNone(locais.elementos_para_locais(ELEMENTOS)[2]["nome"])

    def test_consulta_por_area_e_por_caixa(self):
        por_area = locais.montar_consulta('["amenity"="pharmacy"]', usar_area=True)
        self.assertIn("(area.df)", por_area)
        self.assertIn('"name"="Distrito Federal"', por_area)
        por_caixa = locais.montar_consulta('["amenity"="pharmacy"]', usar_area=False)
        self.assertNotIn("area.df", por_caixa)
        self.assertIn("(-16.05,-48.29,-15.5,-47.31)", por_caixa)
        self.assertTrue(por_caixa.endswith("out center qt;"))


class TestLeitura(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(locais, "PASTA_DADOS", Path(self.pasta.name))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.pasta.cleanup)

    def test_le_arquivo_no_formato_bruto_do_overpass(self):
        (Path(self.pasta.name) / "farmacia.json").write_text(
            json.dumps({"version": 0.6, "elements": ELEMENTOS}), encoding="utf-8"
        )
        self.assertEqual(len(locais.carregar_locais("farmacia")), 3)

    def test_categoria_desconhecida(self):
        with self.assertRaises(KeyError):
            locais.carregar_locais("padaria")

    def test_categoria_sem_arquivo(self):
        with self.assertRaises(FileNotFoundError):
            locais.carregar_locais("hospital")

    def test_listar_categorias_indica_disponibilidade(self):
        (Path(self.pasta.name) / "escola.json").write_text('{"elements": []}', encoding="utf-8")
        por_chave = {c["chave"]: c["disponivel"] for c in locais.listar_categorias()}
        self.assertTrue(por_chave["escola"])
        self.assertFalse(por_chave["farmacia"])
        self.assertEqual(set(por_chave), set(locais.CATEGORIAS))


class TestConsultarOverpass(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(locais.time, "sleep")
        self.sleep = patcher.start()  # nao espera de verdade
        self.addCleanup(patcher.stop)

    def consultar(self, comportamentos, **opcoes):
        """Roda consultar_overpass com urlopen simulado; devolve (resultado, mock)."""
        with mock.patch.object(locais.urllib.request, "urlopen", side_effect=comportamentos) as urlopen:
            resultado = locais.consultar_overpass("consulta", log=lambda m: None, **opcoes)
        return resultado, urlopen

    def test_sucesso_na_primeira_tentativa_envia_user_agent(self):
        resultado, urlopen = self.consultar([resposta_falsa({"elements": ELEMENTOS})])
        self.assertEqual(len(resultado["elements"]), 4)
        pedido = urlopen.call_args.args[0]
        self.assertIn("par-pontos-df", pedido.get_header("User-agent"))
        self.assertEqual(urlopen.call_count, 1)
        self.sleep.assert_not_called()

    def test_429_tenta_de_novo_com_espera_crescente(self):
        resultado, urlopen = self.consultar(
            [erro_http(429), resposta_falsa({"elements": ELEMENTOS})],
            servidores=["https://um"], tentativas_por_servidor=2, espera_base_s=10,
        )
        self.assertEqual(urlopen.call_count, 2)
        self.sleep.assert_called_once_with(10)
        self.assertEqual(len(resultado["elements"]), 4)

    def test_servidor_principal_fora_cai_no_de_reserva(self):
        urls = []

        def urlopen(pedido, timeout):
            urls.append(pedido.full_url)
            if "principal" in pedido.full_url:
                raise erro_http(504)
            return resposta_falsa({"elements": ELEMENTOS})

        with mock.patch.object(locais.urllib.request, "urlopen", side_effect=urlopen):
            locais.consultar_overpass(
                "consulta", servidores=["https://principal", "https://reserva"],
                tentativas_por_servidor=2, log=lambda m: None,
            )
        self.assertEqual(urls, ["https://principal", "https://principal", "https://reserva"])

    def test_remark_de_runtime_error_conta_como_falha(self):
        # o Overpass responde 200 mesmo quando a consulta estoura o tempo
        timeout = resposta_falsa({"elements": [], "remark": "runtime error: Query timed out"})
        resultado, urlopen = self.consultar(
            [timeout, resposta_falsa({"elements": ELEMENTOS})],
            servidores=["https://um"], tentativas_por_servidor=2,
        )
        self.assertEqual(urlopen.call_count, 2)
        self.assertEqual(len(resultado["elements"]), 4)

    def test_http_400_nao_repete(self):
        with mock.patch.object(locais.urllib.request, "urlopen", side_effect=erro_http(400)) as urlopen:
            with self.assertRaises(locais.ErroDownload):
                locais.consultar_overpass("consulta", log=lambda m: None)
        self.assertEqual(urlopen.call_count, 1)

    def test_tudo_falhando_levanta_erro_com_o_ultimo_motivo(self):
        with mock.patch.object(locais.urllib.request, "urlopen", side_effect=TimeoutError("lento")):
            with self.assertRaises(locais.ErroDownload) as contexto:
                locais.consultar_overpass(
                    "consulta", servidores=["https://a", "https://b"],
                    tentativas_por_servidor=1, log=lambda m: None,
                )
        self.assertIn("TimeoutError", str(contexto.exception))

    def test_resposta_que_nao_e_json_conta_como_falha(self):
        lixo = mock.MagicMock()
        lixo.read.return_value = b"<html>erro</html>"
        lixo.__enter__.return_value = lixo
        lixo.__exit__.return_value = False
        with mock.patch.object(locais.urllib.request, "urlopen", return_value=lixo):
            with self.assertRaises(locais.ErroDownload):
                locais.consultar_overpass(
                    "consulta", servidores=["https://a"], tentativas_por_servidor=1,
                    log=lambda m: None,
                )


class TestBaixarCategoria(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(locais, "PASTA_DADOS", Path(self.pasta.name) / "data")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.pasta.cleanup)

    def test_grava_arquivo_com_data_do_download(self):
        with mock.patch.object(locais, "consultar_overpass", return_value={"elements": ELEMENTOS}):
            total = locais.baixar_categoria("farmacia", log=lambda m: None)
        self.assertEqual(total, 3)
        salvo = json.loads(locais.caminho_arquivo("farmacia").read_text(encoding="utf-8"))
        self.assertIn("baixado_em", salvo)
        self.assertEqual(len(locais.carregar_locais("farmacia")), 3)  # volta a ser legivel

    def test_area_vazia_cai_na_caixa_do_df(self):
        consultas = []

        def falso(consulta, **_):
            consultas.append(consulta)
            return {"elements": []} if "area.df" in consulta else {"elements": ELEMENTOS}

        with mock.patch.object(locais, "consultar_overpass", side_effect=falso):
            total = locais.baixar_categoria("escola", log=lambda m: None)
        self.assertEqual(total, 3)
        self.assertEqual(len(consultas), 2)
        self.assertNotIn("area.df", consultas[1])

    def test_poucos_locais_nao_grava_arquivo(self):
        um_so = {"elements": [ELEMENTOS[0]]}
        with mock.patch.object(locais, "consultar_overpass", return_value=um_so):
            with self.assertRaises(locais.ErroDownload):
                locais.baixar_categoria("hospital", log=lambda m: None)
        self.assertFalse(locais.caminho_arquivo("hospital").exists())

    def test_falha_de_rede_preserva_arquivo_antigo(self):
        locais.PASTA_DADOS.mkdir()
        antigo = locais.caminho_arquivo("posto")
        antigo.write_text('{"elements": []}', encoding="utf-8")
        with mock.patch.object(locais, "consultar_overpass", side_effect=locais.ErroDownload("fora")):
            with self.assertRaises(locais.ErroDownload):
                locais.baixar_categoria("posto", log=lambda m: None)
        self.assertEqual(antigo.read_text(encoding="utf-8"), '{"elements": []}')


if __name__ == "__main__":
    unittest.main()