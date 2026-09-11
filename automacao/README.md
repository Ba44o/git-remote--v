# Relatório automático de live

A cada 15 minutos o GitHub Actions procura lives que **terminaram há 45+ minutos** e ainda
não têm relatório. Para cada uma: atualiza as fontes, gera o workbook de 8 abas no template
travado e publica na pasta do Drive.

**Pasta:** [Relatorios de Live — Rhode Jeans](https://drive.google.com/drive/folders/1tWpDpY6gpOijpEkw_EpWmylohL8BpRix)

## Peças

| arquivo | o que faz |
|---|---|
| `gerar_relatorio_live.py` | gera o workbook de uma sala. `--room <id>` |
| `monitor_lives.py` | acha o que está pendente, gera e publica |
| `oauth_setup.py` | autorização do Google, uma vez só |
| `.github/workflows/relatorio-live.yml` | o cron de 15 min |
| `lib/receita.py` | base de receita canônica (usada pelo gerador) |

## Estado: a própria pasta do Drive

Cada planilha criada leva o `room_id` em `appProperties`. Listar a pasta já diz o que foi
feito — sem tabela nova, sem DDL, sem arquivo de controle no git.
**Apagou um relatório da pasta? Ele se regenera no próximo ciclo.**

## Por que 45 minutos

Pedidos continuam entrando e mudando de status depois que a live acaba, e a atribuição do
GMV Max leva alguns minutos para assentar. 45 min é o **piso**, não o ideal: medido em
10/09, o status de pagamento ainda se moveu bastante depois disso. Por isso todo relatório
declara o horário da medição e traz o alerta de **remedir os não pagos em 48h**.

## O que o gerador detecta sozinho

Nada de número escrito à mão — lição da auditoria de 11/09, quando textos com valores fixos
envelheceram em silêncio depois de uma recoleta.

- **Hora fora da curva** — a hora com CPA > 2× a média das demais vira a seção "o número que
  explica a live", com contrafactual. Se nenhuma destoa, a aba diz isso.
- **Corte de promoção** — pelo **piso** de preço por produto em faixas de 15 min: se o piso
  sobe e não volta em 2+ produtos ao mesmo tempo, é corte. Mede o antes/depois em peças/min
  e contribuição/min.
- **Furo de grade** — zero **entre** dois tamanhos que vendem.
- **Inversão hero × não-hero** — só aparece se realmente houver inversão de margem.
- **Plano de ação** — montado dos achados e ordenado por R$ em jogo.

## Rodar na mão

```bash
python3 automacao/monitor_lives.py --dry-run          # o que faria
python3 automacao/monitor_lives.py --room <room_id>   # força uma sala
python3 automacao/gerar_relatorio_live.py --room <id> --saida /tmp/x.xlsx
```

No GitHub: aba **Actions** → *Rhode — Relatório automático de live* → **Run workflow**
(aceita `room`, `espera` e `dry_run`).

## ⚠️ Setup obrigatório: OAuth

A service account (`rhode-etl-936@…`) tem **quota ZERO de Drive** — testado em 11/09:
`The user's Drive storage quota has been exceeded`. Ela escreve em planilha que já exista,
mas **não cria nenhuma**. Por isso a automação precisa agir como o dono da conta.

Ver o cabeçalho de `oauth_setup.py` para o passo a passo. Resumo:

1. Criar um *OAuth client ID* tipo **Desktop** no projeto `creators-rhode`, salvar como
   `client_secret.json` na raiz
2. Adicionar o próprio e-mail em **Usuários de teste** da tela de consentimento
   (senão dá `403 access_denied` mesmo sendo o dono)
3. `pip3 install google-auth-oauthlib && python3 automacao/oauth_setup.py`
4. Cadastrar o conteúdo de `token_google.json` como secret **`GOOGLE_OAUTH_TOKEN`** no GitHub

Sem esse secret o workflow falha de propósito, com mensagem explicando — em vez de rodar e
não entregar nada.

### ⚠️ O escopo é `drive.file`, de propósito

Na primeira tentativa pedi `drive` + `spreadsheets` completos e a tela de consentimento
quebrou com **400 malformed** — são escopos *sensíveis*, exigem registro na tela e
verificação do Google.

`drive.file` dá acesso **só aos arquivos que este app criar** — que é exatamente o caso, já
que a automação cria os relatórios. É escopo **não-sensível**: nenhuma configuração extra,
nenhuma verificação. A Sheets API também honra `drive.file` para escrever nesses arquivos.

**Consequência prática:** a automação não enxerga planilhas criadas por fora (pelo conector
ou à mão). Se você criar um relatório manualmente na pasta, o monitor não vai vê-lo e vai
gerar o dele — deixe a pasta para a automação.

## Limites conhecidos

- **Atribuição por SKU é por JANELA DE TEMPO**, não por `room_id` — nenhuma fonte liga pedido
  a sala no nível de SKU. Cada relatório declara o tamanho do viés.
- **Sem funil**: impressões, CTR, CTOR, ATC, CPM, CPC e PCU não existem na API (testado).
  Só `live_views`. Retenção só via export manual do Seller Center.
- **Sem log de alterações**: 11 endpoints testados, todos 404. `modify_time` não serve —
  registra varredura do TikTok, não ação humana.
- **Granularidade mínima é 1 hora** (`stat_time_hour`). 15 min não existe.
