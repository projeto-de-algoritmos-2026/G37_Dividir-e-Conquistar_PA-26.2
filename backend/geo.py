import math

RAIO_TERRA_M = 6371000.0


def projetar(lat: float, lon: float, lat_ref: float) -> tuple[float, float]:
    """Converte (lat, lon) em graus para (x, y) em metros."""
    x = math.radians(lon) * RAIO_TERRA_M * math.cos(math.radians(lat_ref))
    y = math.radians(lat) * RAIO_TERRA_M
    return x, y


def x_para_lon(x: float, lat_ref: float) -> float:
    """Operacao inversa de `projetar` para o eixo x: metros -> longitude."""
    return math.degrees(x / (RAIO_TERRA_M * math.cos(math.radians(lat_ref))))


def distancia_haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia em linha reta (metros) entre dois pontos, considerando a
    curvatura da Terra. Usada so para reportar a distancia final ao usuario."""
    lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * RAIO_TERRA_M * math.atan2(math.sqrt(a), math.sqrt(1 - a))