import math
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

# Numero maximo de vizinhos (seguintes em y) que cada ponto da faixa precisa
# comparar. Prova classica: numa caixa delta x 2*delta cabem no maximo 8
# pontos com distancia >= delta entre si, ou seja, 7 alem do proprio ponto.
MAX_VIZINHOS_FAIXA = 7


@dataclass(frozen=True)
class Ponto:
    id: int  # posicao original do ponto na lista de entrada
    x: float
    y: float


@dataclass
class PassoDivisao:
    """Registro de uma chamada recursiva (usado para visualizar o algoritmo)."""

    nivel: int
    n_pontos: int
    x_divisao: float
    delta_lados: float = math.inf  # melhor distancia achada nas duas metades
    delta_final: float = math.inf  # depois de olhar a faixa central
    pontos_na_faixa: int = 0
    comparacoes_faixa: int = 0
    max_vizinhos_por_ponto: int = 0


@dataclass
class Resultado:
    ponto_a: Ponto
    ponto_b: Ponto
    distancia: float
    comparacoes: int
    passos: List[PassoDivisao] = field(default_factory=list)


def distancia(a: Ponto, b: Ponto) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def _forca_bruta_trecho(
    pontos: List[Ponto], contador: Dict[str, int]
) -> Tuple[float, Ponto, Ponto]:
    """Compara todos os pares de uma lista pequena (caso base)."""
    melhor = math.inf
    par: Optional[Tuple[Ponto, Ponto]] = None
    for i in range(len(pontos)):
        for j in range(i + 1, len(pontos)):
            contador["comparacoes"] += 1
            d = distancia(pontos[i], pontos[j])
            if d < melhor:
                melhor = d
                par = (pontos[i], pontos[j])
    assert par is not None
    return melhor, par[0], par[1]


def _mesclar_por_y(esq: List[Ponto], dir: List[Ponto]) -> List[Ponto]:
    """Junta duas listas ja ordenadas por y numa so (passo do merge sort)."""
    resultado: List[Ponto] = []
    i = j = 0
    while i < len(esq) and j < len(dir):
        if esq[i].y <= dir[j].y:
            resultado.append(esq[i])
            i += 1
        else:
            resultado.append(dir[j])
            j += 1
    resultado.extend(esq[i:])
    resultado.extend(dir[j:])
    return resultado


def _resolver(
    por_x: List[Ponto],
    limite_caso_base: int,
    nivel: int,
    max_nivel_passos: int,
    contador: Dict[str, int],
    passos: List[PassoDivisao],
) -> Tuple[float, Ponto, Ponto, List[Ponto]]:
    """
    Recebe os pontos ordenados por x. Devolve:
    (menor distancia, ponto a, ponto b, os mesmos pontos ordenados por y)
    """
    n = len(por_x)

    # CASO BASE: poucos pontos, forca bruta resolve direto
    if n <= limite_caso_base:
        d, a, b = _forca_bruta_trecho(por_x, contador)
        return d, a, b, sorted(por_x, key=lambda p: p.y)

    # DIVIDIR: corta no meio por uma linha vertical em x_divisao
    meio = n // 2
    x_divisao = por_x[meio].x

    passo: Optional[PassoDivisao] = None
    if nivel <= max_nivel_passos:
        passo = PassoDivisao(nivel=nivel, n_pontos=n, x_divisao=x_divisao)
        passos.append(passo)  # ordem de visita: de cima para baixo

    # CONQUISTAR: resolve cada metade
    d_esq, a_esq, b_esq, y_esq = _resolver(
        por_x[:meio], limite_caso_base, nivel + 1, max_nivel_passos, contador, passos
    )
    d_dir, a_dir, b_dir, y_dir = _resolver(
        por_x[meio:], limite_caso_base, nivel + 1, max_nivel_passos, contador, passos
    )

    if d_esq <= d_dir:
        delta, melhor_a, melhor_b = d_esq, a_esq, b_esq
    else:
        delta, melhor_a, melhor_b = d_dir, a_dir, b_dir
    delta_lados = delta

    por_y = _mesclar_por_y(y_esq, y_dir)

    # COMBINAR: so interessam pontos a menos de `delta` da linha de corte
    faixa = [p for p in por_y if abs(p.x - x_divisao) < delta_lados]

    comparacoes_faixa = 0
    max_vizinhos = 0
    for i in range(len(faixa)):
        j = i + 1
        vizinhos = 0
        # cada ponto so olha os proximos (em y) enquanto estiverem a menos
        # de `delta` de distancia vertical, e no maximo MAX_VIZINHOS_FAIXA
        while (
            j < len(faixa)
            and j - i <= MAX_VIZINHOS_FAIXA
            and faixa[j].y - faixa[i].y < delta
        ):
            contador["comparacoes"] += 1
            comparacoes_faixa += 1
            vizinhos += 1
            d = distancia(faixa[i], faixa[j])
            if d < delta:
                delta, melhor_a, melhor_b = d, faixa[i], faixa[j]
            j += 1
        max_vizinhos = max(max_vizinhos, vizinhos)

    if passo is not None:
        passo.delta_lados = delta_lados
        passo.delta_final = delta
        passo.pontos_na_faixa = len(faixa)
        passo.comparacoes_faixa = comparacoes_faixa
        passo.max_vizinhos_por_ponto = max_vizinhos

    return delta, melhor_a, melhor_b, por_y


def par_mais_proximo(
    pontos: List[Ponto], limite_caso_base: int = 3, max_nivel_passos: int = 4
) -> Resultado:
    """
    Acha o par de pontos mais proximo em O(n log n).

    limite_caso_base: com quantos pontos ou menos a recursao para e usa
        forca bruta (minimo 3, senao uma metade poderia ficar com 1 ponto).
    max_nivel_passos: ate que nivel da recursao registrar os passos para
        visualizacao (0 = so a divisao principal).
    """
    if len(pontos) < 2:
        raise ValueError("Sao necessarios pelo menos 2 pontos.")
    if limite_caso_base < 3:
        raise ValueError("limite_caso_base deve ser pelo menos 3.")

    por_x = sorted(pontos, key=lambda p: (p.x, p.y))
    contador = {"comparacoes": 0}
    passos: List[PassoDivisao] = []

    d, a, b, _ = _resolver(por_x, limite_caso_base, 0, max_nivel_passos, contador, passos)

    return Resultado(
        ponto_a=a,
        ponto_b=b,
        distancia=d,
        comparacoes=contador["comparacoes"],
        passos=passos,
    )


def forca_bruta(pontos: List[Ponto]) -> Resultado:
    """Versao O(n^2): compara todos os pares. Serve de gabarito e de
    comparacao de tempo contra o dividir e conquistar."""
    if len(pontos) < 2:
        raise ValueError("Sao necessarios pelo menos 2 pontos.")
    contador = {"comparacoes": 0}
    d, a, b = _forca_bruta_trecho(pontos, contador)
    return Resultado(ponto_a=a, ponto_b=b, distancia=d, comparacoes=contador["comparacoes"])


@dataclass
class Duplicata:
    mantido: Ponto
    removido: Ponto
    distancia: float


def remover_duplicatas(
    pontos: List[Ponto],
    limiar: float,
    escolher_remocao: Optional[Callable[[Ponto, Ponto], Ponto]] = None,
    limite_remocoes: int = 2000,
    tempo_maximo_s: Optional[float] = None,
) -> Tuple[List[Ponto], List[Duplicata], bool]:
    """
    Tira da lista os pontos que sao duplicatas de outro (a menos de `limiar`),
    para que o par mais proximo do que sobrar seja de lugares DIFERENTES.

    Usa o proprio dividir e conquistar: acha o par mais proximo; se ele esta a
    menos de `limiar`, e uma duplicata -> tira um dos dois e repete. Para
    quando o par mais proximo ja esta alem do limiar (ou restam 2 pontos).

    escolher_remocao(a, b) devolve qual dos dois sai (padrao: o segundo).
    limite_remocoes e tempo_maximo_s evitam que uma lista enorme, cheia de
    duplicatas, demore demais; se algum deles for atingido com duplicatas
    ainda por tirar, o terceiro valor devolvido (truncada) e True.

    Devolve (pontos que sobraram, duplicatas removidas, truncada).
    """
    restantes = list(pontos)
    duplicatas: List[Duplicata] = []
    truncada = False
    inicio = time.perf_counter()

    while len(restantes) > 2:
        par = par_mais_proximo(restantes, max_nivel_passos=-1)
        if par.distancia >= limiar:
            break  # o que sobrou sao lugares diferentes

        estourou_tempo = (
            tempo_maximo_s is not None and time.perf_counter() - inicio >= tempo_maximo_s
        )
        if len(duplicatas) >= limite_remocoes or estourou_tempo:
            truncada = True
            break

        sai = escolher_remocao(par.ponto_a, par.ponto_b) if escolher_remocao else par.ponto_b
        fica = par.ponto_a if sai.id == par.ponto_b.id else par.ponto_b
        duplicatas.append(Duplicata(mantido=fica, removido=sai, distancia=par.distancia))
        restantes = [p for p in restantes if p.id != sai.id]

    return restantes, duplicatas, truncada