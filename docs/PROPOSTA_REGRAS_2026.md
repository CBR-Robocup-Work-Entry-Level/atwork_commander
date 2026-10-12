# RoboCup@Work Brasil Entry-Level 2026 — formato das tasks e ajustes de regra

**Para:** Mikael (Chair Regular) e TC. **De:** Victor Ayres (Chair Entry-Level).
**Objetivo:** fechar o formato do arquivo de task que o Commander gera, resolver
as dúvidas que as equipes levantaram e listar os pontos do rulebook v1 que
precisam de uma frase a mais. Nenhuma regra de identidade muda; o que muda é o
arquivo ficar explícito.

---

## 1. O que as equipes perguntaram

1. "Tendo dois cubos com o mesmo ID mas de cores distintas, como vamos saber
   para onde levar, se o arquivo final só diz 'na mesa tal vai estar o cubo 1'
   e a cor não é mais informada?"
2. "Como a PP vai ser representada agora que cada slot tem uma AprilTag de
   referência? Vai ser passado o estado inicial da mesa de precisão (no slot 21
   está o ATTC 1, no 22 o ATTC 3, o 23 vazio...)?"

As duas perguntas têm a mesma raiz: o arquivo do ano passado dizia **em qual
área** o objeto termina, mas não **onde dentro da área**, e deixava para o
robô deduzir o resto a partir de regras de texto. Isso quebrou no momento em
que (a) a cor saiu do arquivo e (b) a PP ganhou tags de referência.

## 2. Regras que ficam exatamente como estão

- ATTC não tem identificador de cor na tag. Cubos azuis e vermelhos usam IDs
  de 1 a 30. O mesmo ID pode existir nas duas cores na arena; **nunca** o mesmo
  ID na mesma cor.
- Container não tem ID: é reconhecido só pela cor, e descrito pela workstation
  em que está. Containers de cores diferentes podem dividir a mesma
  workstation; **nunca** dois da mesma cor na mesma workstation.
- A cor dos ATTCs não é informada no arquivo de equipe.

## 3. Como cada conflito é resolvido (sem mudar essas regras)

| Conflito | Solução no arquivo / gerador |
|---|---|
| Mesmo ID em duas cores, cor não informada | **IDs únicos por task.** O inventário pode ter 4 azul e 4 vermelho, mas uma task só sorteia um deles (e decoys nunca repetem ID de objeto). Dentro de uma task, "cubo 4" é sempre um cubo só. |
| "Cubo entra no container da própria cor" obrigava o robô a deduzir dentro/fora | O arquivo diz explicitamente: `containers: {BLUE: [4]}` = cubo 4 dentro do container azul; `table: [9]` = cubo 9 solto na mesa. A regra de cor vira garantia do gerador, não dedução do robô. |
| Container sem ID | Identidade = cor + workstation: `containers: [{color: BLUE, at: WS_1}]`, e dentro do estado de WS_1 a chave `containers.BLUE`. |
| PP com tags de referência por slot | Cada slot tem uma tag **fixa** (101..107, esquerda para direita), listada em `precision_tables`. O estado diz `slots: {101: null, 102: 4, ...}` (tag do slot -> objeto, null = vazio). |
| AMT: ordem inicial da PP | **Não é informada.** `start_state.PP.slots: null`; o arquivo lista os 6 objetos presentes; o robô lê as tags e descobre. `finish_state` é explícito slot a slot. |
| Zona de empilhamento | Área de serviço própria, `ST`, com tag de referência fixa (200) no centro. O estado diz `stack: [13, 8]` = 13 na base (sobre a tag), 8 em cima. |
| Prateleira: nível | `levels: {BOTTOM: [...], TOP: [...]}` explícito, em vez de "entrega é sempre em cima". |
| Ordem de `obj_ids` era posição | `obj_ids` passa a ser só o conjunto de objetos na área (ordem crescente). A posição está nas chaves `table` (esq. -> dir.), `containers`, `levels`, `slots`, `stack`. A união delas é sempre igual a `obj_ids`, e o Commander confere isso em cada arquivo gerado. |

Efeito prático para as equipes: um parser do ano passado que só lê `obj_ids`
continua acertando a área de destino; quem quiser pontuação completa lê a
chave de posição da área. Nada aumenta de dificuldade: o robô continua tendo
de ler tags, achar o container pela cor e posicionar na PP, exatamente como o
rulebook já pedia. O que some é a adivinhação.

## 4. O arquivo novo, de relance

```yaml
task_id: ATT2
active_service_areas: [WS_1, WS_4, SH_2, PP]
objects: [{id: 4}, {id: 9}, {id: 17}, {id: 22}]
containers: [{color: BLUE, at: WS_1}, {color: RED, at: WS_4}]
precision_tables:
  PP: {slot_tags: [101, 102, 103, 104, 105, 106, 107]}
finish_state:
  WS_1: {obj_ids: [4],  table: [],  containers: {BLUE: [4]}}
  WS_4: {obj_ids: [17], table: [],  containers: {RED: [17]}}
  SH_2: {obj_ids: [9],  levels: {BOTTOM: [], TOP: [9]}}
  PP:   {obj_ids: [22], slots: {101: null, 102: null, 103: 22, 104: null, 105: null, 106: null, 107: null}}
```

Contrato completo, campo a campo: `config/schema_task_equipe.yaml` no
repositório do Commander. O guia do juiz (cores, decoys, obstáculos,
coordenadas de montagem) continua separado.

## 5. Pontos do rulebook v1 que pedem uma frase nova

Nenhum muda uma regra de identidade; são esclarecimentos para o texto não
contradizer o arquivo.

1. **2.8 (última frase):** "O ID da tag corresponde ao ID do objeto que deve
   ser colocado naquela cavidade." Isso exigiria trocar as placas da PP a cada
   rodada e não funciona no AMT. Proposta: *as tags de referência dos slots
   são fixas, com IDs fora da faixa dos ATTCs (101..107, da esquerda para a
   direita); o arquivo da task diz qual objeto vai em qual slot.*
2. **2.7.3:** "No máximo cinco cavidades são utilizadas no teste" contradiz
   4.4.1 (6 tags + 1 slot vazio). Proposta: *a mesa de precisão tem 7 slots.*
3. **4.4.1 (AMT):** (a) são ATTCs (cubos) com tags 1 a 6, não tags soltas;
   (b) o arranjo inicial não é informado à equipe; (c) estado final = ordem
   crescente da esquerda para a direita, **slot da ponta direita vazio**
   (o arquivo diz isso slot a slot, para não haver duas leituras de "ordem
   crescente com um slot vazio").
4. **2.7.4 (zona de empilhamento):** "será localizada em alguma das mesas... a
   mesa será definida durante a competição." Proposta: *a área de empilhamento
   é uma área de serviço própria (`ST`), fixa na arena, com uma AprilTag de
   referência (ID 200) no centro; a pilha é montada sobre a tag.* Isso também
   fecha o 4.4.2 ("empilhados em uma área de serviço ativa"): é na ST.
5. **4.4.2 / 4.5 (containers):** o texto não diz a cor do cubo que entra em cada
   container. Proposta: *um ATTC só entra no container da própria cor* (já é
   assim no 4.4.3; vira regra geral). O arquivo diz qual cubo entra em qual.
6. **Ordem da pilha:** o rulebook não define. Proposta: *o arquivo lista a pilha
   da base ao topo e essa é a ordem esperada.* Alternativa mais leniente: só o
   conjunto conta. Precisa de decisão do TC; o Commander já gera a ordem.
7. **Faixas de ID:** formalizar *ATTCs: 1..30; tags fixas da arena: >= 100;
   família tag36h11.* Hoje só os ATTCs estão escritos.
8. **2.7.5 (containers):** acrescentar *no máximo um container de cada cor por
   workstation*, que é o que o grupo já combinou.
9. **Decoys (4.4.2):** acrescentar *objetos de distração nunca repetem o ID de
   um objeto da task* (senão o ID deixa de identificar o cubo).
10. **4.5 vs 2.7.1 (alturas):** a Final fala em "0-15 cm" e 2.7.1 só lista
    5, 10 e 15. A arena base de Salvador tem mesas de 0 cm; incluir 0 cm em
    2.7.1.
11. **4.5:** "Dois ATTCs devem ser coletados de uma prateleira (na parte
    inferior)". Com duas prateleiras na arena, o gerador pode usar as duas.
    Proposta: *de prateleira(s)*.

## 6. Respostas prontas para o grupo das equipes

> **Mesmo ID em duas cores.** Dentro de uma task o ID nunca se repete: se a
> task pede o cubo 1, existe um único cubo 1 na arena naquela rodada. A arena
> pode ter o 1 azul e o 1 vermelho no estoque, mas o gerador nunca usa os dois
> juntos. A cor continua não sendo informada; o destino de cada cubo é
> explícito no arquivo (mesa, dentro de qual container, nível da prateleira,
> slot da PP, posição na pilha).

> **PP e AMT.** Cada slot da mesa de precisão tem uma AprilTag fixa acima
> (101..107, da esquerda para a direita), listada no arquivo em
> `precision_tables`. No AMT o estado inicial da PP **não** é informado
> (`slots: null`): o arquivo diz quais 6 objetos estão na mesa, e o robô lê as
> tags para descobrir onde cada um está. O estado final é explícito:
> `slots: {101: 1, 102: 2, ..., 106: 6, 107: null}`. Nos testes de transporte
> (ATT2, Final) o `finish_state` da PP diz exatamente em qual slot cada objeto
> termina.

## 7. O que muda no Commander (v2.1.0)

- Contrato novo do arquivo de equipe (`config/schema_task_equipe.yaml`) e
  checagem automática do contrato em cada geração (`tools/selftest.py`).
- Metaarena schema v5: tags dos slots da PP e tag da ST cadastráveis na GUI
  (padrões 101..107 e 200). Arquivos antigos abrem normalmente.
- Arena de exemplo = CBR 2026 baseada em Salvador 2025 (14 WS, 2 SH, PP, ST),
  descrita em `docs/arena_cbr2026.md`.
- ATT1 e Final empilham só na ST; AMT esconde o arranjo inicial.
- Guia do juiz traz slot + tag de cada objeto na PP e a tag de referência da
  ST.

Para testar: `python main.py` (GUI) ou
`python main.py gerar ATT2 --seed 42` e `python tools/selftest.py 200`.
