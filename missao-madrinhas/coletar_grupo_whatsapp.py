#!/usr/bin/env python3
"""
Missão das Madrinhas — COLETOR DE PARTICIPANTES DO GRUPO (WhatsApp Web via Chrome logado).

Lê a lista de participantes direto da aba do WhatsApp Web aberta no seu Chrome,
rolando a lista (o WhatsApp virtualiza: só o que está visível existe no DOM).
Salva os telefones num .txt pronto pro relatorio_grupo.py.

━━━ ANTES DE RODAR (3 coisas) ━━━
 1. Chrome aberto em https://web.whatsapp.com (logado).
 2. Abra o GRUPO → clique no nome do grupo (dados do grupo) → role até a lista de
    participantes. Deixe ESSA aba como a aba ATIVA da janela da frente.
 3. No Chrome: menu "Visualizar" → "Desenvolvedor" → marque
    "Permitir JavaScript de eventos do Apple" (Allow JavaScript from Apple Events).
    (Na 1ª vez o macOS também pede permissão de Automação pro Terminal.)

━━━ USO ━━━
  python3 missao-madrinhas/coletar_grupo_whatsapp.py
  # depois:
  python3 missao-madrinhas/relatorio_grupo.py --participantes missao-madrinhas/grupo_participantes.txt \
      --respostas respostas.csv

⚠️ Limitação: contato SALVO na sua agenda aparece com NOME (sem número) no WhatsApp Web —
   esse não é capturado. Convidadas (desconhecidas) aparecem com número, que é o que importa.
"""
import subprocess, re, sys, os, time, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA_PADRAO = os.path.join(ROOT, 'missao-madrinhas', 'grupo_participantes.txt')

# JS de um passo: coleta os telefones visíveis e rola um pouco. Tudo em aspas simples.
JS_STEP = (
    "(function(){"
    "var W=window,cs=[].slice.call(document.querySelectorAll('div')).filter(function(d){"
    "var r=d.getBoundingClientRect();"
    "return d.scrollHeight>d.clientHeight+40&&d.clientHeight>180&&r.width>220&&r.left>W.innerWidth*0.3;});"
    "if(!cs.length)return 'NOCONTAINER';"
    "cs.sort(function(a,b){return b.scrollHeight-a.scrollHeight;});"
    "var c=cs[0],t=c.innerText||'';"
    "var m=t.match(/\\+?\\d[\\d \\-().]{8,}\\d/g)||[];"
    "var b=c.scrollTop;c.scrollTop=b+Math.round(c.clientHeight*0.85);"
    "return m.join(';')+'||'+b+'>'+c.scrollTop+'/'+c.scrollHeight;})()"
)

def run_js(js, timeout=30):
    esc = js.replace('\\', '\\\\').replace('"', '\\"')
    scr = f'tell application "Google Chrome" to execute javascript "{esc}" in active tab of window 1'
    try:
        p = subprocess.run(['osascript', '-e', scr], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, 'timeout no osascript'
    if p.returncode != 0:
        return None, (p.stderr or '').strip()
    return p.stdout.strip(), None

def checar_ambiente():
    out, err = run_js('1+1')
    if err or out != '2':
        print('✗ Não consegui executar JS no Chrome.')
        if err: print('  erro:', err[:200])
        print('\n  Verifique:')
        print('   • Chrome aberto (janela da frente).')
        print('   • Menu Visualizar → Desenvolvedor → "Permitir JavaScript de eventos do Apple".')
        print('   • Permissão de Automação (Ajustes → Privacidade → Automação → Terminal → Chrome).')
        sys.exit(1)
    host, _ = run_js('location.host')
    if 'whatsapp' not in (host or '').lower():
        print(f'✗ A aba ativa não é o WhatsApp Web (host: {host or "?"}).')
        print('  Deixe a aba do web.whatsapp.com ativa, com os DADOS DO GRUPO abertos.')
        sys.exit(1)
    print(f'✓ Chrome ok · aba: {host}')

def coletar(max_passos, pausa):
    vistos, ordem = set(), []
    ultimo_scroll, parado = -1, 0
    for i in range(1, max_passos + 1):
        out, err = run_js(JS_STEP)
        if err:
            print('  erro no passo:', err[:160]); break
        if out == 'NOCONTAINER':
            print('✗ Não achei a lista rolável. Abra os DADOS DO GRUPO (clique no nome do grupo)')
            print('  e deixe a lista de participantes visível.'); sys.exit(1)
        tels_txt, _, pos = (out or '').partition('||')
        novos = 0
        for t in [x.strip() for x in tels_txt.split(';') if x.strip()]:
            d = re.sub(r'\D', '', t)
            if len(d) < 10:
                continue
            if d not in vistos:
                vistos.add(d); ordem.append(t.strip()); novos += 1
        antes = pos.split('>')[0] if '>' in pos else ''
        print(f'  passo {i:>3}: +{novos} novos · total {len(ordem)} · scroll {pos}')
        if antes == str(ultimo_scroll):
            parado += 1
            if parado >= 3:
                print('  (fim da lista)'); break
        else:
            parado = 0
        ultimo_scroll = int(antes) if antes.isdigit() else ultimo_scroll
        time.sleep(pausa)
    return ordem

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--saida', default=SAIDA_PADRAO)
    ap.add_argument('--passos', type=int, default=120, help='máx. de rolagens (default 120)')
    ap.add_argument('--pausa', type=float, default=0.35, help='segundos entre rolagens')
    a = ap.parse_args()

    print('Coletor de participantes — WhatsApp Web\n')
    checar_ambiente()
    print('\nRolando a lista e coletando...')
    tels = coletar(a.passos, a.pausa)

    if not tels:
        print('\n✗ Nenhum telefone capturado. Provavelmente a lista de participantes não está aberta,')
        print('  ou todos são contatos salvos (aparecem só com nome).')
        sys.exit(1)

    os.makedirs(os.path.dirname(a.saida), exist_ok=True)
    with open(a.saida, 'w', encoding='utf-8') as f:
        f.write('\n'.join(tels) + '\n')

    print(f'\n✓ {len(tels)} telefones salvos em: {a.saida}')
    print('\nPróximo passo (gera a planilha do relatório):')
    print(f'  python3 missao-madrinhas/relatorio_grupo.py --participantes "{a.saida}" \\')
    print('      --respostas respostas.csv')

if __name__ == '__main__':
    main()
