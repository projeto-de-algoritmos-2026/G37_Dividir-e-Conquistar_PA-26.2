import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional

PASTA_DADOS = Path(__file__).parent / "data"

# categorias disponiveis: chave -> rotulo e filtro de tags do OpenStreetMap
CATEGORIAS: Dict[str, Dict[str, str]] = {
    "farmacia": {"rotulo": "Farmácias", "filtro": '["amenity"="pharmacy"]'},
    "hospital": {"rotulo": "Hospitais", "filtro": '["amenity"="hospital"]'},
    "escola": {"rotulo": "Escolas", "filtro": '["amenity"="school"]'},
    "supermercado": {"rotulo": "Supermercados", "filtro": '["shop"="supermarket"]'},
    "posto": {"rotulo": "Postos de combustível", "filtro": '["amenity"="fuel"]'},
    "parada": {"rotulo": "Paradas de ônibus", "filtro": '["highway"="bus_stop"]'},
}

# overpass.private.coffee era conhecido como overpass.kumi.systems
SERVIDORES = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

# a politica de uso do Overpass pede que o app se identifique
USER_AGENT = "par-pontos-df/1.0 (trabalho academico de Projeto de Algoritmos - UnB)"

# caixa aproximada do DF (sul, oeste, norte, leste), usada se a area nao for achada
DF_SUL, DF_OESTE, DF_NORTE, DF_LESTE = -16.05, -48.29, -15.50, -47.31


class ErroDownload(Exception):
    """Nao foi possivel baixar os dados do OpenStreetMap."""


# ---------- consulta ----------


def montar_consulta(filtro: str, usar_area: bool = True, timeout_s: int = 120) -> str:
    """Monta a consulta Overpass QL. Com usar_area, busca dentro da area
    administrativa "Distrito Federal"; senao, dentro da caixa aproximada."""
    if usar_area:
        escopo = (
            'area["boundary"="administrative"]["admin_level"="4"]'
            '["name"="Distrito Federal"]->.df;'
        )
        alvo = "(area.df)"
    else:
        escopo = ""
        alvo = f"({DF_SUL},{DF_OESTE},{DF_NORTE},{DF_LESTE})"
    # "out center" transforma predios/areas em um ponto central; "qt" pula a ordenacao
    return f"[out:json][timeout:{timeout_s}];{escopo}nwr{filtro}{alvo};out center qt;"


def elementos_para_locais(elementos: List[dict]) -> List[dict]:
    """Converte os elementos do Overpass em {lat, lon, nome, osm}.
    Pontos usam lat/lon; predios e areas usam o campo `center`. Elementos
    sem posicao sao ignorados."""
    locais = []
    for e in elementos:
        centro = e.get("center") or {}
        lat = e.get("lat", centro.get("lat"))
        lon = e.get("lon", centro.get("lon"))
        if lat is None or lon is None:
            continue
        tags = e.get("tags") or {}
        locais.append(
            {"lat": lat, "lon": lon, "nome": tags.get("name"), "osm": f"{e.get('type')}/{e.get('id')}"}
        )
    return locais


# ---------- leitura (usada pela API) ----------


def caminho_arquivo(chave: str) -> Path:
    return PASTA_DADOS / f"{chave}.json"


def listar_categorias() -> List[dict]:
    """Todas as categorias, indicando quais ja tem dados baixados."""
    return [
        {"chave": chave, "rotulo": c["rotulo"], "disponivel": caminho_arquivo(chave).exists()}
        for chave, c in CATEGORIAS.items()
    ]


def carregar_locais(chave: str) -> List[dict]:
    """Le os locais ja baixados de uma categoria.

    KeyError: categoria desconhecida. FileNotFoundError: ainda nao baixada."""
    if chave not in CATEGORIAS:
        raise KeyError(chave)
    caminho = caminho_arquivo(chave)
    if not caminho.exists():
        raise FileNotFoundError(caminho)
    bruto = json.loads(caminho.read_text(encoding="utf-8"))
    return elementos_para_locais(bruto.get("elements", []))


# ---------- download (usado por baixar_dados.py) ----------


def consultar_overpass(
    consulta: str,
    servidores: Optional[List[str]] = None,
    tentativas_por_servidor: int = 2,
    timeout_http_s: int = 180,
    espera_base_s: int = 10,
    log: Callable[[str], None] = print,
) -> dict:
    """Envia a consulta, tentando cada servidor algumas vezes, com espera
    crescente entre as tentativas. Levanta ErroDownload se nada funcionar."""
    servidores = servidores or SERVIDORES
    corpo = urllib.parse.urlencode({"data": consulta}).encode("utf-8")
    ultimo_erro = "sem resposta"

    for url in servidores:
        for tentativa in range(1, tentativas_por_servidor + 1):
            log(f"  {url} (tentativa {tentativa}/{tentativas_por_servidor})...")
            try:
                pedido = urllib.request.Request(
                    url,
                    data=corpo,
                    headers={
                        "User-Agent": USER_AGENT,
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                )
                with urllib.request.urlopen(pedido, timeout=timeout_http_s) as resposta:
                    dados = json.loads(resposta.read().decode("utf-8"))

                # o Overpass responde HTTP 200 mesmo quando a consulta estoura o
                # tempo ou a memoria: o aviso vem no campo "remark"
                remark = dados.get("remark", "")
                if "runtime error" in remark:
                    raise ErroDownload(f"o servidor nao terminou a consulta ({remark[:120]})")
                return dados

            except urllib.error.HTTPError as erro:
                ultimo_erro = f"HTTP {erro.code}"
                if erro.code == 400:
                    # consulta invalida: repetir nao adianta
                    raise ErroDownload("o servidor recusou a consulta (HTTP 400)") from erro
            except ErroDownload as erro:
                ultimo_erro = str(erro)
            except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as erro:
                ultimo_erro = f"{type(erro).__name__}: {erro}"

            log(f"    falhou: {ultimo_erro}")
            if tentativa < tentativas_por_servidor:
                espera = espera_base_s * tentativa
                log(f"    aguardando {espera} s para tentar de novo...")
                time.sleep(espera)

    raise ErroDownload(f"nenhum servidor respondeu (ultimo erro: {ultimo_erro})")


def baixar_categoria(chave: str, log: Callable[[str], None] = print, **opcoes) -> int:
    """Baixa uma categoria e salva em data/<chave>.json. Devolve quantos locais.
    So grava o arquivo se o download deu certo (nunca deixa arquivo pela metade)."""
    filtro = CATEGORIAS[chave]["filtro"]

    dados: dict = {}
    for usar_area in (True, False):
        dados = consultar_overpass(montar_consulta(filtro, usar_area), log=log, **opcoes)
        if dados.get("elements"):
            break
        log("  area do DF sem resultados; tentando pela caixa aproximada do DF...")

    total = len(elementos_para_locais(dados.get("elements", [])))
    if total < 2:
        raise ErroDownload(f"foram encontrados menos de 2 locais ({total})")

    dados["baixado_em"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    PASTA_DADOS.mkdir(exist_ok=True)
    destino = caminho_arquivo(chave)
    temporario = destino.with_suffix(".tmp")
    temporario.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    temporario.replace(destino)
    return total