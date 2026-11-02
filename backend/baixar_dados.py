import sys
import time

from locais import CATEGORIAS, ErroDownload, baixar_categoria, montar_consulta


def main(argumentos):
    pedidas = [a for a in argumentos if not a.startswith("--")]
    desconhecidas = [c for c in pedidas if c not in CATEGORIAS]
    if desconhecidas:
        print(f"Categoria desconhecida: {', '.join(desconhecidas)}")
        print(f"Disponiveis: {', '.join(CATEGORIAS)}")
        return 2
    chaves = pedidas or list(CATEGORIAS)

    if "--consulta" in argumentos:
        for chave in chaves:
            print(f"// {CATEGORIAS[chave]['rotulo']}")
            print(montar_consulta(CATEGORIAS[chave]["filtro"]))
            print()
        return 0

    resultados = {}
    for i, chave in enumerate(chaves, start=1):
        rotulo = CATEGORIAS[chave]["rotulo"]
        print(f"[{i}/{len(chaves)}] {rotulo}")
        try:
            total = baixar_categoria(chave)
            resultados[chave] = f"{total} locais"
            print(f"  ok: {total} locais salvos em data/{chave}.json\n")
        except ErroDownload as erro:
            resultados[chave] = f"FALHOU ({erro})"
            print(f"  ERRO: {erro}\n")
        if i < len(chaves):
            time.sleep(5)  # intervalo entre consultas: o servidor publico e compartilhado

    print("Resumo:")
    for chave, resultado in resultados.items():
        print(f"  {CATEGORIAS[chave]['rotulo']}: {resultado}")

    falhas = [c for c, r in resultados.items() if r.startswith("FALHOU")]
    if falhas:
        print("\nAlgumas categorias falharam. Tente de novo mais tarde (os servidores")
        print("publicos ficam mais livres de madrugada) so com essas: ")
        print(f"  python3 baixar_dados.py {' '.join(falhas)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))