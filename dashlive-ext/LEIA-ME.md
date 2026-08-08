# DashLive · Monitor Ao Vivo — Extensão Chrome (v1.2)

Painel operacional de live commerce que aparece **sobreposto na tela da LIVE** no Seller Center do TikTok. Lê os números direto da página e roda o semáforo de saúde em tempo real — sem digitar nada.

Modelo do guia oficial BR: **GMV = Impressões × GPM**, funil **ERR → CTR → CO → AOV**, prioridade ⭐⭐⭐/⭐⭐/⭐.

> **Os benchmarks não são mais constantes no código.** Saem da tabela `lives` do Supabase — a mesma fonte do `dash-live.html` — via `gerar_benchmarks_live.py`. Ver "Benchmarks" abaixo.

## Instalar (1 vez, ~1 min)

1. `chrome://extensions` → ligue o **Modo do desenvolvedor**.
2. **Carregar sem compactação** → selecione a pasta `dashlive-ext/` do repo.
3. O ícone do DashLive aparece na barra.

Se o `benchmarks.js` estiver velho (ou você quiser a janela mais recente):

```bash
python3 gerar_benchmarks_live.py     # regrava dashlive-ext/benchmarks.js a partir de `lives`
```

Depois, em `chrome://extensions`, clique em recarregar na extensão.

## Usar

1. Abra o **Seller Center / console da LIVE** no Chrome.
2. Ícone do DashLive → **meta de GMV** + **duração** → **Iniciar live**.
3. No painel: aba **Dados** → **Calibrar métricas**.

### Calibração

O TikTok ofusca os nomes internos dos elementos, então a extensão **aprende** onde cada número está: você clica em cada métrica na página uma vez.

Ordem do funil: **ERR · Impressões · Cliques em produto · Views · CTR · CO · GMV · Pedidos · Comentários**.
Impressões, cliques e comentários são opcionais — mas **calibrar os cliques é fortemente recomendado**, e o motivo está logo abaixo.

Quebrou depois de uma atualização do TikTok? **Recalibra.** Sem esperar dev.

## Benchmarks — de onde vêm e por que há dois conjuntos

Rastreáveis: cada número traz janela, n e a coluna de origem, e o painel mostra contra **qual régua** a live está sendo julgada.

**A coluna `ctr` da nossa base tem dois denominadores diferentes**, conforme a versão do export do Seller Center:

| Perfil | CTR é | Ordem de grandeza |
|---|---|---|
| `views` | cliques em produto ÷ **views** | ~22% |
| `impressoes` | cliques em produto ÷ **impressões de produto** | ~6,5% |

São métricas distintas com o mesmo nome. Julgar uma pela régua da outra pinta a live inteira de vermelho — por isso o perfil é **detectado**, nunca presumido:

- **Com os cliques calibrados** → a extensão reproduz os dois quocientes e vê qual bate com o CTR da tela. Decisão exata (acerta em 75/75 lives reais no teste).
- **Sem os cliques** → só resta a ordem de grandeza. Funciona na maioria, mas uma live de CTR genuinamente ruim é indistinguível de uma medida no outro denominador. Nesses casos o painel **diz que não sabe** em vez de escolher errado — e por isso essa via nunca fixa o bench sozinha.

### O que mudou de verdade em relação ao build anterior

| Antes | Agora | Por quê |
|---|---|---|
| CO 8,9% "provisório" (2,52 ÷ 28,4) | **CO medido** (coluna `ctor`) | `ctor` **é** a taxa de compra após clique — bate ao 4º decimal em 235/235 lives. O 8,9% saiu de dividir onde era pra multiplicar; com ele, **50 de 50** lives reais entravam em vermelho |
| Conv/visualização 2,52% "medida" | **derivada** = CTR × CO (~0,57%) | 2,52 era o próprio CO. A conversão por visualização é o produto das etapas |
| Ticket bench R$67 | **R$81,88** (GMV ÷ pedidos) | R$67 era `avg_price` = preço por **item**. O painel calcula GMV÷pedidos — outro denominador |
| "Pico de viewers 9.519" | **Views médias por live** | O pico médio real é ~180. 9.519 era da ordem de *views*, não de pico |
| CTR 28,4% fixo | **régua detectada** (22,4% ou 6,58%) | Ver acima |

Registrado em `docs/DECISOES-E-PREMISSAS.md` (R10 e R11).

## O que o painel entrega

- **Semáforo em cascata**: desfecho = **GMV/hora** (⭐⭐⭐), diagnosticado pelo funil **ERR → CTR → CO → AOV** (⭐⭐), com engajamento (⭐) puxando amarelo *antes* do resultado cair. O motivo aponta o **gargalo mais acima** — é onde a correção rende mais.
- **KPIs na ordem do funil** + faixa de **derivados** (conv/visualização = CTR×CO · GPM = GMV/1k impressões) + linha de **proveniência** dizendo qual régua está valendo e de que janela.
- **Gatilhos com as alavancas do guia**: CTR baixo → ≤30 itens, reordenar (heróis nas posições 1-5 e 26-30), fixar todos, descrição assertiva. CO baixo → preço, oferta relâmpago com estoque limitado, cupom + frete. ERR caindo → aquecer 40min antes, cenário, câmera-mic-luz. O gatilho de GMV **decompõe** em alcance vs eficiência.
- **Aba Sacola**: cue sheet com tipagem (Gerador de Tráfego / Herói / Valor Agregado), aviso de **≤30 itens**, marcação das **posições nobres** (1-5 e as 5 últimas), alerta de herói fora da vitrine.
- **Compliance**: registrar violação (horário + motivo + ação) → timeline + relatório.
- **Frameworks**: 6 mecânicas com roteiro pronto + "Usei agora".
- **Snapshots** a cada 15min (ou manual) → **relatório pós-live**.

Painel **arrastável**, **minimizável** (–) e **ocultável** (×).

## Gravação no Supabase

No popup, **Senha do painel** (a mesma do admin) → **Conectar**. O token fica no storage local do Chrome; a extensão nunca vê a service key — a escrita passa por `/api/get-hub` (`action=live_monitor`), igual ao resto do projeto.

Com a conexão ativa, **Encerrar live grava o relatório** em `live_monitor_sessao` + `live_monitor_snapshot`. O id sai do horário de início, então reenviar atualiza em vez de duplicar. O **JSON continua saindo sempre** — se a rede falhar, a live não fica sem relatório.

⚠️ **Antes do primeiro uso:** rodar `rhode-vercel/sql/live_monitor.sql` no Supabase → SQL Editor.

Conferência: a view `live_monitor_vs_oficial` põe lado a lado o GMV lido na tela e o GMV atribuído do `live_attr`. Divergência grande = calibração apontando pro número errado, não "o dado mudou".

## Privacidade e permissões

`storage` é a única permissão. Hosts: os domínios do TikTok (leitura da tela) e `dash.rhodejeans.com.br` (gravação do relatório). Sem remote code, sem eval, sem lib externa em runtime — inclusive as fontes, que agora usam a stack do sistema. Overlay em Shadow DOM, sem vazar CSS pra página.

## Testes

```bash
node tests/test_dashlive_lib.mjs
```

Parsing pt-BR, derivados, detecção de régua e **round-trip contra uma amostra real da tabela `lives`**: cada valor é formatado como o Seller Center pinta e devolvido ao parser, pra garantir que o que o painel lê ao vivo é o mesmo número que vai pro dashboard.

## Se o painel não aparecer

Confirme que a aba é `*.tiktok.com` / `*.tiktokglobalshop.com` / `*.tiktokshop.com`. Se o Seller Center usar outro domínio, é só adicionar em `matches` e `host_permissions` no `manifest.json` e recarregar.

## Pendente (Sprint 2)

- **Sync multi-device**: espelhar o painel no celular enquanto o operador opera no desktop. Hoje o estado é por navegador/perfil.
- **`room_id` na sessão**: hoje a conferência com `live_attr` casa pela sala mais próxima no mesmo dia. Com o `room_id` capturado da URL da live, o join fica exato.
