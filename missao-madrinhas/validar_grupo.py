#!/usr/bin/env python3
"""
Missão das Madrinhas — VALIDAÇÃO DE GRUPO (apuração real).

Cruza as respostas do Form B (telefone + quem convidou) com a lista REAL de
participantes do grupo WhatsApp (via Z-API). Assim você sabe, por madrinha,
quantas convidadas ela trouxe que ESTÃO MESMO no grupo — não só as que
preencheram o formulário.

Regra: válida = registrou no Form B  E  o telefone está no grupo agora.

USO:
  1) Descobrir o ID do grupo (roda uma vez):
       python3 missao-madrinhas/validar_grupo.py --listar-grupos
  2) Exportar as respostas do Form B em CSV
       (na planilha: Arquivo → Fazer download → CSV) e salvar, ex: respostas.csv
  3) Validar:
       python3 missao-madrinhas/validar_grupo.py --grupo <ID_DO_GRUPO> --respostas respostas.csv

Lê ZAPI_INSTANCE / ZAPI_TOKEN / ZAPI_CLIENT_TOKEN do .env (não commita credencial).
"""
import os, re, sys, csv, argparse
from collections import defaultdict
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_env(path):
    env = {}
    if os.path.exists(path):
        for line in open(path, encoding='utf-8'):
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env

ENV = {**load_env(os.path.join(ROOT, '.env')), **os.environ}
INST = ENV.get('ZAPI_INSTANCE'); TOK = ENV.get('ZAPI_TOKEN'); CT = ENV.get('ZAPI_CLIENT_TOKEN')
BASE = f'https://api.z-api.io/instances/{INST}/token/{TOK}'
HDR = {'Client-Token': CT or ''}

def norm(p):
    """Telefone BR -> chave canônica (DDD + 8 últimos dígitos), tolerante a +55 e ao 9º dígito."""
    d = re.sub(r'\D', '', str(p or ''))
    if d.startswith('55') and len(d) >= 12:
        d = d[2:]
    if len(d) < 10:
        return None
    return d[:2] + d[-8:]

def zapi_group(group_id):
    r = requests.get(f'{BASE}/group-metadata/{group_id}', headers=HDR, timeout=40)
    r.raise_for_status()
    data = r.json()
    parts = data.get('participants') or data.get('groupParticipants') or []
    phones = set()
    for p in parts:
        ph = p.get('phone') or p.get('id') if isinstance(p, dict) else p
        n = norm(ph)
        if n:
            phones.add(n)
    return phones, data.get('subject', '(grupo)')

def listar_grupos():
    r = requests.get(f'{BASE}/chats', headers=HDR, timeout=40)
    r.raise_for_status()
    print('ID do grupo'.ljust(30), 'Nome')
    print('-' * 60)
    for c in r.json():
        is_group = c.get('isGroup') or str(c.get('phone', '')).endswith('-group') or str(c.get('phone','')).endswith('@g.us')
        if is_group:
            print(str(c.get('phone', '')).ljust(30), c.get('name') or c.get('subject') or '')
    print('\nUse o ID (coluna esquerda) do grupo RhodeLovers em --grupo.')

def read_responses(path):
    rows = list(csv.reader(open(path, encoding='utf-8-sig')))
    if not rows:
        sys.exit('CSV vazio.')
    head = [h.strip().lower() for h in rows[0]]
    iM = next((i for i, h in enumerate(head) if 'convidou' in h or 'madrinha' in h), None)
    iP = next((i for i, h in enumerate(head) if 'whatsapp' in h or 'telefone' in h or 'phone' in h), None)
    if iM is None or iP is None:
        sys.exit('O CSV precisa das colunas "Quem te convidou" e "Seu WhatsApp".')
    out = []
    for r in rows[1:]:
        if len(r) <= max(iM, iP):
            continue
        madr = (r[iM] or '').strip()
        if madr:
            out.append((madr, norm(r[iP]), (r[iP] or '').strip()))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--grupo', help='ID do grupo (veja --listar-grupos)')
    ap.add_argument('--respostas', help='CSV das respostas do Form B')
    ap.add_argument('--listar-grupos', action='store_true')
    ap.add_argument('--saida', default=os.path.join(ROOT, 'missao-madrinhas', 'validacao_madrinhas.csv'))
    a = ap.parse_args()

    if not (INST and TOK and CT):
        sys.exit('Faltam ZAPI_INSTANCE / ZAPI_TOKEN / ZAPI_CLIENT_TOKEN no .env')
    if a.listar_grupos:
        return listar_grupos()
    if not a.grupo or not a.respostas:
        sys.exit('uso: --grupo <ID> --respostas <arquivo.csv>   (ou --listar-grupos)')

    grupo, nome = zapi_group(a.grupo)
    resp = read_responses(a.respostas)

    reg = defaultdict(list)          # madrinha -> [(chave, telefone_original), ...]
    for madr, key, raw in resp:
        reg[madr].append((key, raw))

    linhas = []
    fora_detalhe = []
    for madr, itens in reg.items():
        vistos = {}
        for key, raw in itens:
            if key and key not in vistos:
                vistos[key] = raw
        validas = [raw for k, raw in vistos.items() if k in grupo]
        fora = [raw for k, raw in vistos.items() if k not in grupo]
        linhas.append((madr, len(itens), len(vistos), len(validas), len(fora)))
        for raw in fora:
            fora_detalhe.append((madr, raw))
    linhas.sort(key=lambda x: -x[3])

    print(f'\nGrupo: {nome} · {len(grupo)} participantes · {len(resp)} registros no Form B\n')
    print(f'{"Madrinha":<26}{"registros":>10}{"únicas":>8}{"VÁLIDAS":>9}{"fora":>6}')
    print('-' * 59)
    for madr, tot, uniq, val, fora in linhas:
        print(f'{madr[:26]:<26}{tot:>10}{uniq:>8}{val:>9}{fora:>6}')
    if linhas:
        campea = max(linhas, key=lambda x: x[3])
        print(f'\n👑 Campeã por VÁLIDAS: {campea[0]} — {campea[3]} convidadas no grupo.')

    with open(a.saida, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Madrinha', 'Registros', 'Telefones únicos', 'Válidas (no grupo)', 'Fora do grupo'])
        for row in linhas:
            w.writerow(row)
        w.writerow([])
        w.writerow(['— Registrou mas NÃO está no grupo (pra cobrar/excluir) —'])
        w.writerow(['Madrinha', 'Telefone'])
        for madr, raw in fora_detalhe:
            w.writerow([madr, raw])
    print(f'\n📄 Detalhe salvo em: {a.saida}')
    print('   "válidas" = telefone registrado que está no grupo agora. Rode no dia 22/07.')

if __name__ == '__main__':
    main()
