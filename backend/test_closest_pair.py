import random
import unittest

from closest_pair import (
    MAX_VIZINHOS_FAIXA,
    Ponto,
    forca_bruta,
    par_mais_proximo,
    remover_duplicatas,
)
from geo import projetar, x_para_lon


def gerar(n, rng, inteiros=False, faixa=1000):
    if inteiros:
        # coordenadas inteiras pequenas -> muitos empates e pontos repetidos
        return [Ponto(i, rng.randint(0, 10), rng.randint(0, 10)) for i in range(n)]
    return [Ponto(i, rng.uniform(0, faixa), rng.uniform(0, faixa)) for i in range(n)]


class TestParMaisProximo(unittest.TestCase):
    def test_dois_pontos(self):
        r = par_mais_proximo([Ponto(0, 0, 0), Ponto(1, 3, 4)])
        self.assertAlmostEqual(r.distancia, 5.0)

    def test_tres_pontos(self):
        r = par_mais_proximo([Ponto(0, 0, 0), Ponto(1, 10, 10), Ponto(2, 10, 11)])
        self.assertAlmostEqual(r.distancia, 1.0)

    def test_menos_de_dois_pontos_da_erro(self):
        with self.assertRaises(ValueError):
            par_mais_proximo([Ponto(0, 1, 1)])

    def test_caso_base_invalido(self):
        with self.assertRaises(ValueError):
            par_mais_proximo([Ponto(0, 0, 0), Ponto(1, 1, 1)], limite_caso_base=2)

    def test_todos_no_mesmo_x(self):
        pontos = [Ponto(i, 5.0, float(i * i)) for i in range(40)]
        self.assertAlmostEqual(
            par_mais_proximo(pontos).distancia, forca_bruta(pontos).distancia
        )

    def test_todos_no_mesmo_y(self):
        pontos = [Ponto(i, float(i * 3), 7.0) for i in range(40)]
        self.assertAlmostEqual(
            par_mais_proximo(pontos).distancia, forca_bruta(pontos).distancia
        )

    def test_pontos_repetidos_distancia_zero(self):
        pontos = [Ponto(i, float(i), float(i)) for i in range(20)]
        pontos.append(Ponto(20, 7.0, 7.0))  # repete o ponto 7
        self.assertEqual(par_mais_proximo(pontos).distancia, 0.0)

    def test_aleatorios_contra_forca_bruta(self):
        rng = random.Random(42)
        for _ in range(500):
            n = rng.randint(2, 80)
            inteiros = rng.random() < 0.5
            pontos = gerar(n, rng, inteiros=inteiros)
            base = rng.choice([3, 4, 7])
            esperado = forca_bruta(pontos).distancia
            obtido = par_mais_proximo(pontos, limite_caso_base=base).distancia
            self.assertAlmostEqual(obtido, esperado, msg=f"n={n} base={base}")

    def test_conjunto_grande(self):
        rng = random.Random(7)
        pontos = gerar(1500, rng)
        self.assertAlmostEqual(
            par_mais_proximo(pontos).distancia, forca_bruta(pontos).distancia
        )

    def test_faixa_nunca_passa_do_limite_de_vizinhos(self):
        rng = random.Random(3)
        for _ in range(100):
            pontos = gerar(rng.randint(10, 200), rng, inteiros=rng.random() < 0.5)
            r = par_mais_proximo(pontos, max_nivel_passos=20)
            for passo in r.passos:
                self.assertLessEqual(passo.max_vizinhos_por_ponto, MAX_VIZINHOS_FAIXA)

    def test_passos_registrados_ate_o_nivel_pedido(self):
        rng = random.Random(1)
        r = par_mais_proximo(gerar(200, rng), max_nivel_passos=2)
        self.assertTrue(all(p.nivel <= 2 for p in r.passos))
        self.assertEqual(r.passos[0].nivel, 0)  # primeiro passo e a divisao principal
        self.assertEqual(r.passos[0].n_pontos, 200)


class TestRemoverDuplicatas(unittest.TestCase):
    def test_cluster_de_tres_fica_so_com_um(self):
        # tres pontos quase no mesmo lugar e dois bem distantes
        pontos = [Ponto(0, 0, 0), Ponto(1, 1, 0), Ponto(2, 0, 1), Ponto(3, 500, 0), Ponto(4, 0, 900)]
        restantes, dups, truncada = remover_duplicatas(pontos, limiar=10)
        self.assertEqual(len(dups), 2)
        self.assertEqual(len(restantes), 3)
        self.assertFalse(truncada)
        self.assertGreaterEqual(par_mais_proximo(restantes).distancia, 10)

    def test_sem_duplicatas_nao_remove_nada(self):
        pontos = [Ponto(i, i * 100.0, 0.0) for i in range(6)]
        restantes, dups, truncada = remover_duplicatas(pontos, limiar=10)
        self.assertEqual(len(restantes), 6)
        self.assertEqual(dups, [])
        self.assertFalse(truncada)

    def test_escolha_de_qual_remover_e_respeitada(self):
        pontos = [Ponto(0, 0, 0), Ponto(1, 1, 0), Ponto(2, 1000, 0)]
        restantes, dups, _ = remover_duplicatas(
            pontos, limiar=10, escolher_remocao=lambda a, b: a if a.id == 0 else b
        )
        self.assertEqual((dups[0].removido.id, dups[0].mantido.id), (0, 1))
        self.assertEqual({p.id for p in restantes}, {1, 2})

    def test_limite_de_remocoes_marca_truncada(self):
        pontos = [Ponto(i, float(i), 0.0) for i in range(10)]  # 10 pontos colados
        restantes, dups, truncada = remover_duplicatas(pontos, limiar=100, limite_remocoes=3)
        self.assertEqual(len(dups), 3)
        self.assertEqual(len(restantes), 7)
        self.assertTrue(truncada)

    def test_tempo_maximo_marca_truncada(self):
        pontos = [Ponto(i, float(i), 0.0) for i in range(10)]
        _, _, truncada = remover_duplicatas(pontos, limiar=100, tempo_maximo_s=0)
        self.assertTrue(truncada)

    def test_todos_iguais_termina_com_dois(self):
        pontos = [Ponto(i, 5.0, 5.0) for i in range(6)]
        restantes, dups, truncada = remover_duplicatas(pontos, limiar=1)
        self.assertEqual(len(restantes), 2)
        self.assertEqual(len(dups), 4)
        self.assertFalse(truncada)

    def test_invariantes_em_conjuntos_aleatorios(self):
        rng = random.Random(11)
        for _ in range(200):
            pontos = gerar(rng.randint(2, 60), rng, inteiros=True)  # muitos empates
            limiar = rng.choice([1, 2, 3])
            restantes, dups, _ = remover_duplicatas(pontos, limiar=limiar)

            ids_restantes = {p.id for p in restantes}
            ids_removidos = {d.removido.id for d in dups}
            self.assertEqual(len(ids_restantes) + len(ids_removidos), len(pontos))
            self.assertFalse(ids_restantes & ids_removidos)
            self.assertTrue(all(d.distancia < limiar for d in dups))
            if len(restantes) > 2:  # sobrou so lugar diferente
                self.assertGreaterEqual(forca_bruta(restantes).distancia, limiar)


class TestGeo(unittest.TestCase):
    def test_x_para_lon_e_inverso_de_projetar(self):
        lat_ref = -15.8
        for lat, lon in [(-15.79, -47.88), (-16.02, -48.06), (-15.6, -47.5)]:
            x, _ = projetar(lat, lon, lat_ref)
            self.assertAlmostEqual(x_para_lon(x, lat_ref), lon, places=9)


if __name__ == "__main__":
    unittest.main()