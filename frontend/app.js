const API_URL = "http://127.0.0.1:8000";

// caixa aproximada do Distrito Federal: [[sul, oeste], [norte, leste]]
const LIMITES_DF = [[-16.05, -48.29], [-15.50, -47.31]];

const LIMITE_PONTOS = 20000; // maximo aceito pela API
const LIMITE_SUSPEITA_M = 30; // abaixo disso, avisa que pode ser duplicata

// preferCanvas: desenha os pontos num canvas, bem mais leve com milhares de pontos
const mapa = L.map("mapa", { preferCanvas: true, doubleClickZoom: false });
mapa.fitBounds(LIMITES_DF);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "&copy; OpenStreetMap contributors",
}).addTo(mapa);

// ---------- estado ----------

let pontos = []; // [{lat, lon, nome, osm}] -- a ordem e a mesma enviada para a API
let pontosOriginais = []; // copia da lista carregada, usada por "Restaurar tudo"
let parAtual = null; // {a, b, distancia}: indices do par na lista `pontos`
let limitesDoPar = null;
let suspeitos = []; // pares ja removidos: [{a, b, distancia}]

const camadaPontos = L.layerGroup().addTo(mapa);
const camadaResultado = L.layerGroup().addTo(mapa);
const camadaDivisao = L.layerGroup().addTo(mapa);

const el = (id) => document.getElementById(id);
const elCategoria = el("categoria");
const elCarregar = el("carregar");
const elContador = el("contador");
const elStatus = el("status");
const elResultado = el("resultado");
const elNomeA = el("nomeA");
const elNomeB = el("nomeB");
const elDistancia = el("distancia");
const elDica = el("dica");
const elLegenda = el("legenda");
const elIgnorar = el("ignorarDuplicatas");
const elLimiar = el("limiar");
const elBlocoDuplicatas = el("blocoDuplicatas");
const elResumoDuplicatas = el("resumoDuplicatas");
const elListaDuplicatas = el("duplicatas");
const elMetricas = el("metricas");
const elQtd = el("qtd");
const elSuspeitos = el("suspeitos");
const elBlocoSuspeitos = el("blocoSuspeitos");
const btnZoom = el("zoomPar");
const btnRemover = el("remover");
const chkDivisao = el("mostrarDivisao");

// ---------- utilidades ----------

// Os nomes vem do OpenStreetMap (qualquer pessoa edita), entao so entram na
// pagina por textContent / createElement, nunca por innerHTML.
function rotulo(p) {
  return p.nome || "(sem nome)";
}

function formatarDistancia(metros) {
  return metros >= 1000 ? `${(metros / 1000).toFixed(2)} km` : `${metros.toFixed(1)} m`;
}

function formatarMs(ms) {
  return ms < 1 ? ms.toFixed(3) : ms.toFixed(2);
}

function formatarNumero(n) {
  return n.toLocaleString("pt-BR");
}

function atualizarContador() {
  const s = pontos.length === 1 ? "" : "s";
  elContador.textContent = `${formatarNumero(pontos.length)} ponto${s}`;
}

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

function desenharPonto(p) {
  L.circleMarker([p.lat, p.lon], {
    radius: 4, color: "#1d4ed8", weight: 1, fillColor: "#3b82f6", fillOpacity: 0.8,
  })
    .bindPopup(() => conteudoPopup(p)) // o popup so e montado quando alguem clica
    .addTo(camadaPontos);
}

function redesenharPontos() {
  camadaPontos.clearLayers();
  pontos.forEach((p) => desenharPonto(p));
}

function limparResultado() {
  camadaResultado.clearLayers();
  camadaDivisao.clearLayers();
  elResultado.hidden = true;
  elBlocoDuplicatas.hidden = true;
  elListaDuplicatas.replaceChildren();
  btnZoom.hidden = true;
  btnRemover.hidden = true;
  parAtual = null;
  limitesDoPar = null;
}

function renderSuspeitos() {
  elSuspeitos.replaceChildren();
  suspeitos.forEach((s) => {
    const item = document.createElement("li");
    item.textContent = `${s.a} ↔ ${s.b} (${formatarDistancia(s.distancia)})`;
    elSuspeitos.appendChild(item);
  });
  elBlocoSuspeitos.hidden = suspeitos.length === 0;
}

// troca a lista inteira de pontos (carregar categoria, aleatorios, limpar, restaurar)
function definirPontos(lista) {
  pontos = lista;
  pontosOriginais = lista.slice();
  suspeitos = [];
  redesenharPontos();
  limparResultado();
  renderSuspeitos();
  atualizarContador();
}

// ---------- carregar locais ----------
// Os locais vem da API, que le os dados do OpenStreetMap baixados antes
// (python3 baixar_dados.py). Assim a tela nao depende de o OpenStreetMap
// estar no ar na hora de usar.

// mostra "mensagem (12 s)" para a pessoa ver que nao travou; devolve a funcao que para o contador
function iniciarContador(mensagem) {
  const inicio = Date.now();
  const atualizar = () => {
    elStatus.textContent = `${mensagem} (${Math.round((Date.now() - inicio) / 1000)} s)`;
  };
  atualizar();
  const id = setInterval(atualizar, 1000);
  return () => clearInterval(id);
}

async function textoDoErro(resposta) {
  try {
    const corpo = await resposta.json();
    if (corpo.detail) return String(corpo.detail);
  } catch {
    // resposta sem JSON: usa a mensagem generica
  }
  return `Erro ${resposta.status}.`;
}

async function carregarCategorias() {
  try {
    const resposta = await fetch(`${API_URL}/categorias`);
    if (!resposta.ok) throw new Error();
    const categorias = await resposta.json();

    elCategoria.replaceChildren();
    categorias.forEach((c) => {
      const opcao = document.createElement("option");
      opcao.value = c.chave;
      opcao.textContent = c.disponivel ? c.rotulo : `${c.rotulo} (sem dados)`;
      opcao.disabled = !c.disponivel;
      elCategoria.appendChild(opcao);
    });

    const primeira = categorias.find((c) => c.disponivel);
    if (primeira) {
      elCategoria.value = primeira.chave;
    } else {
      elStatus.textContent = "Nenhuma categoria baixada ainda. Rode: python3 baixar_dados.py (dentro de backend/).";
    }
  } catch {
    elStatus.textContent = "Não foi possível falar com a API. Ela está rodando? (python3 run.py)";
  }
}

async function carregarCategoria() {
  elCarregar.disabled = true;
  const pararContagem = iniciarContador("Carregando");

  try {
    const resposta = await fetch(`${API_URL}/locais?categoria=${encodeURIComponent(elCategoria.value)}`);
    if (!resposta.ok) {
      elStatus.textContent = await textoDoErro(resposta);
      return;
    }

    const dados = await resposta.json();
    if (dados.locais.length < 2) {
      elStatus.textContent = "Foram encontrados menos de 2 locais nessa categoria.";
      return;
    }

    definirPontos(dados.locais);
    mapa.fitBounds(LIMITES_DF);

    let aviso = "";
    if (dados.total > dados.locais.length) {
      aviso = ` (usando só ${formatarNumero(dados.locais.length)} de ${formatarNumero(dados.total)})`;
    }
    elStatus.textContent = `${dados.rotulo}: ${formatarNumero(dados.locais.length)} locais carregados${aviso}.`;
  } catch {
    elStatus.textContent = "Não foi possível falar com a API. Ela está rodando? (python3 run.py)";
  } finally {
    pararContagem();
    elCarregar.disabled = false;
  }
}

elCarregar.addEventListener("click", carregarCategoria);

// ---------- calcular o par mais proximo ----------

function desenharDivisao(passo) {
  // a linha de corte e a faixa central cobrem a altura de todos os pontos
  const lats = pontos.map((p) => p.lat);
  const latMin = Math.min(...lats) - 0.02;
  const latMax = Math.max(...lats) + 0.02;

  L.rectangle(
    [[latMin, passo.lon_faixa_esquerda], [latMax, passo.lon_faixa_direita]],
    { color: "#f59e0b", weight: 1, fillOpacity: 0.15 }
  ).addTo(camadaDivisao);

  L.polyline(
    [[latMin, passo.lon_divisao], [latMax, passo.lon_divisao]],
    { color: "#f59e0b", weight: 2, dashArray: "6" }
  ).addTo(camadaDivisao);
}

// so numeros entram aqui, entao innerHTML e seguro
function htmlMetricas(dados) {
  const dc = dados.dividir_conquistar;
  let html = "";
  if (dados.limpeza) {
    const qtd = dados.limpeza.duplicatas.length;
    html += `<b>Limpeza de duplicatas:</b> ${formatarNumero(qtd)} removida${qtd === 1 ? "" : "s"} · ${formatarMs(dados.limpeza.tempo_ms)} ms<br/>`;
  }
  html += `<b>Dividir e conquistar:</b> ${formatarNumero(dc.comparacoes)} comparações · ${formatarMs(dc.tempo_ms)} ms<br/>`;

  if (dados.forca_bruta) {
    const fb = dados.forca_bruta;
    html += `<b>Força bruta:</b> ${formatarNumero(fb.comparacoes)} comparações · ${formatarMs(fb.tempo_ms)} ms<br/>`;
    html += dados.mesmo_resultado
      ? `<span class="ok">✓ os dois acharam a mesma distância</span>`
      : `<span>⚠ resultados diferentes</span>`;
  } else {
    html += `<i>Força bruta não executada (acima de 3.000 pontos).</i>`;
  }
  return html;
}

// lista as duplicatas que a API ignorou e marca cada uma no mapa (circulo cinza vazado)
function mostrarDuplicatas(limpeza, ignorar) {
  if (!ignorar || !limpeza) {
    elLegenda.textContent = "Par mais próximo (sem ignorar duplicatas)";
    return;
  }

  const qtd = limpeza.duplicatas.length;
  const s = qtd === 1 ? "" : "s";
  elLegenda.textContent = qtd === 0
    ? "Par mais próximo (nenhuma duplicata encontrada)"
    : `Par mais próximo de locais diferentes (${formatarNumero(qtd)} duplicata${s} ignorada${s})`;
  if (qtd === 0) return;

  limpeza.duplicatas.forEach((d) => {
    const mantido = pontos[d.indice_mantido];
    const removido = pontos[d.indice_removido];

    L.circleMarker([removido.lat, removido.lon], {
      radius: 7, color: "#6b7280", weight: 2, fill: false,
    })
      .bindPopup(() => conteudoPopup(removido))
      .addTo(camadaResultado);

    const item = document.createElement("li");
    item.textContent = `${rotulo(mantido)} ↔ ${rotulo(removido)} (${formatarDistancia(d.distancia_metros)})`;
    elListaDuplicatas.appendChild(item);
  });

  elResumoDuplicatas.textContent =
    `${formatarNumero(qtd)} duplicata${s} ignorada${s} (a menos de ${limpeza.limiar_m} m)` +
    (limpeza.truncada ? " — limite atingido, pode haver mais" : "");
  elBlocoDuplicatas.hidden = false;
}

async function calcular() {
  if (pontos.length < 2) {
    elStatus.textContent = "Carregue ou adicione pelo menos 2 pontos.";
    return;
  }

  limparResultado();
  const pararContagem = iniciarContador("Calculando");

  // so ignora duplicatas se a caixa estiver marcada e o limite for um numero valido
  const limiar = parseFloat(elLimiar.value);
  const ignorar = elIgnorar.checked && Number.isFinite(limiar) && limiar > 0;

  try {
    const resposta = await fetch(`${API_URL}/par-mais-proximo`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      // a API so precisa de lat/lon (e de saber se tem nome, para manter o cadastro
      // mais completo entre duplicatas); max_nivel_passos: 0 pede so a divisao principal
      body: JSON.stringify({
        pontos: pontos.map(({ lat, lon, nome }) => ({ lat, lon, tem_nome: Boolean(nome) })),
        ignorar_duplicatas_ate_m: ignorar ? limiar : null,
        max_nivel_passos: 0,
      }),
    });
    if (!resposta.ok) throw new Error(`Erro ${resposta.status} ao calcular.`);

    const dados = await resposta.json();
    // "indice" e a posicao do ponto na lista que enviamos
    const a = pontos[dados.ponto_a.indice];
    const b = pontos[dados.ponto_b.indice];
    parAtual = { a: dados.ponto_a.indice, b: dados.ponto_b.indice, distancia: dados.distancia_metros };

    L.polyline([[a.lat, a.lon], [b.lat, b.lon]], { color: "#dc2626", weight: 3 }).addTo(camadaResultado);
    [[a, "A"], [b, "B"]].forEach(([p, letra]) =>
      L.circleMarker([p.lat, p.lon], {
        radius: 8, color: "#dc2626", weight: 2, fillColor: "#ef4444", fillOpacity: 1,
      })
        .bindTooltip(letra, { permanent: true, direction: "top" })
        .bindPopup(() => conteudoPopup(p))
        .addTo(camadaResultado)
    );

    if (dados.passos.length > 0) desenharDivisao(dados.passos[0]);

    mostrarDuplicatas(dados.limpeza, ignorar);

    elNomeA.textContent = rotulo(a);
    elNomeB.textContent = rotulo(b);
    elDistancia.textContent = formatarDistancia(dados.distancia_metros);
    elDica.textContent =
      dados.distancia_metros < LIMITE_SUSPEITA_M
        ? "Muito perto: vale conferir se é o mesmo local cadastrado duas vezes."
        : "";
    elMetricas.innerHTML = htmlMetricas(dados);

    limitesDoPar = L.latLngBounds([[a.lat, a.lon], [b.lat, b.lon]]);
    elResultado.hidden = false;
    btnZoom.hidden = false;
    btnRemover.hidden = false;
    elStatus.textContent = "";
  } catch (erro) {
    limparResultado();
    elStatus.textContent = erro.message.startsWith("Erro")
      ? erro.message
      : "Não foi possível falar com a API. Ela está rodando? (python3 run.py)";
  } finally {
    pararContagem();
  }
}

el("calcular").addEventListener("click", calcular);

// ---------- remover duplicado e buscar o proximo par ----------

// se o novo par ficou fora da parte visivel do mapa, leva o mapa ate ele;
// se ja esta na tela, nao mexe (para nao tirar o zoom de quem esta olhando)
function acompanharPar() {
  if (limitesDoPar && !mapa.getBounds().contains(limitesDoPar)) {
    mapa.fitBounds(limitesDoPar, { maxZoom: 16, padding: [60, 60] });
  }
}

btnRemover.addEventListener("click", async () => {
  if (!parAtual) return;
  const { a, b, distancia } = parAtual;

  suspeitos.push({ a: rotulo(pontos[a]), b: rotulo(pontos[b]), distancia });
  pontos.splice(b, 1); // tira o ponto B; o A continua na lista

  renderSuspeitos();
  redesenharPontos();
  atualizarContador();

  if (pontos.length < 2) {
    limparResultado();
    elStatus.textContent = "Restam menos de 2 pontos.";
    return;
  }
  await calcular();
  acompanharPar();
});

el("restaurar").addEventListener("click", () => {
  definirPontos(pontosOriginais.slice());
  elStatus.textContent = "Lista restaurada.";
});

// ---------- outras opcoes ----------

mapa.on("click", (evento) => {
  const p = { lat: evento.latlng.lat, lon: evento.latlng.lng, nome: "Ponto manual", osm: null };
  pontos.push(p);
  pontosOriginais.push(p);
  desenharPonto(p);
  limparResultado(); // o resultado antigo nao vale mais com um ponto novo
  atualizarContador();
});

el("aleatorios").addEventListener("click", async () => {
  const n = parseInt(elQtd.value, 10);
  if (!Number.isInteger(n) || n < 2 || n > LIMITE_PONTOS) {
    elStatus.textContent = `Use uma quantidade entre 2 e ${formatarNumero(LIMITE_PONTOS)}.`;
    return;
  }

  try {
    const resposta = await fetch(`${API_URL}/pontos-aleatorios?n=${n}`);
    if (!resposta.ok) throw new Error();
    const lista = await resposta.json();
    definirPontos(lista.map((p) => ({ lat: p.lat, lon: p.lon, nome: null, osm: null })));
    mapa.fitBounds(LIMITES_DF);
    elStatus.textContent = `${formatarNumero(n)} pontos aleatórios gerados.`;
  } catch {
    elStatus.textContent = "Não foi possível falar com a API. Ela está rodando? (python3 run.py)";
  }
});

el("limpar").addEventListener("click", () => {
  definirPontos([]);
  elStatus.textContent = "";
});

chkDivisao.addEventListener("change", () => {
  if (chkDivisao.checked) mapa.addLayer(camadaDivisao);
  else mapa.removeLayer(camadaDivisao);
});

btnZoom.addEventListener("click", () => {
  if (limitesDoPar) mapa.fitBounds(limitesDoPar, { maxZoom: 16, padding: [60, 60] });
});

carregarCategorias();