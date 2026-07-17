#!/bin/bash
# Deploy da tela de cadastro (madrinhas.html) na Vercel — mission das madrinhas.
# Sobe só o que é novo (madrinhas.html + rota no vercel.json) e ISOLA o hub.html:
# durante o deploy o hub.html volta pra versão já publicada (não sobe edições locais em andamento),
# e suas edições do hub são restauradas no fim.
set -e
ROOT="/Users/user/Documents/VS Claude Teste"
cd "$ROOT"

BK="$(mktemp)"
cp rhode-vercel/public/hub.html "$BK"
restore(){ cp "$BK" rhode-vercel/public/hub.html; echo "✓ hub.html (suas edições locais) restaurado"; }
trap restore EXIT

git show HEAD:rhode-vercel/public/hub.html > rhode-vercel/public/hub.html
echo "→ hub.html na versão publicada só durante o deploy ($(wc -c < rhode-vercel/public/hub.html) bytes)"

cd rhode-vercel
echo "→ subindo pra produção (Vercel)…"
vercel --prod --yes

echo ""
echo "✅ Deploy concluído. Teste:"
echo "   https://creators.rhodejeans.com.br/vira-madrinha                     (madrinha pega o link)"
echo "   https://creators.rhodejeans.com.br/madrinhas?madrinha=Ana%20Souza    (convidada)"
echo "   https://creators.rhodejeans.com.br/dash-madrinhas                    (dash interno do placar)"
