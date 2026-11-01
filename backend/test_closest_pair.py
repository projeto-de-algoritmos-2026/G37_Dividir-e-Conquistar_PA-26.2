import random
import unittest

from closest_pair import MAX_VIZINHOS_FAIXA, Ponto, forca_bruta, par_mais_proximo
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


class TestGeo(unittest.TestCase):
    def test_x_para_lon_e_inverso_de_projetar(self):
        lat_ref = -15.8
        for lat, lon in [(-15.79, -47.88), (-16.02, -48.06), (-15.6, -47.5)]:
            x, _ = projetar(lat, lon, lat_ref)
            self.assertAlmostEqual(x_para_lon(x, lat_ref), lon, places=9)


if __name__ == "__main__":
    unittest.main()