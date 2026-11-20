# @Work Commander

Gerador de tasks da **RoboCup@Work Brasil (Entry-Level)**, edição 2026. O
operador cadastra a arena como ela foi montada de verdade, escolhe a prova,
confere os arquivos no preview e baixa. Cada geração produz **dois arquivos**:

| Arquivo | Para quem | Conteúdo |
|---|---|---|
| `<PROVA>_seed<N>_equipe.yaml` | equipes | YAML no formato oficial da competição, com a **cor** e a **posição explícita** de cada objeto. Sem decoys, sem obstáculos, sem seed. |
| `<PROVA>_seed<N>_juiz.yaml` | juiz / TC | Planta de montagem: **coordenada (x, y) em cm de cada cubo**, decoys, obstáculos, estado final, transportes e conferência. |

A aba **Cronômetro** marca a rodada: 3 min de preparo e o tempo oficial de cada
prova, com reinício e registro do tempo final da equipe.

O contrato do arquivo de equipe está em
[config/schema_task_equipe.yaml](config/schema_task_equipe.yaml); as decisões
de regra por trás dele, em [docs/PROPOSTA_REGRAS_2026.md](docs/PROPOSTA_REGRAS_2026.md).

## Uso

```bash
pip install -r requirements.txt

python main.py                                # GUI (caminho normal)
python main.py checar                         # situação da arena, prova por prova
python main.py gerar ATT2 --seed 42 --decoys 3
python main.py gerar ATT1 --empilhamento WS_3 # zona de empilhamento em WS_3 nesta geração
python tools/selftest.py 200                  # estresse: 200 seeds por prova + contrato
python tools/test_cronometro.py               # máquina de estados do cronômetro
python main.py planilha ATT2_seed42_equipe.yaml --equipes "FEI;UFMG;Robotronix"
                                              # planilha dos juízes de uma task salva
```

Requer Python 3.10+, PyYAML, openpyxl e tkinter (já vem no Python para Windows).

## Onde ficam os arquivos

O programa é feito para virar executável, então nada gravável mora na pasta do
projeto:

- **Metaarena:** `%APPDATA%/atwork_commander/metaarena.json` (Windows) ou
  `~/.config/atwork_commander/` (Linux/macOS). Na primeira execução ele parte de
  `config/metaarena.exemplo.json`, que é a **arena de referência da CBR 2026**
  (base: RoboCup 2025 Salvador, 10 m x 7,5 m, 15 workstations — uma delas com a
  zona de empilhamento —, 2 prateleiras e mesa de precisão). Descrição e medidas em
  [docs/arena_cbr2026.md](docs/arena_cbr2026.md).
- **Tasks geradas:** pasta **Downloads** do usuário por padrão, escolhível no
  preview.
- **Histórico do cronômetro:** `cronometro.csv`, na mesma pasta da metaarena.
- **Lista de equipes da planilha dos juízes:** `equipes.json`, na mesma pasta.

## Fluxo da GUI

1. **Arena** — cadastra as Áreas de Serviço. Pode importar direto o
   `service_areas.yaml` do mapa do robô (ROS 2), que já traz IDs, tipos e as
   dimensões de mesa. Aqui também se cadastram a **distância aproximada** de
   cada área até o START e o FINISH, as **tags de referência fixas** da mesa de
   precisão (padrão 101..107) e **qual workstation hospeda a zona de
   empilhamento** (tag padrão 200).
2. **Inventário** — marca quais ATTCs existem fisicamente (grade tag × cor) e
   quantos containers a organização tem.
3. **Gerar task** — uma prova por vez. A aba mostra antes o que a arena atende e
   o que não atende; o botão gera e abre o preview com as duas abas (equipe e
   juiz). Nada é gravado antes da confirmação. A mesa da zona de empilhamento
   pode ser trocada aqui mesmo, antes de gerar.
4. **Cronômetro** — escolhe a prova (os tempos já vêm definidos) e a equipe.
   **START** começa os 3 min de preparo; **START** de novo (equipe pronta)
   começa o tempo da prova — se os 3 min zerarem, a prova começa sozinha.
   **RESET** é o reinício da equipe: guarda o tempo de prova restante, para o
   relógio e volta aos 3 min de preparo esperando o START; a prova seguinte
   continua do tempo guardado (um reinício por rodada, rulebook 5.6). **STOP**
   encerra e registra o tempo final (usado, restante e bônus de tempo) na tela
   e no `cronometro.csv`.
5. **Planilha dos juízes** — gera, quando você pedir, o `.xlsx` de pontuação de
   uma task. Escolha o `…_equipe.yaml` (depois de gerar na aba 3 ele já vem
   preenchido) e digite as equipes, uma por linha, quantas forem. A planilha
   sai com a aba **Prova** (objetivos, áreas, decoys e a tabela de pontos
   editável), uma **aba por equipe** com o nome dela e a **Classificação**. O
   juiz marca `x` nos objetivos e nas áreas, digita penalidades e o tempo
   restante, e o total atualiza na hora. Nada fica congelado nem protegido.

## As regras que o arquivo de equipe segue

Identidade (edição 2026, conforme a reunião TC/OC de 30/07/2026):

- um ATTC é o par `(tag, cor)`; o mesmo par nunca existe duas vezes na arena;
- a mesma tag pode existir nas duas cores na arena, nunca na mesma mesa;
- a cor de cada ATTC **é informada** à equipe (`objects: [{id: 4, color: BLUE}]`);
- container **não tem AprilTag**: o arquivo informa a cor e a workstation de
  cada um, e localizar o container sobre a mesa (pela cor) é tarefa do robô;
  no máximo um container de cada cor por workstation;
- decoys **não** entram no arquivo de equipe: são cubos com ID fora da lista de
  objetos da task, e aparecem só no guia do juiz.

O que o gerador garante para que nada seja ambíguo:

- **IDs únicos por task** — nem objetos entre si, nem decoys contra objetos.
  "Cubo 4" é sempre um cubo só, mesmo que a arena tenha o 4 nas duas cores;
- **cubo só entra em container da própria cor**, e o arquivo diz
  explicitamente qual cubo entra em qual container (`containers: {BLUE: [4]}`);
- **toda posição é explícita**: em cada área, `obj_ids` é o conjunto de objetos
  presentes (ordem crescente, sem posição) e as chaves `table`, `containers`,
  `levels`, `slots` e `stack` dizem exatamente onde cada um está. A união delas
  é sempre igual a `obj_ids`; `team_yaml.conferir()` checa isso e o selftest
  roda a checagem em todo arquivo gerado;
- **tags de referência no arquivo** (`precision_tables`, `stacking_areas`):
  nada precisa ser hardcoded no robô;
- **zona de empilhamento não é uma área própria**: é uma workstation da arena
  com uma tag de referência, escolhida pela organização (nunca sorteada). Nas
  provas com pilha (ATT1, Final) ela aparece em `stacking_areas` e a mesa só
  recebe a pilha (`stack`); nas demais é uma workstation comum;
- **AMT:** o arranjo inicial da mesa de precisão é escondido (`slots: null`);
  a equipe sabe quais objetos estão lá e qual é o estado final, slot a slot.

Não existe bloco `constraints`: o que antes era texto livre virou posição nos
estados.

## Metaarena

Cada Área de Serviço guarda:

| Campo | Por que existe |
|---|---|
| tipo, ID, altura | classificação do rulebook |
| **lado marcado** | balanceamento entre a zona segue-linha e o resto (ATT1/ATT2) |
| **distância do START / ao FINISH** (m, opcional) | BMT e BTT1 preferem as mesas de menor percurso; o guia do juiz mostra as distâncias |
| **níveis** | prateleira |
| **slots + tag de cada slot** | mesa de precisão (padrão 7 slots, tags 101..107) |
| **zona de empilhamento** (sim/não) + pilha máxima + tag de referência | workstation de 5, 10 ou 15 cm que hospeda a zona (padrão 3, tag 200); uma só por arena |

Só isso. Cada campo que sobrou muda alguma decisão do gerador; o resto foi
removido em vez de virar formulário para preencher:

- **posição `(x, y)` e grafo de caminhos** — basta a distância aproximada até
  o START e o FINISH, que se mede com trena ou contando placas do piso;
- **capacidade por área** — virou `rules.MAX_OBJETOS_POR_AREA`, teto único para
  workstation e prateleira (a mesa de precisão usa os slots);
- **flag "montada"** — apagar a linha da área faz o mesmo.

O **inventário** é a outra metade: um ATTC é o par `(tag, cor)`. O gerador só
sorteia o que está marcado, então nenhuma task pede objeto que a organização não
tem. Sem inventário cadastrado ele assume 1..30 nas duas cores e avisa no guia
do juiz.

Tags de referência fixas usam IDs a partir de 100, fora da faixa dos ATTCs
(1..30), e nunca se repetem na arena; a metaarena recusa salvar se repetirem.

## Coordenadas de montagem

O guia do juiz não diz "sobre a mesa": diz **onde**. Cada área vira uma grade de
posições fixas — as mesmas em todas as rodadas — e cada cubo recebe o `(x, y)`
em cm dentro da zona de manipulação, com a origem no canto frontal esquerdo.

```yaml
WS_2:
  tipo: workstation
  altura_cm: 5
  containers:
  - {cor: VERMELHO, x_cm: 66.4, y_cm: 15.0}
  objetos:
  - {tag: 3, cor: AZUL, posicao: 1, x_cm: 13.6, y_cm: 15.0}
  - {tag: 11, cor: AZUL, posicao: 2, x_cm: 26.8, y_cm: 15.0}
PP:
  tipo: mesa de precisao
  tags_dos_slots: [101, 102, 103, 104, 105, 106, 107]
  objetos:
  - {tag: 4, cor: AZUL, slot: 1, tag_do_slot: 101, x_cm: 11.7, y_cm: 15.0}
WS_15:
  tipo: workstation
  altura_cm: 10
  zona_de_empilhamento: {tag_de_referencia: 200, nesta_prova: EM USO - a mesa so recebe a pilha}
  objetos:
  - {tag: 1, cor: VERMELHO, sobre_a_tag_de_referencia: 200}
  - {tag: 3, cor: VERMELHO, empilhado_sobre_a_tag: 1}
```

As medidas da zona estão em `rules.py` (`ZONA_LARGURA_CM`, `ZONA_PROFUNDIDADE_CM`,
`ZONA_MARGEM_CM`, `TOLERANCIA_POSICAO_CM`) e a grade é calculada em
[core/layout.py](atwork/core/layout.py). Containers ocupam posições da direita
para a esquerda, objetos da esquerda para a direita — nunca disputam lugar.

## Arena incompleta

O rulebook descreve a arena ideal: 3 áreas de cada lado, prateleira em cada
lado, todas as alturas de mesa representadas. Arena real quase nunca fecha essa
conta.

Nada disso é restrição dura. O seletor pontua as combinações possíveis, fica com
a mais próxima do previsto e registra o que não deu como **desvio** — que
aparece no preview e no guia do juiz. A task sai do mesmo jeito.

Erro de geração só acontece quando não existe alternativa: nenhuma prateleira
para a prova que entrega em prateleira, nenhuma workstation marcada como zona
de empilhamento para ATT1 e Final, nenhuma mesa de 5 ou 10 cm para o BTT1, inventário sem cubos
suficientes.

## Estrutura

```
main.py                     entrypoint (GUI + CLI)
atwork/
  rules.py                  constantes do rulebook (inclui tags de referência)
  paths.py                  %APPDATA%, Downloads, PyInstaller
  cli.py                    linha de comando
  arena/                    modelo, persistência e importação da metaarena
    model.py storage.py importer.py
  core/                     núcleo do gerador
    task.py                 Task + TaskBuilder (invariantes de colocação)
    selection.py            escolha de áreas por melhor esforço
    objects.py              sorteio de cubos a partir do inventário
    layout.py               grade de posições e coordenada (x, y) de cada cubo
    obstacles.py            sorteio dos pares de área dos obstáculos
    cronometro.py           máquina de estados do cronômetro de rodada
  generators/               um módulo por prova, mesma interface
    bmt.py btt1.py btt2.py amt.py att1.py att2.py final.py
  validation/               schema.py (invariantes) + tests.py (regras da prova)
  export/                   team_yaml.py (+ conferir), referee_yaml.py, writer.py
  ui/                       app.py + uma aba por arquivo + preview_dialog.py
    theme.py                tema visual (ttk clam repintado no estilo Win 11)
    viewer.py               realce de sintaxe dos arquivos no preview
config/
  metaarena.exemplo.json    arena de referência CBR 2026, usada na primeira execução
  schema_task_equipe.yaml   contrato do YAML de equipe, campo a campo
docs/
  PROPOSTA_REGRAS_2026.md   decisões de formato e ajustes de texto do rulebook
  arena_cbr2026.md          layout da arena de referência
tools/selftest.py           estresse dos geradores + checagem do contrato
tools/test_cronometro.py    teste do cronômetro com relógio falso
```

O `metaarena.json` está no schema **v6**. Arquivos v1 a v5 continuam abrindo:
os campos aposentados são ignorados na leitura, os novos assumem o padrão, e o
arquivo só muda de formato quando você salva. A antiga área `ST` (tipo
STACKING) vira, na leitura, uma workstation nova com a zona de empilhamento
marcada — confira na aba Arena se é essa a mesa certa.

## Empacotar como executável

```bash
pip install pyinstaller
pyinstaller --noconsole --onefile --name atwork-commander ^
  --add-data "config;config" main.py
```

`atwork/paths.py` já resolve os caminhos tanto rodando do código quanto
congelado.

## Fonte de verdade

Rulebook CBR RoboCup@Work Brasil (Entry-Level), edição 2026 (v1, junho).
Durações: BMT 6, BTT1 10, BTT2 10, AMT 15, ATT1 20, ATT2 20, Final 30 min.
Onde o rulebook deixa margem, vale `docs/PROPOSTA_REGRAS_2026.md`, com as
atualizações registradas no topo daquele arquivo.
