import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import L from "leaflet";
import { LIMITES_DF } from "../config.js";
import { rotulo } from "../format.js";

// Popup montado so com DOM (createElement / textContent): os nomes vem do
// OpenStreetMap (qualquer pessoa edita), entao nunca entram como HTML.
function conteudoPopup(p) {
  const div = document.createElement("div");
  const nome = document.createElement("b");
  nome.textContent = rotulo(p);
  div.appendChild(nome);

  if (p.osm) {
    div.appendChild(document.createElement("br"));
    const link = document.createElement("a");
    link.href = `https://www.openstreetmap.org/${p.osm}`;
    link.target = "_blank";
    link.rel = "noopener";
    link.textContent = "Ver no OpenStreetMap";
    div.appendChild(link);
  }
  return div;
}

const MapaLeaflet = forwardRef(function MapaLeaflet(
  { pontos, par, duplicatasRemovidas, passoDivisao, mostrarDivisao, onMapClick },
  ref
) {
  const mapaRef = useRef(null);
  const camadaPontosRef = useRef(null);
  const camadaResultadoRef = useRef(null);
  const camadaDivisaoRef = useRef(null);
  // guarda o callback mais recente sem recriar o mapa
  const onMapClickRef = useRef(onMapClick);
  onMapClickRef.current = onMapClick;

  // cria o mapa UMA vez
  useEffect(() => {
    // preferCanvas: desenha os pontos num canvas, bem mais leve com milhares de pontos
    const mapa = L.map("mapa", { preferCanvas: true, doubleClickZoom: false });
    mapa.fitBounds(LIMITES_DF);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(mapa);

    camadaPontosRef.current = L.layerGroup().addTo(mapa);
    camadaResultadoRef.current = L.layerGroup().addTo(mapa);
    camadaDivisaoRef.current = L.layerGroup().addTo(mapa);

    mapa.on("click", (evento) => {
      onMapClickRef.current?.({ lat: evento.latlng.lat, lng: evento.latlng.lng });
    });

    mapaRef.current = mapa;
    return () => {
      mapa.remove();
      mapaRef.current = null;
    };
  }, []);

  // acoes de camera pedidas pelo App (via ref)
  useImperativeHandle(ref, () => ({
    fitDF() {
      mapaRef.current?.fitBounds(LIMITES_DF);
    },
    zoomNoPar(bounds) {
      mapaRef.current?.fitBounds(L.latLngBounds(bounds), { maxZoom: 16, padding: [60, 60] });
    },
    // se o par esta fora da parte visivel, leva o mapa ate ele; se ja aparece, nao mexe
    acompanharPar(bounds) {
      const mapa = mapaRef.current;
      if (!mapa) return;
      const alvo = L.latLngBounds(bounds);
      if (!mapa.getBounds().contains(alvo)) {
        mapa.fitBounds(alvo, { maxZoom: 16, padding: [60, 60] });
      }
    },
  }));

  // redesenha os pontos azuis quando a lista muda
  useEffect(() => {
    const camada = camadaPontosRef.current;
    if (!camada) return;
    camada.clearLayers();
    pontos.forEach((p) => {
      L.circleMarker([p.lat, p.lon], {
        radius: 4, color: "#1d4ed8", weight: 1, fillColor: "#3b82f6", fillOpacity: 0.8,
      })
        .bindPopup(() => conteudoPopup(p)) // o popup so e montado quando alguem clica
        .addTo(camada);
    });
  }, [pontos]);

  // redesenha o resultado: par em vermelho (A/B) + duplicatas ignoradas (circulo cinza)
  useEffect(() => {
    const camada = camadaResultadoRef.current;
    if (!camada) return;
    camada.clearLayers();

    if (par && par.a && par.b) {
      const { a, b } = par;
      L.polyline([[a.lat, a.lon], [b.lat, b.lon]], { color: "#dc2626", weight: 3 }).addTo(camada);
      [[a, "A"], [b, "B"]].forEach(([p, letra]) =>
        L.circleMarker([p.lat, p.lon], {
          radius: 8, color: "#dc2626", weight: 2, fillColor: "#ef4444", fillOpacity: 1,
        })
          .bindTooltip(letra, { permanent: true, direction: "top" })
          .bindPopup(() => conteudoPopup(p))
          .addTo(camada)
      );
    }

    (duplicatasRemovidas || []).forEach((removido) => {
      if (!removido) return;
      L.circleMarker([removido.lat, removido.lon], {
        radius: 7, color: "#6b7280", weight: 2, fill: false,
      })
        .bindPopup(() => conteudoPopup(removido))
        .addTo(camada);
    });
  }, [par, duplicatasRemovidas]);

  // redesenha a divisao principal (linha de corte + faixa central) e liga/desliga a camada
  useEffect(() => {
    const camada = camadaDivisaoRef.current;
    const mapa = mapaRef.current;
    if (!camada || !mapa) return;
    camada.clearLayers();

    if (mostrarDivisao && passoDivisao && pontos.length > 0) {
      // a linha e a faixa cobrem a altura de todos os pontos
      const lats = pontos.map((p) => p.lat);
      const latMin = Math.min(...lats) - 0.02;
      const latMax = Math.max(...lats) + 0.02;

      L.rectangle(
        [[latMin, passoDivisao.lon_faixa_esquerda], [latMax, passoDivisao.lon_faixa_direita]],
        { color: "#f59e0b", weight: 1, fillOpacity: 0.15 }
      ).addTo(camada);

      L.polyline(
        [[latMin, passoDivisao.lon_divisao], [latMax, passoDivisao.lon_divisao]],
        { color: "#f59e0b", weight: 2, dashArray: "6" }
      ).addTo(camada);
    }

    if (mostrarDivisao) {
      if (!mapa.hasLayer(camada)) mapa.addLayer(camada);
    } else if (mapa.hasLayer(camada)) {
      mapa.removeLayer(camada);
    }
  }, [passoDivisao, mostrarDivisao, pontos]);

  return <div id="mapa" />;
});

export default MapaLeaflet;
