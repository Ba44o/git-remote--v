# Playbooks — procedimentos repetíveis

Biblioteca do **como se faz**. Cada playbook nasceu de uma investigação real que deu certo —
a ideia é não redescobrir o caminho na próxima vez.

Diferença dos outros docs:
- `RUNBOOK.md` = **quebrou em produção** → sintoma → diagnóstico → fix
- `DECISOES-E-PREMISSAS.md` = **no que acreditamos** e por quê
- `PLAYBOOKS.md` (este) = **como conduzir** uma análise ou operação recorrente

---

## PB-1 · Diagnosticar uma queda de GMV

Extraído da investigação de jul/26 ([R1](DECISOES-E-PREMISSAS.md)). A lição central: **a
narrativa que chega junto com a queda quase sempre está errada.** Testar a narrativa por último.

1. **Fixar janela comparável.** Nunca mês fechado vs mês parcial — usar dias 1–N contra 1–N.
   Fonte: `pedidos_sku` no Supabase (não o warehouse, que defasa).
2. **Separar volume de preço.** Peças, GMV e preço/peça em três colunas. Na maioria dos casos
   um deles está parado e isso já mata metade das hipóteses.
3. **Checar mídia antes de qualquer coisa.** `ads_campanha` na mesma janela: custo, receita,
   ROI. **Gasto caindo com ROI intacto = causa dominante, pare aqui.** Foi exatamente isso em
   julho (−42% de gasto, ROI 7,78→7,81).
4. **Descartar ruptura com a curva diária** do hero. Curva contínua = não é estoque. Não
   aceitar "faltou produto" sem ver a curva.
5. **Só então testar a narrativa** (preço subiu? conteúdo piorou?).
6. **Ressalvas honestas obrigatórias:** preço realizado ≠ etiqueta; `video_perf` sofre viés de
   acumulação (vídeo novo teve menos tempo no ar) → não concluir queda de engajamento dali.
7. Fechar com veredito no ledger.

**Armadilha conhecida:** aceitar o briefing como premissa. Em julho o briefing dizia "o preço
subiu pra R$109,90" — o preço estava parado em R$80 havia 3 meses, e uma consultoria inteira
foi respondida em cima da pergunta errada.

---

## PB-2 · Decidir onde escalar (posição por motor)

Formato aprovado em 10/07/26 — gerador em `relatorios/_templates/posicao-escala-por-motor/`.
**Reusar o gerador, não reconstruir do zero.**

1. Uma aba **por motor**: Live própria · Live afiliada · Vídeo afiliada · GMV-Max. **Nunca
   blendar live própria com afiliada** (CPA R$7 vs R$406 — a média mente).
2. Por aba: (a) rentabilidade do canal — CPA, ROAS, contrib/peça; (b) projeção por SKU em
   **unidades**, mês anterior realizado → meta, com crescimento editável; (c) proporção % por
   SKU + classe HERO/ESTEIRA.
3. **Nunca misturar ads com projeção de venda.** Projeção é meta de venda por produto. Ads é
   lente de rentabilidade, aba separada.
4. Hero/Esteira é **por SKU**, da lista firme — nunca por modelo, nunca inventar categoria.
5. Contribuição: escolher a lente e **dizer qual é**. Antes-de-mídia e depois-de-mídia dão
   rankings **invertidos** (ver R3 no ledger).
6. Saída = arquivo **novo datado**, nunca sobrescrever (escrever em .xlsx aberto corrompe).

---

## PB-3 · Fechar o mês

1. Coletar na fonte viva (Supabase / API TikTok), não no `warehouse/*.csv`.
2. **GMV headline = GMV oficial** (Orders API, `total_amount` onde `paid_time>0`) — bate com o
   Seller Center. Não misturar os 3 níveis de GMV sem rotular.
3. Cascata de lucro: settlement − CPV − mídia − imposto. Imposto = **6,4%** (Lucro Presumido),
   e o custo de GMV Max sai **inteiro** da conta de ads.
4. KPIs sempre vs. período anterior. Sem dado = "sem dado".
5. Saída `.xlsx` (nível expert: fórmulas vivas, condicional, gráficos nativos) + `.md`, em
   `relatorios/AAAA-MM/`, nome `Relatorio <descrição>_<AAAA-MM-DD>`.
6. Filtros temporais sempre: Janela + Mês + Data (de/até). Ordenação decrescente.

---

## PB-4 · Antes de afirmar um número

Checklist curto, aplicável a qualquer entrega:

- [ ] Veio da fonte viva ou de um CSV que pode ter defasado?
- [ ] A query paginada tem `order=<coluna única>`? (sem isso o split por canal enviesa e **a
      contagem não denuncia** — R7)
- [ ] Média ou mediana? Seeding tem baleias — mediana R$4.149 vs média R$23.762.
- [ ] É medição ou **aposta**? Se é aposta, está rotulada e editável?
- [ ] Categoria/SKU foi conferida no catálogo ou foi inferida? (nunca inventar)
- [ ] O veredito da premissa foi dito em voz alta?

---

## Playbooks existentes em outros arquivos

| Playbook | Onde |
|---|---|
| Seeding — conteúdo e cobrança | [`docs/PLAYBOOK_SEEDING_CONTEUDO.md`](PLAYBOOK_SEEDING_CONTEUDO.md) |
| Bio Rhode — operação do CMS (hero, live, blocos) | [`docs/BIO-OPERACAO.md`](BIO-OPERACAO.md) |
| Relatório mensal de Seeding (6 abas, template aprovado) | memória `reference_seeding_report_template` |
| Conciliação ponta-a-ponta | [`docs/CONCILIACAO.md`](CONCILIACAO.md) |
| Debug de produção (17 cenários) | [`RUNBOOK.md`](../RUNBOOK.md) |

## Lacunas — playbooks que ainda faltam

- **Matar / escalar uma campanha** — critério de corte explícito (hoje é ad-hoc).
- **Lançar um SKU novo** — do catálogo ao seeding ao card.
- **Ativar creator parada** — a alavanca 206→160 da meta 10k nunca virou procedimento.
- **Investigar vazamento de checkout** — os R$104k/mês de Pix expirado (A5 no ledger).
