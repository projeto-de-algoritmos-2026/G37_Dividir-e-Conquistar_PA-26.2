import { useEffect, useRef, useState } from "react";
import MapaLeaflet from "./components/MapaLeaflet.jsx";
import Painel from "./components/Painel.jsx";
import { LIMITE_PONTOS } from "./config.js";
import { getCategorias, getLocais, postParMaisProximo, getAleatorios } from "./api.js";
import { rotulo, formatarNumero } from "./format.js";

export default function App() {
  // ---------- estado ----------
  const [categorias, setCategorias] = useState([]);
  const [categoriaSel, setCategoriaSel] = useState("");
  const [pontos, setPontos] = useState([]); // [{lat, lon, nome, osm}] na mesma ordem enviada a API
  const [pontosOriginais, setPontosOriginais] = useState([]); // copia para "Restaurar tudo"
  const [parAtual, setParAtual] = useState(null); // {a, b, distancia}: indices na lista `pontos`
  const [resultado, setResultado] = useState(null); // resposta crua da API (metricas, limpeza, passos)
  const [suspeitos, setSuspeitos] = useState([]); // pares ja removidos: [{a, b, distancia}] (nomes)
  const [status, setStatus] = useState("");
  const [carregando, setCarregando] = useState(false);

  const [ignorarDup, setIgnorarDup] = useState(true);
  const [limiar, setLimiar] = useState(30);
  const [mostrarDivisao, setMostrarDivisao] = useState(true);
  const [qtd, setQtd] = useState(200);

  const mapaRef = useRef(null);

  // ---------- carregar categorias no inicio ----------
  useEffect(() => {
    (async () => {
      try {
        const cats = await getCategorias();
        setCategorias(cats);
        const primeira = cats.find((c) => c.disponivel);
        if (primeira) setCategoriaSel(primeira.chave);
        else
          setStatus(
            "Nenhuma categoria baixada ainda. Rode: python3 baixar_dados.py (dentro de backend/)."
          );
      } catch (e) {
        setStatus(e.message);
      }
    })();
  }, []);

  // troca a lista inteira de pontos (carregar categoria, aleatorios, limpar, restaurar)
  function definirPontos(lista) {
    setPontos(lista);
    setPontosOriginais(lista.slice());
    setSuspeitos([]);
    setParAtual(null);
    setResultado(null);
    mapaRef.current?.fitDF();
  }

  // ---------- carregar locais de uma categoria ----------
  async function carregarCategoria() {
    if (!categoriaSel) return;
    setCarregando(true);
    setStatus("Carregando...");
    try {
      const dados = await getLocais(categoriaSel);
      if (dados.locais.length < 2) {
        setStatus("Foram encontrados menos de 2 locais nessa categoria.");
        return;
      }
      definirPontos(dados.locais);
      let aviso = "";
      if (dados.total > dados.locais.length) {
        aviso = ` (usando só ${formatarNumero(dados.locais.length)} de ${formatarNumero(
          dados.total
        )})`;
      }
      setStatus(
        `${dados.rotulo}: ${formatarNumero(dados.locais.length)} locais carregados${aviso}.`
      );
    } catch (e) {
      setStatus(e.message);
    } finally {
      setCarregando(false);
    }
  }

  // ---------- calcular o par mais proximo ----------
  // listaPontos permite recalcular com uma lista nova (usado ao remover o B)
  async function calcular(listaPontos = pontos) {
    if (listaPontos.length < 2) {
      setStatus("Carregue ou adicione pelo menos 2 pontos.");
      return null;
    }
    setCarregando(true);
    setStatus("Calculando...");

    const lim = Number(limiar);
    const ignorar = ignorarDup && Number.isFinite(lim) && lim > 0;

    try {
      // a API so precisa de lat/lon (e se tem nome, para manter o cadastro mais
      // completo entre duplicatas); max_nivel_passos: 0 pede so a divisao principal
      const dados = await postParMaisProximo({
        pontos: listaPontos.map(({ lat, lon, nome }) => ({
          lat,
          lon,
          tem_nome: Boolean(nome),
        })),
        ignorar_duplicatas_ate_m: ignorar ? lim : null,
        max_nivel_passos: 0,
      });
      setResultado(dados);
      setParAtual({
        a: dados.ponto_a.indice,
        b: dados.ponto_b.indice,
        distancia: dados.distancia_metros,
      });
      setStatus("");
      return dados;
    } catch (e) {
      setResultado(null);
      setParAtual(null);
      setStatus(e.message);
      return null;
    } finally {
      setCarregando(false);
    }
  }

  // ---------- tirar o B da busca e ir ao proximo par ----------
  async function removerBeProximo() {
    if (!parAtual) return;
    const { a, b, distancia } = parAtual;

    setSuspeitos((prev) => [
      ...prev,
      { a: rotulo(pontos[a]), b: rotulo(pontos[b]), distancia },
    ]);

    const novos = pontos.slice();
    novos.splice(b, 1); // tira o ponto B; o A continua na lista
    setPontos(novos);
    setResultado(null);
    setParAtual(null);

    if (novos.length < 2) {
      setStatus("Restam menos de 2 pontos.");
      return;
    }

    const dados = await calcular(novos);
    if (dados) {
      const na = novos[dados.ponto_a.indice];
      const nb = novos[dados.ponto_b.indice];
      // se o novo par ficou fora da area visivel, leva o mapa ate ele
      mapaRef.current?.acompanharPar([
        [na.lat, na.lon],
        [nb.lat, nb.lon],
      ]);
    }
  }

  function restaurar() {
    definirPontos(pontosOriginais.slice());
    setStatus("Lista restaurada.");
  }

  // ---------- outras opcoes ----------
  async function gerarAleatorios() {
    const n = parseInt(qtd, 10);
    if (!Number.isInteger(n) || n < 2 || n > LIMITE_PONTOS) {
      setStatus(`Use uma quantidade entre 2 e ${formatarNumero(LIMITE_PONTOS)}.`);
      return;
    }
    try {
      const lista = await getAleatorios(n);
      definirPontos(lista.map((p) => ({ lat: p.lat, lon: p.lon, nome: null, osm: null })));
      setStatus(`${formatarNumero(n)} pontos aleatórios gerados.`);
    } catch (e) {
      setStatus(e.message);
    }
  }

  function addPontoManual(latlng) {
    const p = { lat: latlng.lat, lon: latlng.lng, nome: "Ponto manual", osm: null };
    setPontos((prev) => [...prev, p]);
    setPontosOriginais((prev) => [...prev, p]);
    // o resultado antigo nao vale mais com um ponto novo
    setResultado(null);
    setParAtual(null);
  }

  function limpar() {
    definirPontos([]);
    setStatus("");
  }

  // ---------- derivados (sempre a partir da lista `pontos` atual) ----------
  const par = parAtual
    ? { a: pontos[parAtual.a], b: pontos[parAtual.b], distancia: parAtual.distancia }
    : null;

  const duplicatasResolvidas = resultado?.limpeza
    ? resultado.limpeza.duplicatas.map((d) => ({
        mantido: pontos[d.indice_mantido],
        removido: pontos[d.indice_removido],
        distancia: d.distancia_metros,
      }))
    : [];

  const passoDivisao = resultado?.passos?.[0] || null;

  function zoomNoPar() {
    if (par)
      mapaRef.current?.zoomNoPar([
        [par.a.lat, par.a.lon],
        [par.b.lat, par.b.lon],
      ]);
  }

  return (
    <>
      <MapaLeaflet
        ref={mapaRef}
        pontos={pontos}
        par={par}
        duplicatasRemovidas={duplicatasResolvidas.map((d) => d.removido)}
        passoDivisao={passoDivisao}
        mostrarDivisao={mostrarDivisao}
        onMapClick={addPontoManual}
      />
      <Painel
        categorias={categorias}
        categoriaSel={categoriaSel}
        onCategoriaChange={setCategoriaSel}
        onCarregar={carregarCategoria}
        pontosLen={pontos.length}
        status={status}
        carregando={carregando}
        ignorarDup={ignorarDup}
        onIgnorarChange={setIgnorarDup}
        limiar={limiar}
        onLimiarChange={setLimiar}
        onCalcular={() => calcular()}
        resultado={resultado}
        par={par}
        duplicatasResolvidas={duplicatasResolvidas}
        onZoomPar={zoomNoPar}
        onRemoverB={removerBeProximo}
        suspeitos={suspeitos}
        onRestaurar={restaurar}
        qtd={qtd}
        onQtdChange={setQtd}
        onGerarAleatorios={gerarAleatorios}
        mostrarDivisao={mostrarDivisao}
        onToggleDivisao={setMostrarDivisao}
        onLimpar={limpar}
      />
    </>
  );
}
