// Os nomes vem do OpenStreetMap (qualquer pessoa edita). No React eles so entram
// na pagina como texto ({p.nome} no JSX ja escapa), nunca como HTML.
export const rotulo = (p) => (p && p.nome) || "(sem nome)";

export const formatarDistancia = (metros) =>
  metros >= 1000 ? `${(metros / 1000).toFixed(2)} km` : `${metros.toFixed(1)} m`;

export const formatarMs = (ms) => (ms < 1 ? ms.toFixed(3) : ms.toFixed(2));

export const formatarNumero = (n) => n.toLocaleString("pt-BR");
