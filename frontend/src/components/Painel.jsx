import { LIMITE_SUSPEITA_M } from "../config.js";
import { rotulo, formatarDistancia, formatarMs, formatarNumero } from "../format.js";

export default function Painel(props) {
  const {
    categorias,
    categoriaSel,
    onCategoriaChange,
    onCarregar,
    pontosLen,
    status,
    carregando,
    ignorarDup,
    onIgnorarChange,
    limiar,
    onLimiarChange,
    onCalcular,
    resultado,
    par,
    duplicatasResolvidas,
    onZoomPar,
    onRemoverB,
    suspeitos,
    onRestaurar,
    qtd,
    onQtdChange,
    onGerarAleatorios,
    mostrarDivisao,
    onToggleDivisao,
    onLimpar,
  } = props;

  const q = duplicatasResolvidas.length;

  let legenda;
  if (!resultado || !resultado.limpeza) {
    legenda = "Par mais próximo (sem ignorar duplicatas)";
  } else if (q === 0) {
    legenda = "Par mais próximo (nenhuma duplicata encontrada)";
  } else {
    legenda = `Par mais próximo de locais diferentes (${formatarNumero(q)} duplicata${q === 1 ? "" : "s"} ignorada${q === 1 ? "" : "s"})`;
  }

  return (
    <div id="painel">
      <h3>Pontos mais próximos no DF</h3>

      <p className="ajuda">
        Carregue locais reais do OpenStreetMap e descubra quais <b>dois locais diferentes</b> estão mais perto um do outro. O mesmo lugar cadastrado duas vezes (duplicata) é ignorado e listado à parte.
      </p>

      <div className="linha">
        <select value={categoriaSel} onChange={(e) => onCategoriaChange(e.target.value)}>
          {categorias.map((c) => (
            <option key={c.chave} value={c.chave} disabled={!c.disponivel}>
              {c.disponivel ? c.rotulo : c.rotulo + " (sem dados)"}
            </option>
          ))}
        </select>
        <button onClick={onCarregar} disabled={carregando}>
          Carregar
        </button>
      </div>

      <p id="contador">
        {`${formatarNumero(pontosLen)} ponto${pontosLen === 1 ? "" : "s"}`}
      </p>

      <p id="status">{status}</p>

      <label className="opcao">
        <input
          type="checkbox"
          checked={ignorarDup}
          onChange={(e) => onIgnorarChange(e.target.checked)}
        />
        Ignorar duplicatas (locais a menos de{" "}
        <input
          type="number"
          value={limiar}
          min="1"
          max="1000"
          onChange={(e) => onLimiarChange(e.target.value)}
        />
        {" "}m um do outro)
      </label>

      <button id="calcular" onClick={onCalcular} disabled={carregando}>
        Calcular par mais próximo
      </button>

      {resultado && par && (
        <div id="resultado">
          <p id="legenda">{legenda}</p>
          <p>
            <b>A:</b> {rotulo(par.a)}
          </p>
          <p>
            <b>B:</b> {rotulo(par.b)}
          </p>
          <p>
            <b>Distância:</b> {formatarDistancia(resultado.distancia_metros)}
          </p>
          <p id="dica">
            {resultado.distancia_metros < LIMITE_SUSPEITA_M
              ? "Muito perto: vale conferir se é o mesmo local cadastrado duas vezes."
              : ""}
          </p>
          <p id="metricas">
            {resultado.limpeza && (
              <span>
                <b>Limpeza de duplicatas:</b> {formatarNumero(q)}{" "}
                {q === 1 ? "removida" : "removidas"} · {formatarMs(resultado.limpeza.tempo_ms)} ms
                <br />
              </span>
            )}
            <span>
              <b>Dividir e conquistar:</b>{" "}
              {formatarNumero(resultado.dividir_conquistar.comparacoes)} comparações ·{" "}
              {formatarMs(resultado.dividir_conquistar.tempo_ms)} ms
              <br />
            </span>
            {resultado.forca_bruta ? (
              <span>
                <b>Força bruta:</b>{" "}
                {formatarNumero(resultado.forca_bruta.comparacoes)} comparações ·{" "}
                {formatarMs(resultado.forca_bruta.tempo_ms)} ms
                <br />
                {resultado.mesmo_resultado ? (
                  <span className="ok">✓ os dois acharam a mesma distância</span>
                ) : (
                  <span>⚠ resultados diferentes</span>
                )}
              </span>
            ) : (
              <i>Força bruta não executada (acima de 3.000 pontos).</i>
            )}
          </p>

          {resultado.limpeza && duplicatasResolvidas.length > 0 && (
            <details id="blocoDuplicatas">
              <summary>
                {`${formatarNumero(q)} duplicata(s) ignorada(s) (a menos de ${resultado.limpeza.limiar_m} m)`}
                {resultado.limpeza.truncada ? " — limite atingido, pode haver mais" : ""}
              </summary>
              <ul id="duplicatas">
                {duplicatasResolvidas.map((d, i) => (
                  <li key={i}>
                    {`${rotulo(d.mantido)} ↔ ${rotulo(d.removido)} (${formatarDistancia(d.distancia)})`}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}

      {par && (
        <div className="linha">
          <button onClick={onZoomPar}>Zoom no par</button>
          <button onClick={onRemoverB}>Tirar B da busca e ir ao próximo par</button>
        </div>
      )}

      {suspeitos.length > 0 && (
        <div>
          <h4>Locais tirados da busca</h4>
          <ol id="suspeitos">
            {suspeitos.map((s, i) => (
              <li key={i}>
                {`${s.a} ↔ ${s.b} (${formatarDistancia(s.distancia)})`}
              </li>
            ))}
          </ol>
          <button onClick={onRestaurar}>Restaurar tudo</button>
        </div>
      )}

      <details>
        <summary>Outras opções</summary>
        <p className="ajuda">Você também pode clicar no mapa para adicionar pontos.</p>
        <div className="linha">
          <input
            type="number"
            value={qtd}
            min="2"
            max="20000"
            onChange={(e) => onQtdChange(e.target.value)}
          />
          <button onClick={onGerarAleatorios}>Gerar aleatórios</button>
        </div>
        <label>
          <input
            type="checkbox"
            checked={mostrarDivisao}
            onChange={(e) => onToggleDivisao(e.target.checked)}
          />{" "}
          Mostrar divisão principal do algoritmo
        </label>
        <div className="linha">
          <button onClick={onLimpar}>Limpar tudo</button>
        </div>
      </details>
    </div>
  );
}
