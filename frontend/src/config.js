// Endereco da API. Da para trocar com VITE_API_URL no .env sem mexer no codigo.
export const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

// caixa aproximada do Distrito Federal: [[sul, oeste], [norte, leste]]
export const LIMITES_DF = [
  [-16.05, -48.29],
  [-15.5, -47.31],
];

export const LIMITE_PONTOS = 20000; // maximo aceito pela API
export const LIMITE_SUSPEITA_M = 30; // abaixo disso, avisa que pode ser duplicata
