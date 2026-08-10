# CRM do TikTok Shop — Referência da ferramenta

> Mapeamento da interface a partir das telas do Seller Center (conta Rhode, BR).
> Capturado em **10/08/2026**. Documento descritivo: registra **o que a ferramenta oferece**.

**Caminho:** Central do vendedor → **Marketing → Clientes**
**URL:** `seller-br.tiktok.com/crm?module_name=segments&plan_category=2&plan_channel=im&shop_region=BR`

**Abas da tela:** `Criar planos de chat` · `Gerenciar planos de divulgação`
**Aba Segmentos:** `Padrão 6` · `Personalizado 0`

---

## 1. Criar segmento para clientes da loja

Campos do formulário:
- **Nome do segmento** (até 100 caracteres)
- **Condições** — *"Utilize pelo menos 3 condições para obter uma segmentação de clientes mais precisa."*
- **Tamanho estimado** — exibido no canto superior direito, atualiza conforme as condições
- Botão `+` para adicionar condições · ícone de lixeira para remover
- Ações: `Cancelar` · `Salvar`

**Tooltip da tela:** *"Os resultados dos segmentos são refinados usando nosso algoritmo."*

---

## 2. Catálogo de condições — 4 famílias, 19 condições

### 2.1 Dados demográficos (3)
| Condição |
|---|
| Idade |
| Gênero |
| Região |

### 2.2 Comportamento de compra (8)
| Condição |
|---|
| Navegaram nos produtos da loja |
| Salvaram os produtos da loja nos favoritos |
| Adicionaram produtos da loja ao carrinho |
| Avaliaram os produtos da loja |
| Fizeram pedidos |
| Valor do pagamento |
| Data do primeiro pedido |
| Data do último pedido |

### 2.3 Engajamento (5)
| Condição |
|---|
| Assistiram os vídeos com produtos à venda |
| Curtiram vídeos com produtos à venda |
| Produtos clicados em vídeos com produtos à venda |
| Assistiram a transmissões ao vivo |
| Clicaram em produtos na LIVE |

### 2.4 Desempenho de divulgação histórico (3)
| Condição |
|---|
| Leram suas mensagens |
| Clicaram nas suas mensagens |
| Cancelaram a assinatura de suas mensagens |

---

## 3. Janela de tempo

Seletor de **rádio** (escolha única), com apenas **3 opções**:

- Nos últimos **7 dias**
- Nos últimos **30 dias**
- Nos últimos **90 dias**

> Não há faixa customizada, nem data inicial/final.

---

## 4. Modelos de planos automatizados

Aba *Gerenciar planos de divulgação* → **Modelos de planos automatizados** · marcado **"Sem limite de cota"**.

| Plano | Descrição na tela | Status |
|---|---|---|
| **Promover eventos de LIVE** | "Lembretes de eventos de LIVE para gerar visitas à LIVE e manter seus usuários ativos." | 🔴 **não criado** (botão *Criar plano*) |
| **Lembrete para iniciar LIVE** | "Envie uma mensagem para clientes em potencial quando você iniciar uma LIVE" — marcado **"Conversão alta"** | 🔴 **não criado** (botão *Criar plano*) |
| **Receber lembretes sobre reduções de preço** | "Destacar reduções de preço para trazer compradores de volta e incentivá-los a concluir a compra." | 🟢 Em andamento desde **08/10/2026** — sem data de encerramento |
| **Recuperar carrinhos abandonados** | "Recuperar vendas perdidas lembrando os clientes dos itens deixados no carrinho." | 🟢 Em andamento desde **01/14/2026** — sem data de encerramento |
| **Recuperar finalizações de compra incompletas** | "Reengajar clientes que pararam na etapa de finalização da compra com um lembrete amigável." | 🟢 Em andamento desde **01/14/2026** — sem data de encerramento |
| **Agradecimento pós-compra** | "Conquistar lealdade agradecendo aos clientes após cada compra." | 🟢 Em andamento desde **01/14/2026** — sem data de encerramento |

> Datas no formato americano (MM/DD/AAAA) como aparecem na tela:
> `01/14/2026` = 14 de janeiro de 2026 · `08/10/2026` = 10 de agosto de 2026.

---

## 5. Notas de funcionamento

- **Canal de entrega = IM** (mensagem direta dentro do TikTok). A URL traz `plan_channel=im`
  e as abas são de *planos de chat* / *planos de divulgação*.
- **Mínimo de 3 condições** recomendado pela própria tela para cada segmento.
- **Tamanho estimado** aparece antes de salvar.
- Os resultados são **refinados por algoritmo do TikTok** — o segmento não é um filtro literal.
- Estado atual da conta: **6 segmentos Padrão · 0 Personalizados** ("Ainda não há segmentos criados").

---

## 6. Ainda não capturado
- Operadores de cada condição (faixa, contagem, maior/menor, negação/exclusão)
- Existe conector **E / OU** entre condições?
- Conteúdo dos **6 segmentos "Padrão"**
- Métricas de desempenho dos 4 planos automatizados já em andamento
