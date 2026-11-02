import random
import time
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from closest_pair import Ponto, forca_bruta, par_mais_proximo, remover_duplicatas
from geo import distancia_haversine, projetar, x_para_lon
from locais import CATEGORIAS, carregar_locais, listar_categorias

app = FastAPI(title="Par de Pontos Mais Proximo - Dividir e Conquistar")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# caixa aproximada do Distrito Federal
DF_LAT_MIN, DF_LAT_MAX = -16.05, -15.50
DF_LON_MIN, DF_LON_MAX = -48.29, -47.31

# a forca bruta e O(n^2); acima disso ela demora demais para ser comparada
LIMITE_FORCA_BRUTA = 3000
LIMITE_PONTOS = 20000

# a limpeza de duplicatas repete o algoritmo varias vezes; este e o tempo maximo dela
TEMPO_MAXIMO_LIMPEZA_S = 10


# ---------- modelos ----------


class PontoEntrada(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class PontoPedido(PontoEntrada):
    # so serve para decidir qual duplicata manter: fica a que tem nome
    tem_nome: bool = False


class PedidoPar(BaseModel):
    pontos: List[PontoPedido] = Field(min_length=2, max_length=LIMITE_PONTOS)
    # se informado, antes de achar o par tira as duplicatas (locais a menos de
    # tantos metros de outro), para o resultado ser de lugares diferentes
    ignorar_duplicatas_ate_m: Optional[float] = Field(default=None, ge=0, le=1000)
    comparar_forca_bruta: bool = True
    limite_caso_base: int = Field(default=3, ge=3, le=50)
    max_nivel_passos: int = Field(default=4, ge=0, le=10)


class PontoSaida(BaseModel):
    indice: int  # posicao do ponto na lista enviada
    lat: float
    lon: float


class PassoSaida(BaseModel):
    nivel: int
    n_pontos: int
    lon_divisao: float  # linha vertical de corte
    lon_faixa_esquerda: float  # limites da faixa central (delta de cada lado)
    lon_faixa_direita: float
    delta_lados_m: float
    delta_final_m: float
    pontos_na_faixa: int
    comparacoes_faixa: int
    max_vizinhos_por_ponto: int


class Metricas(BaseModel):
    tempo_ms: float
    comparacoes: int


class DuplicataSaida(BaseModel):
    indice_mantido: int
    indice_removido: int
    distancia_metros: float


class Limpeza(BaseModel):
    limiar_m: float
    duplicatas: List[DuplicataSaida]
    tempo_ms: float
    truncada: bool  # True se parou no limite de tempo/quantidade com duplicatas sobrando


class RespostaPar(BaseModel):
    ponto_a: PontoSaida
    ponto_b: PontoSaida
    distancia_metros: float
    dividir_conquistar: Metricas
    forca_bruta: Optional[Metricas] = None  # None se desligado ou n grande demais
    mesmo_resultado: Optional[bool] = None
    limpeza: Optional[Limpeza] = None  # None se nao pediu para ignorar duplicatas
    passos: List[PassoSaida]


class CategoriaSaida(BaseModel):
    chave: str
    rotulo: str
    disponivel: bool  # False se os dados ainda nao foram baixados


class LocalSaida(BaseModel):
    lat: float
    lon: float
    nome: Optional[str] = None
    osm: Optional[str] = None  # ex.: "node/123", para montar o link do OpenStreetMap


class RespostaLocais(BaseModel):
    rotulo: str
    total: int  # quantos locais existem no arquivo
    locais: List[LocalSaida]  # no maximo LIMITE_PONTOS


class LinhaBenchmark(BaseModel):
    n: int
    dividir_conquistar: Metricas
    forca_bruta: Optional[Metricas] = None


# ---------- funcoes auxiliares ----------


def _projetar_pontos(pontos: List[PontoEntrada]):
    """Converte lat/lon para o plano em metros. Devolve (pontos, lat_ref)."""
    lat_ref = sum(p.lat for p in pontos) / len(pontos)
    convertidos = []
    for i, p in enumerate(pontos):
        x, y = projetar(p.lat, p.lon, lat_ref)
        convertidos.append(Ponto(id=i, x=x, y=y))
    return convertidos, lat_ref


def _gerar_aleatorios(n: int, seed: Optional[int]) -> List[PontoEntrada]:
    rng = random.Random(seed)
    return [
        PontoEntrada(
            lat=rng.uniform(DF_LAT_MIN, DF_LAT_MAX),
            lon=rng.uniform(DF_LON_MIN, DF_LON_MAX),
        )
        for _ in range(n)
    ]


def _cronometrar(funcao, *args, **kwargs):
    inicio = time.perf_counter()
    resultado = funcao(*args, **kwargs)
    return resultado, (time.perf_counter() - inicio) * 1000


# ---------- endpoints ----------


@app.post("/par-mais-proximo", response_model=RespostaPar)
def rota_par_mais_proximo(pedido: PedidoPar):
    pontos, lat_ref = _projetar_pontos(pedido.pontos)

    # 1. (opcional) tira as duplicatas, para o par achado ser de locais diferentes
    limpeza = None
    if pedido.ignorar_duplicatas_ate_m:
        def quem_sai(a: Ponto, b: Ponto) -> Ponto:
            # entre dois cadastros do mesmo lugar, tira o que nao tem nome
            if not pedido.pontos[a.id].tem_nome and pedido.pontos[b.id].tem_nome:
                return a
            return b

        (pontos, removidas, truncada), tempo_limpeza = _cronometrar(
            remover_duplicatas,
            pontos,
            pedido.ignorar_duplicatas_ate_m,
            quem_sai,
            tempo_maximo_s=TEMPO_MAXIMO_LIMPEZA_S,
        )
        limpeza = Limpeza(
            limiar_m=pedido.ignorar_duplicatas_ate_m,
            duplicatas=[
                DuplicataSaida(
                    indice_mantido=d.mantido.id,
                    indice_removido=d.removido.id,
                    distancia_metros=distancia_haversine(
                        pedido.pontos[d.mantido.id].lat, pedido.pontos[d.mantido.id].lon,
                        pedido.pontos[d.removido.id].lat, pedido.pontos[d.removido.id].lon,
                    ),
                )
                for d in removidas
            ],
            tempo_ms=tempo_limpeza,
            truncada=truncada,
        )

    # 2. acha o par mais proximo do que sobrou (os "indices" continuam sendo os
    #    da lista enviada, porque cada Ponto guarda sua posicao original)
    resultado, tempo_dc = _cronometrar(
        par_mais_proximo,
        pontos,
        limite_caso_base=pedido.limite_caso_base,
        max_nivel_passos=pedido.max_nivel_passos,
    )

    metricas_fb = None
    mesmo = None
    if pedido.comparar_forca_bruta and len(pontos) <= LIMITE_FORCA_BRUTA:
        bruta, tempo_fb = _cronometrar(forca_bruta, pontos)
        metricas_fb = Metricas(tempo_ms=tempo_fb, comparacoes=bruta.comparacoes)
        # compara a distancia (pode haver varios pares empatados)
        mesmo = abs(bruta.distancia - resultado.distancia) < 1e-6

    original_a = pedido.pontos[resultado.ponto_a.id]
    original_b = pedido.pontos[resultado.ponto_b.id]

    passos = []
    for p in resultado.passos:
        passos.append(
            PassoSaida(
                nivel=p.nivel,
                n_pontos=p.n_pontos,
                lon_divisao=x_para_lon(p.x_divisao, lat_ref),
                lon_faixa_esquerda=x_para_lon(p.x_divisao - p.delta_lados, lat_ref),
                lon_faixa_direita=x_para_lon(p.x_divisao + p.delta_lados, lat_ref),
                delta_lados_m=p.delta_lados,
                delta_final_m=p.delta_final,
                pontos_na_faixa=p.pontos_na_faixa,
                comparacoes_faixa=p.comparacoes_faixa,
                max_vizinhos_por_ponto=p.max_vizinhos_por_ponto,
            )
        )

    return RespostaPar(
        ponto_a=PontoSaida(indice=resultado.ponto_a.id, lat=original_a.lat, lon=original_a.lon),
        ponto_b=PontoSaida(indice=resultado.ponto_b.id, lat=original_b.lat, lon=original_b.lon),
        distancia_metros=distancia_haversine(
            original_a.lat, original_a.lon, original_b.lat, original_b.lon
        ),
        dividir_conquistar=Metricas(tempo_ms=tempo_dc, comparacoes=resultado.comparacoes),
        forca_bruta=metricas_fb,
        mesmo_resultado=mesmo,
        limpeza=limpeza,
        passos=passos,
    )


@app.get("/pontos-aleatorios", response_model=List[PontoEntrada])
def rota_pontos_aleatorios(
    n: int = Query(100, ge=2, le=LIMITE_PONTOS),
    seed: Optional[int] = None,
):
    return _gerar_aleatorios(n, seed)


@app.get("/categorias", response_model=List[CategoriaSaida])
def rota_categorias():
    return listar_categorias()


@app.get("/locais", response_model=RespostaLocais)
def rota_locais(categoria: str = Query(...)):
    if categoria not in CATEGORIAS:
        raise HTTPException(status_code=404, detail=f"Categoria desconhecida: {categoria}.")
    try:
        todos = carregar_locais(categoria)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Os dados dessa categoria ainda nao foram baixados. "
            "Rode: python3 baixar_dados.py (dentro da pasta backend).",
        )
    return RespostaLocais(
        rotulo=CATEGORIAS[categoria]["rotulo"],
        total=len(todos),
        locais=todos[:LIMITE_PONTOS],
    )


@app.get("/benchmark", response_model=List[LinhaBenchmark])
def rota_benchmark(tamanhos: str = Query("100,500,1000,2000,3000")):
    try:
        lista = [int(t) for t in tamanhos.split(",")]
    except ValueError:
        raise HTTPException(status_code=400, detail="tamanhos deve ser numeros separados por virgula.")

    if not 1 <= len(lista) <= 10 or any(n < 2 or n > LIMITE_PONTOS for n in lista):
        raise HTTPException(
            status_code=400,
            detail=f"Use de 1 a 10 tamanhos, cada um entre 2 e {LIMITE_PONTOS}.",
        )

    linhas = []
    for n in lista:
        pontos, _ = _projetar_pontos(_gerar_aleatorios(n, seed=n))
        dc, tempo_dc = _cronometrar(par_mais_proximo, pontos, max_nivel_passos=-1)
        fb_metricas = None
        if n <= LIMITE_FORCA_BRUTA:
            fb, tempo_fb = _cronometrar(forca_bruta, pontos)
            fb_metricas = Metricas(tempo_ms=tempo_fb, comparacoes=fb.comparacoes)
        linhas.append(
            LinhaBenchmark(
                n=n,
                dividir_conquistar=Metricas(tempo_ms=tempo_dc, comparacoes=dc.comparacoes),
                forca_bruta=fb_metricas,
            )
        )
    return linhas


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)