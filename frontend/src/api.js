import { API_URL } from "./config.js";

export const ERRO_API =
  "Não foi possível falar com a API. Ela está rodando? (python3 run.py)";

// tenta tirar a mensagem "detail" que a API manda no corpo do erro
async function textoDoErro(resposta) {
  try {
    const corpo = await resposta.json();
    if (corpo.detail) return String(corpo.detail);
  } catch {
    // resposta sem JSON: usa a mensagem generica
  }
  return `Erro ${resposta.status}.`;
}

export async function getCategorias() {
  let r;
  try {
    r = await fetch(`${API_URL}/categorias`);
  } catch {
    throw new Error(ERRO_API);
  }
  if (!r.ok) throw new Error(ERRO_API);
  return r.json();
}

export async function getLocais(categoria) {
  let r;
  try {
    r = await fetch(`${API_URL}/locais?categoria=${encodeURIComponent(categoria)}`);
  } catch {
    throw new Error(ERRO_API);
  }
  if (!r.ok) throw new Error(await textoDoErro(r));
  return r.json();
}

export async function postParMaisProximo(corpo) {
  let r;
  try {
    r = await fetch(`${API_URL}/par-mais-proximo`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corpo),
    });
  } catch {
    throw new Error(ERRO_API);
  }
  if (!r.ok) throw new Error(`Erro ${r.status} ao calcular.`);
  return r.json();
}

export async function getAleatorios(n) {
  let r;
  try {
    r = await fetch(`${API_URL}/pontos-aleatorios?n=${n}`);
  } catch {
    throw new Error(ERRO_API);
  }
  if (!r.ok) throw new Error(ERRO_API);
  return r.json();
}
