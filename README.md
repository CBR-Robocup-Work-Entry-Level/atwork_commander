# @Work Commander

Gerador de tasks da **RoboCup@Work Brasil (Entry-Level)**. O operador cadastra a
arena como ela foi montada de verdade, escolhe a prova, confere os arquivos no
preview e baixa. Cada geração produz **dois arquivos**:

| Arquivo | Para quem | Conteúdo |
|---|---|---|
| `<PROVA>_seed<N>_equipe.yaml` | equipes | YAML no formato oficial da competição. Sem cores de ATTC, sem decoys, sem obstáculos, sem seed. |
| `<PROVA>_seed<N>_juiz.yaml` | juiz / TC | Planta de montagem: **coordenada (x, y) em cm de cada cubo**, cores, decoys, obstáculos, estado final, transportes e conferência. |

## Uso

```bash
pip install -r requirements.txt

python main.py                                # GUI (caminho normal)
python main.py checar                         # situação da arena, prova por prova
python main.py gerar ATT2 --seed 42 --decoys 3
python tools/selftest.py 200                  # estresse: 200 seeds por prova
```

Requer Python 3.10+, PyYAML e tkinter (já vem no Python para Windows).

## Onde ficam os arquivos

O programa é feito para virar executável, então nada gravável mora na pasta do
projeto:

- **Metaarena:** `%APPDATA%/atwork_commander/metaarena.json` (Windows) ou
  `~/.config/atwork_commander/` (Linux/macOS). Na primeira execução ele parte de
  `config/metaarena.exemplo.json`.
- **Tasks geradas:** pasta **Downloads** do usuário por padrão, escolhível no
  preview.

## Fluxo da GUI

1. **Arena** — cadastra as Áreas de Serviço. Pode importar direto o
   `service_areas.yaml` do mapa do robô (ROS 2), que já traz IDs, tipos e as
   dimensões de mesa.
2. **Inventário** — marca quais ATTCs existem fisicamente (grade tag × cor) e
   quantos containers a organização tem.
3. **Gerar task** — uma prova por vez. A aba mostra antes o que a arena atende e
   o que não atende; o botão gera e abre o preview com as duas abas (equipe e
   juiz). Nada é gravado antes da confirmação.

No preview os dois arquivos aparecem com realce de sintaxe (esquema VSCode
Light+), sem biblioteca externa — tudo em tags do widget `Text`.

## Metaarena

Cada Área de Serviço guarda:

| Campo | Por que existe |
|---|---|
| tipo, ID, altura | classificação do rulebook |
| **lado marcado** | balanceamento entre a zona segue-linha e o resto (ATT1/ATT2) |
| **níveis / cavidades / pilha máxima** | geometria de prateleira, mesa de precisão e área de empilhamento |

Só isso. Cada campo que sobrou muda alguma decisão do gerador; o resto foi
removido em vez de virar formulário para preencher:

- **posição `(x, y)` e grafo de caminhos** — na arena da competição toda área é
  alcançável a partir de qualquer outra;
- **capacidade por área** — virou `rules.MAX_OBJETOS_POR_AREA`, teto único para
  workstation, prateleira e empilhamento (a mesa de precisão usa as cavidades);
- **flag "montada"** — apagar a linha da área faz o mesmo.

O **inventário** é a outra metade: um ATTC é o par `(tag, cor)`. O gerador só
sorteia o que está marcado, então nenhuma task pede objeto que a organização não
tem. Sem inventário cadastrado ele assume 1..30 nas duas cores e avisa no guia
do juiz.

Regras de identidade aplicadas:

- dois ATTCs com a mesma tag **e** a mesma cor nunca coexistem na arena;
- a mesma tag pode existir nas duas cores na arena, mas os dois cubos **nunca**
  vão para a mesma Área de Serviço;
- dentro de uma task os IDs são únicos — o arquivo de equipe não revela cor, e
  dois objetos de mesmo ID ficariam indistinguíveis;
- decoys nunca repetem ID de objeto de tarefa e só aparecem no arquivo do juiz;
- **todo cubo vai para o container da própria cor** — é o que permite ao robô
  deduzir o destino sem que o arquivo de equipe revele cor nenhuma;
- nenhum cubo termina solto na área que hospeda o container da mesma cor, porque
  aí "dentro" e "fora" seriam leituras igualmente válidas.

## O que o arquivo de equipe não diz

Ele não tem bloco `constraints`. Como colocar cada objeto sai do rulebook, não
da task: cubo entra no container da própria cor, entrega em prateleira é no
nível superior, coleta é no inferior, e na mesa de precisão cada tag vai na
cavidade que casa com ela. O arquivo descreve só o que muda de uma task para
outra — áreas ativas, objetos, onde cada um começa e onde termina.

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
para a prova que entrega em prateleira, nenhuma mesa de 5 ou 10 cm para o BTT1,
inventário sem cubos suficientes.

## Estrutura

```
main.py                     entrypoint (GUI + CLI)
atwork/
  rules.py                  constantes do rulebook
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
  generators/               um módulo por prova, mesma interface
    bmt.py btt1.py btt2.py amt.py att1.py att2.py final.py
  validation/               schema.py (invariantes) + tests.py (regras da prova)
  export/                   team_yaml.py, referee_yaml.py, writer.py
  ui/                       app.py + uma aba por arquivo + preview_dialog.py
    theme.py                tema visual (ttk clam repintado no estilo Win 11)
    viewer.py               realce de sintaxe dos arquivos no preview
config/
  metaarena.exemplo.json    arena de exemplo, usada na primeira execução
  schema_task_equipe.yaml   contrato do YAML de equipe, campo a campo
tools/selftest.py           estresse dos geradores
```

O `metaarena.json` está no schema **v4**. Arquivos v1 (`dist_start_m`), v2
(`x_m`/`y_m`/`vizinhos`, áreas `START`/`FINISH`) e v3 (`capacidade`,
`disponivel`, `nota`) continuam abrindo: os campos aposentados são ignorados na
leitura, e o arquivo só muda de formato quando você salva.

## Empacotar como executável

```bash
pip install pyinstaller
pyinstaller --noconsole --onefile --name atwork-commander ^
  --add-data "config;config" main.py
```

`atwork/paths.py` já resolve os caminhos tanto rodando do código quanto
congelado.

## Fonte de verdade

Rulebook CBR RoboCup@Work Brasil (Entry-Level), edição 2026. Durações:
BMT 6, BTT1 10, BTT2 10, AMT 15, ATT1 20, ATT2 20, Final 30 min.
