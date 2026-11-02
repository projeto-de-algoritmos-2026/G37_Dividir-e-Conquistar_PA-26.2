# Par de Pontos Mais Próximos — Distrito Federal

Conteúdo da Disciplina: Dividir e Conquistar — Par de Pontos Mais Próximos<br>

## Alunos

| Matrícula | Aluno                       |
| --------- | --------------------------- |
| 222006276 | Luís Gustavo Lopes Oliveira |
| 222006211 | Vitor Valerio Hoffmann      |

## Sobre

Aplicação web que encontra o **par de pontos mais próximos** entre locais
reais do Distrito Federal, usando o algoritmo de **dividir e conquistar**.

**Para que serve.** O usuário escolhe uma categoria (farmácias, hospitais,
escolas, supermercados, postos de combustível ou paradas de ônibus) e o app
carrega do OpenStreetMap todos os locais dela no DF. A pergunta que o app
responde é: **quais são os dois locais diferentes mais próximos um do outro?**
(por exemplo, os dois hospitais ou os dois supermercados mais colados).

Há um detalhe nos dados: o par mais próximo costuma ser **o mesmo lugar
cadastrado duas vezes** (um ponto e o contorno do prédio, os dois marcados
como hospital), a poucos metros. Por isso o app, por padrão, **ignora
duplicatas**: enquanto o par mais próximo estiver a menos de 30 m (limite
editável), ele tira um dos dois e procura de novo, usando o próprio dividir e
conquistar. O que sobra é o par de locais diferentes, e as duplicatas ignoradas
viram um relatório à parte, útil para corrigir o mapa. Em um conjunto com
milhares de locais, comparar todos os pares seria lento; o dividir e conquistar
resolve em O(n log n).

**O problema.** Dados `n` pontos, achar os dois mais próximos entre si. A
solução ingênua compara todos os pares: **O(n²)**. O dividir e conquistar
resolve em **O(n log n)**:

1. **Dividir:** ordena os pontos por `x` e corta no meio com uma linha vertical.
2. **Conquistar:** resolve recursivamente a metade esquerda e a direita. Seja
   `delta` o menor entre as duas respostas.
3. **Combinar:** o par mais próximo pode ter um ponto em cada metade. Mas só
   interessam pontos a menos de `delta` da linha de corte (a **faixa central**).
   Dentro da faixa, ordenados por `y`, cada ponto só precisa ser comparado
   com **no máximo os 7 seguintes** — esse limite é o que mantém a etapa de
   combinação linear.

```
T(n) = 2·T(n/2) + O(n)   ->   O(n log n)
```

Para a combinação continuar linear, os pontos voltam de cada chamada recursiva
já ordenados por `y`, intercalados por um *merge* (o mesmo passo do merge sort),
sem precisar reordenar a faixa a cada nível.

**Como o mapa vira um plano.** O algoritmo trabalha em um plano `(x, y)`, mas o
mapa usa latitude e longitude. Na escala do DF, uma projeção equiretangular
simples converte tudo para metros com boa precisão:

```
x = lon · R · cos(lat_referência)
y = lat · R
```

Com isso, a linha de corte vertical do algoritmo vira uma linha de **longitude
constante** no mapa, fácil de desenhar no Leaflet. A distância final reportada
ao usuário usa a fórmula de haversine.

## Screenshots

> Screenshots do mapa serão adicionados aqui.

## Instalação

Linguagem: Python 3.9+<br>
Framework: FastAPI (backend) e Leaflet (frontend, HTML + JavaScript puro, sem build)<br>

**Pré-requisitos:** Python 3.9 ou superior.

```bash
# 1. ambiente virtual (evita o erro externally-managed-environment)
python3 -m venv venv
source venv/bin/activate      # no Windows: venv\Scripts\activate

# 2. dependências do backend
pip install -r backend/requirements.txt

# 3. baixa os locais do OpenStreetMap (uma vez só; veja "Os dados" abaixo)
cd backend && python3 baixar_dados.py && cd ..

# 4. sobe backend e frontend juntos (Ctrl+C para parar os dois)
python3 run.py
```

Abra **[http://127.0.0.1:5500](http://127.0.0.1:5500)**. A API fica em
`http://127.0.0.1:8000`, com documentação interativa em **`/docs`** — dá para
testar todos os endpoints por lá, sem precisar do mapa.

### Os dados

Os locais (farmácias, hospitais, escolas, supermercados, postos de combustível
e paradas de ônibus do DF) vêm do OpenStreetMap, mas **não são consultados ao
vivo**: o `baixar_dados.py` baixa cada categoria uma vez e salva em
`backend/data/<categoria>.json`, e a API lê desses arquivos. O motivo é que os
servidores públicos do OpenStreetMap (Overpass API) são compartilhados e
costumam ficar sobrecarregados, então uma consulta ao vivo pode demorar minutos
ou falhar justo na hora da apresentação.

```bash
cd backend
python3 baixar_dados.py                    # todas as categorias
python3 baixar_dados.py farmacia escola    # só algumas
```

O script tenta dois servidores, repete com espera crescente e mostra o motivo
de cada falha. Se alguma categoria falhar, rode de novo só com ela mais tarde
(de madrugada os servidores ficam mais livres). **Faça commit dos arquivos de
`backend/data/`**: assim o projeto funciona sem internet. Os dados baixados
também servem como "foto" do OpenStreetMap em uma data, o que deixa os
resultados do relatório reproduzíveis.

Se o script não conseguir baixar uma categoria, uma alternativa é abrir o
[overpass-turbo.eu](https://overpass-turbo.eu), colar a consulta que o
`python3 baixar_dados.py --consulta farmacia` imprime, executar e exportar o
resultado bruto em JSON para `backend/data/farmacia.json` (o formato é o mesmo
da resposta do Overpass).

## Uso

1. **Escolha uma categoria** e clique em **Carregar**. Os locais dela aparecem
   no mapa (`GET /locais`). Categorias cujos dados ainda não foram baixados
   aparecem como *(sem dados)* na lista.
2. **Clique em Calcular par mais próximo** (`POST /par-mais-proximo`). Com
   *Ignorar duplicatas* marcado (padrão, 30 m), o par que aparece em vermelho
   é de **locais diferentes**, com os nomes (A e B) e a distância. As
   duplicatas ignoradas aparecem como círculos cinzas no mapa e numa lista
   recolhível no painel. Clique em um ponto para ver o nome e o link para o
   cadastro no OpenStreetMap, e use **Zoom no par** para enquadrar os dois.
   Desmarcando a opção, o resultado é o par mais próximo "cru", que costuma
   ser uma duplicata.
3. **Para ver o próximo par, clique em Tirar B da busca e ir ao próximo
   par.** O ponto B sai da lista, vai para **Locais tirados da busca** e o
   próximo par mais próximo é calculado; se ele estiver fora da área visível,
   o mapa vai até ele. **Restaurar tudo** volta à lista original.
4. **Compare o desempenho** com a força bruta no painel (comparações e tempo),
   ou pelo `GET /benchmark`. Em *Outras opções* dá para gerar pontos
   aleatórios (`GET /pontos-aleatorios`), clicar no mapa para adicionar pontos
   e mostrar a **linha de corte** e a **faixa central** da divisão principal
   do algoritmo, em laranja.

> O botão tira sempre o ponto B da busca. Como o local some das buscas
> seguintes, ele também deixa de aparecer em pares futuros; **Restaurar tudo**
> desfaz isso.
>
> O limite de 30 m é uma regra prática, não uma certeza: dois locais diferentes
> muito colados (por exemplo, dois prédios do mesmo hospital) podem ser
> tratados como duplicata. Se isso acontecer, diminua o limite ou desmarque a
> opção.

### As métricas

| Métrica              | O que é                                                                   |
| -------------------- | ------------------------------------------------------------------------- |
| Distância            | Distância em metros (haversine) entre os dois pontos do par encontrado.   |
| Comparações          | Quantas vezes dois pontos tiveram a distância calculada.                  |
| Tempo (ms)           | Tempo só do algoritmo, sem rede.                                          |
| Pontos na faixa      | Quantos pontos caíram na faixa central em cada divisão.                   |
| Máx. vizinhos/ponto  | Maior número de vizinhos comparados por ponto na faixa (nunca passa de 7).|

### Dividir e conquistar x força bruta

Medido em uma máquina de teste, com pontos aleatórios (os tempos variam de
computador para computador, mas a diferença de comparações não):

| Pontos | D&C (ms) | D&C (comparações) | Força bruta (ms) | Força bruta (comparações) |
| -----: | -------: | ----------------: | ---------------: | ------------------------: |
|    100 |     0,22 |               125 |             0,63 |                     4.950 |
|    500 |     1,15 |               572 |            15,26 |                   124.750 |
|  1.000 |     2,41 |             1.094 |            62,10 |                   499.500 |
|  2.000 |     5,39 |             2.294 |           248,60 |                 1.999.000 |
|  3.000 |     7,35 |             4.149 |           558,99 |                 4.498.500 |

Com 3.000 pontos, a força bruta faz mais de 4 milhões de comparações e o
dividir e conquistar faz cerca de 4 mil. Com 20.000 pontos (limite da API),
só o dividir e conquistar roda, em torno de 70 ms.

## Outros

### A API

**`POST /par-mais-proximo`** — recebe os pontos e devolve o par mais próximo:

```bash
curl -X POST http://127.0.0.1:8000/par-mais-proximo \
  -H "Content-Type: application/json" \
  -d '{"pontos": [
        {"lat": -15.7942, "lon": -47.8822},
        {"lat": -15.7801, "lon": -47.9292},
        {"lat": -15.7939, "lon": -47.8828},
        {"lat": -16.0192, "lon": -48.0642}
      ]}'
```

Campos opcionais do pedido: `ignorar_duplicatas_ate_m` (limite em metros;
quando informado, tira as duplicatas antes de achar o par; padrão: desligado),
`tem_nome` em cada ponto (se informado, entre duas duplicatas fica a que tem
nome), `comparar_forca_bruta` (padrão `true`),
`limite_caso_base` (padrão `3`, de 3 a 50) e `max_nivel_passos` (padrão `4`,
de 0 a 10: até que nível da recursão os passos são devolvidos).

Resposta (exemplo com os pontos acima; os tempos variam):

```json
{
  "ponto_a": { "indice": 2, "lat": -15.7939, "lon": -47.8828 },
  "ponto_b": { "indice": 0, "lat": -15.7942, "lon": -47.8822 },
  "distancia_metros": 72.3,
  "dividir_conquistar": { "tempo_ms": 0.029, "comparacoes": 3 },
  "forca_bruta": { "tempo_ms": 0.005, "comparacoes": 6 },
  "mesmo_resultado": true,
  "limpeza": null,
  "passos": [
    {
      "nivel": 0,
      "n_pontos": 4,
      "lon_divisao": -47.8828,
      "lon_faixa_esquerda": -47.8835,
      "lon_faixa_direita": -47.8821,
      "delta_lados_m": 72.3,
      "delta_final_m": 72.3,
      "pontos_na_faixa": 2,
      "comparacoes_faixa": 1,
      "max_vizinhos_por_ponto": 1
    }
  ]
}
```

Com `ignorar_duplicatas_ate_m`, o campo `limpeza` traz o limite usado, o tempo
gasto e a lista `duplicatas` (`indice_mantido`, `indice_removido` e
`distancia_metros`); `truncada` indica que a limpeza parou no limite de 2.000
remoções ou de 10 s com duplicatas ainda por tirar. Os índices de todo o
resultado são sempre posições na lista enviada. O tempo e as comparações do
dividir e conquistar e da força bruta se referem ao último cálculo, já depois
da limpeza.

`mesmo_resultado` confirma que o dividir e conquistar e a força bruta acharam a
mesma distância. A força bruta só roda com até 3.000 pontos; acima disso o campo
vem `null`. O limite da API é de 20.000 pontos por pedido.

**`GET /categorias`** — as categorias de locais, indicando quais já têm dados
baixados (`disponivel`).

**`GET /locais?categoria=farmacia`** — os locais da categoria (`lat`, `lon`,
`nome` e `osm`, que identifica o cadastro no OpenStreetMap, como `node/123`).
Devolve **404** com a instrução de baixar os dados se a categoria ainda não
tem arquivo. Entrega no máximo 20.000 locais; o campo `total` informa quantos
existem.

**`GET /pontos-aleatorios?n=100&seed=1`** — gera `n` pontos aleatórios dentro
do DF (`seed` é opcional e torna o resultado repetível).

**`GET /benchmark?tamanhos=100,500,1000`** — mede os dois algoritmos em cada
tamanho e devolve tempo e número de comparações (até 10 tamanhos, cada um de
2 a 20.000).

### Estrutura do projeto

```
backend/
├── closest_pair.py        algoritmo dividir e conquistar + força bruta
├── geo.py                 lat/lon para metros e distância haversine
├── locais.py              leitura dos locais e download do OpenStreetMap
├── baixar_dados.py        script que baixa os locais para data/
├── main.py                API FastAPI
├── test_closest_pair.py   testes do algoritmo contra a força bruta
├── test_locais.py         testes da leitura e do download (sem internet)
├── requirements.txt
└── data/                  locais baixados, um JSON por categoria (vai no git)
frontend/
├── index.html             mapa Leaflet e painel de controle
└── app.js                 chamadas à API e desenho do resultado
run.py                     sobe backend e frontend juntos
```

### Implementação

- **`closest_pair.py`** — o algoritmo completo: divisão por `x`, recursão,
  *merge* por `y`, varredura da faixa central (máx. 7 vizinhos por ponto) e o
  registro dos passos da recursão. Também tem a versão de força bruta, usada
  como gabarito e como comparação de tempo, e `remover_duplicatas`, que repete
  o par mais próximo e tira um ponto de cada par a menos do limite até sobrar
  só local diferente (com teto de remoções e de tempo). A ordenação inicial usa o
  `sorted` do Python; o resto (merge por `y`, faixa, recursão) é próprio.
- **`geo.py`** — projeção lat/lon para metros e distância haversine.
- **`locais.py`** e **`baixar_dados.py`** — lista as categorias, lê os arquivos
  de `data/` e baixa os dados da Overpass API. O download se identifica com um
  `User-Agent` (como a política de uso pede), tenta dois servidores com espera
  crescente entre as tentativas, trata o caso em que o Overpass responde 200
  mas avisa que a consulta estourou o tempo, e só grava o arquivo se o
  download deu certo (um arquivo antigo nunca é trocado por um pela metade).
- **`main.py`** — endpoints, validação dos pedidos e conversão dos passos da
  recursão de volta para longitude, pronta para desenhar no mapa.
- **`frontend/`** — mapa com Leaflet. Carrega as categorias e os locais pela
  API, envia só `lat`/`lon` para o cálculo, destaca o par mais próximo e mantém
  a lista de pares removidos. A divisão principal (nível 0 da recursão, pedida com
  `max_nivel_passos: 0`) é desenhada como linha de corte e faixa central.
  Os nomes vindos do OpenStreetMap entram na página só como texto, nunca
  como HTML.

**Bibliotecas:** nenhuma função pronta de geometria ou de par mais próximo
(como `scipy.spatial`) é usada — o algoritmo é todo implementado do zero.
**FastAPI** apenas serve a API, **Leaflet** desenha o mapa e a **Overpass API**
(OpenStreetMap) fornece os locais no download. Dados © colaboradores do
OpenStreetMap, licença ODbL.

### Testes

```bash
cd backend
python3 -m unittest -v
```

Os testes usam a força bruta como gabarito: o dividir e conquistar precisa dar
a **mesma distância** em 500 conjuntos aleatórios (com coordenadas inteiras que
geram pontos repetidos e empates, e com tamanhos de caso base diferentes),
além de casos difíceis como pontos todos no mesmo `x`, todos no mesmo `y` e
pontos duplicados. Também verificam que nenhum ponto da faixa central compara
mais de 7 vizinhos. A limpeza de duplicatas é testada com clusters de pontos
colados, a escolha de qual ponto sai, os tetos de remoções e de tempo, o caso
de todos os pontos iguais e 200 conjuntos aleatórios, verificando que nada se
perde nem se repete e que o par mais próximo do que sobra está além do limite.

Os testes de `test_locais.py` cobrem a leitura dos arquivos e o download com
respostas simuladas (nenhum usa a internet): servidor limitando com HTTP 429,
servidor principal fora do ar caindo no de reserva, resposta 200 com aviso de
tempo esgotado, consulta recusada, resposta que não é JSON e a garantia de que
um download que falha não apaga os dados antigos.

### Rodando as partes separadas

```bash
python3 backend/main.py                 # só a API
cd frontend && python3 -m http.server 5500   # só a interface
cd backend && python3 -m unittest -v    # só os testes
cd backend && python3 baixar_dados.py   # só o download dos dados
```