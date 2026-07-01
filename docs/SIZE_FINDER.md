# Rhode Size Finder — recomendador de tamanho

Função **pura / stateless**: entra medida do corpo (ou peso + altura), sai o
tamanho + metadados de caimento. Sem estado, sem DB, sem segredo — serve tanto
o **webview do link da bio** quanto o **modo operador** usado na live.

Modelagem no MVP: **Wide Leg**. Arquitetura preparada pra multi-modelagem.

## Arquivos

| Arquivo | Papel |
|---|---|
| [`rhode-vercel/public/size-finder.js`](../rhode-vercel/public/size-finder.js) | **Motor** (UMD, fonte de verdade). Browser: `window.RhodeSizeFinder`; Node/endpoint: `module.exports`. |
| [`rhode-vercel/api/size.js`](../rhode-vercel/api/size.js) | Endpoint stateless — wrapper fino sobre o motor. `GET/POST /api/size`. |
| [`rhode-vercel/public/tamanho.html`](../rhode-vercel/public/tamanho.html) | Página operador/demo (rota `/tamanho`). Usa o motor client-side, resposta instantânea. |
| [`rhode-vercel/test/size-finder.test.js`](../rhode-vercel/test/size-finder.test.js) | Suite zero-dependência. Rodar: `node rhode-vercel/test/size-finder.test.js`. |

## API do motor

```js
const SF = require('./size-finder.js');          // ou window.RhodeSizeFinder

SF.recommend(waistCm, hipCm, preference, model)   // Modo A (por medidas)
SF.quickEstimate(weightKg, heightCm, preference, model) // Modo B (rápido)
SF.recommendAll(waistCm, hipCm, preference)       // roda em todas as modelagens populadas
SF.CHARTS, SF.RANGES, SF.DEFAULT_MODEL, SF.populatedModels(), SF.parseNum(v)
```

- `preference` ∈ `corpo` (default) | `solta`.
- `model` default `wide_leg`.
- **Único campo obrigatório do Modo A:** `waistCm`. `hipCm` é opcional (melhora a precisão).
- Aceita vírgula **ou** ponto como decimal. Fora dos ranges de sanidade → `{ error: { type:'input', field, message } }`.

## Endpoint

```
GET  /api/size?waistCm=70&hipCm=98&preference=corpo
GET  /api/size?weightKg=62&heightCm=165           # vira modo rápido automático
GET  /api/size?waistCm=74&all=1                    # todas as modelagens
POST /api/size  { waistCm, hipCm, preference, model }
```
Erro de input → **HTTP 422**. CORS liberado (dado público, stateless). `Cache-Control: no-store`.

## Contrato de saída

Ver seção 8 da spec. Resumo:

- **Modo A:** `mode, model, recommendedSize, fit{waistEaseCm,hipEaseCm,preference}, confidence, flags[], messages[{level,text}], summary, garment{size,waist,hip,length}, input`.
- **Modo B:** `mode, model, recommendedRange[min,max], confidence:'estimativa', estimated{waistCm,hipCm,bmi}, input, note`.
- `flags` são pra **máquina** (chaves estáveis); `messages` são pra **tela**. A UI decide o que mostrar a partir das flags.
- `confidence` ∈ `alta` | `media` | `consultar` | `estimativa`.
- Comprimento (`length`) é constante = **110 cm** em todo o Wide Leg.

## Premissa de caimento (100% algodão, sem elastano)

- Cintura da peça é o **teto** (precisa `>=` cintura do corpo pra fechar; ideal o mais próximo por cima).
- Quadril da peça um pouco maior que o do corpo (folga `hipEaseMin`, default 2 cm).
- Tamanho final = **o menor tamanho que satisfaz cintura E quadril**. Preferência `solta` sobe um número.

## Multi-modelagem

Adicionar cada modelagem em `CHARTS` com sua própria `sizes` e seu próprio `fit`
(as constantes `hipEaseMin`/`soltaStep` **podem variar por corte**). `recommendAll`
já roda em todas as populadas — nenhuma outra parte da lógica muda.

## Pendências (fora do dev)

1. **Confirmar/corrigir `waist` do 38: 74 → 72.** Está fora da progressão (68→72→76→80…).
   Mantido o valor oficial (74) até confirmação; se confirmado o erro, trocar 1 linha em `size-finder.js`.
2. Enviar as grades de **Mom, Baggy e Chocolate**.
3. Definir se vamos **logar `recomendação → compra → devolução`** (calibra a heurística do Modo B e alimenta o Creator Hub).

## Quirk conhecido (documentado)

A flag **`hipTight`** existe no motor (fiel à spec) mas é **estruturalmente
inalcançável** com a lógica de seleção atual: sempre que uma peça cobre o
quadril sem estourar a grade, a folga é `>= hipEaseMin` por construção; quando
não cobre, cai em `hipOver → consultar`. A suite testa isso por varredura. Se um
dia quiser que `hipTight` dispare, recalibrar `hipEaseMin` ou a regra da flag.
