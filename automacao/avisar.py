#!/usr/bin/env python3
"""
Rhode — aviso por e-mail quando sai relatório novo de live.

Manda pela Gmail API usando a MESMA autorização OAuth do Drive (escopo gmail.send),
então não precisa de senha de app, SMTP nem serviço de terceiro. O e-mail sai da
própria conta do dono.

Se o token não tiver o escopo gmail.send, avisa e segue em frente — publicar o
relatório é o que importa; o e-mail é acessório e nunca deve derrubar o job.
"""
import os, sys, base64, json
from email.message import EmailMessage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTINO = os.environ.get("EMAIL_AVISO", "humbertobasso9@gmail.com")
SCOPE_MAIL = "https://www.googleapis.com/auth/gmail.send"


def _cred():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "pubdrive", os.path.join(ROOT, "relatorios", "_publicar_drive.py"))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod.obter_credenciais()


def tem_escopo_email(cred=None):
    cred = cred or _cred()
    return SCOPE_MAIL in (getattr(cred, "scopes", None) or [])


def _corpo_html(d):
    """d: dict com o resumo da live. Só fatos — o julgamento está no relatório."""
    def br(v, n=2):
        return f"{v:,.{n}f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")
    cor = "#0E9F6E" if d["res"] > 0 else "#FE2C55"
    sinal = "pagou" if d["res"] > 0 else "deu prejuízo"
    alertas = ""
    if d.get("pico"):
        alertas += (f'<li>Hora fora da curva: <b>{d["pico"]["h"]:02d}:00</b> consumiu '
                    f'R$ {br(d["pico"]["c"])} ({d["pico"]["share"]*100:.0f}% da mídia) '
                    f'a um CPA de R$ {br(d["pico"]["cpa"])} contra R$ {br(d["pico"]["cpa_base"])} nas demais.</li>')
    if d.get("corte"):
        alertas += (f'<li>Promoção cortada ≈<b>{d["corte"]["quando"]}</b> — velocidade caiu de '
                    f'{d["corte"]["pm_antes"]:.2f} para {d["corte"]["pm_depois"]:.2f} peças/min.</li>')
    if d.get("furos"):
        alertas += f'<li>Furo de grade em <b>{d["furos"]}</b> dos produtos mais vendidos.</li>'
    if d.get("unpaid_pecas"):
        alertas += (f'<li><b>{d["unpaid_pecas"]} peças não pagas</b> seguram '
                    f'R$ {br(d["unpaid_contrib"])} de contribuição.</li>')
    bloco = f"<p><b>O que o relatório aponta:</b></p><ul>{alertas}</ul>" if alertas else \
            "<p>Nenhum problema material detectado nesta live.</p>"
    return f"""<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:560px;color:#1A1A1E">
<p style="margin:0 0 4px"><b style="font-size:17px">Relatório novo: live de {d['quando']}</b></p>
<p style="margin:0 0 16px;color:#6B6B76;font-size:13px">{d['titulo']}</p>
<table style="border-collapse:collapse;font-size:14px;width:100%">
<tr><td style="padding:6px 0;color:#6B6B76">Receita de lista</td><td style="text-align:right"><b>R$ {br(d['rev'])}</b></td></tr>
<tr><td style="padding:6px 0;color:#6B6B76">Peças pagas</td><td style="text-align:right"><b>{d['qty']}</b></td></tr>
<tr><td style="padding:6px 0;color:#6B6B76">Mídia</td><td style="text-align:right">R$ {br(d['ads'])}</td></tr>
<tr><td style="padding:6px 0;color:#6B6B76">Contribuição</td><td style="text-align:right">R$ {br(d['contrib'])}</td></tr>
<tr style="border-top:1px solid #EFEFF2"><td style="padding:10px 0"><b>Resultado</b></td>
<td style="text-align:right"><b style="color:{cor};font-size:16px">R$ {br(d['res'])}</b></td></tr>
</table>
<p style="font-size:13px;color:#6B6B76;margin:4px 0 16px">A live {sinal} — R$ {br(d['res']/d['dur'])} por hora no ar.</p>
{bloco}
<p style="margin:22px 0"><a href="{d['url']}" style="background:#FE2C55;color:#fff;padding:11px 20px;
border-radius:7px;text-decoration:none;font-weight:600;font-size:14px">Abrir o relatório</a></p>
<p style="font-size:12px;color:#9A9AA5;margin-top:22px;border-top:1px solid #EFEFF2;padding-top:12px">
Gerado automaticamente 45 min após o fim da live ·
<a href="https://drive.google.com/drive/folders/{os.environ.get('DRIVE_FOLDER_ID','1tWpDpY6gpOijpEkw_EpWmylohL8BpRix')}"
style="color:#6B6B76">ver todos na pasta</a><br>
Os pedidos não pagos ainda podem mudar de status — vale remedir em 48h.</p></div>"""


def avisar(d):
    """Manda o aviso. Nunca levanta exceção — retorna True/False."""
    try:
        cred = _cred()
        if not tem_escopo_email(cred):
            print("  ⚠ token sem escopo gmail.send — e-mail não enviado "
                  "(rode automacao/oauth_setup.py para reautorizar)")
            return False
        from googleapiclient.discovery import build
        msg = EmailMessage()
        msg["To"] = DESTINO
        msg["Subject"] = f"Relatório da live de {d['quando']} — resultado R$ {d['res']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        msg.set_content(f"Relatório novo da live de {d['quando']}.\n\n"
                        f"Resultado: R$ {d['res']:,.2f}\nPeças: {d['qty']}\n\n{d['url']}")
        msg.add_alternative(_corpo_html(d), subtype="html")
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        build("gmail", "v1", credentials=cred).users().messages().send(
            userId="me", body={"raw": raw}).execute()
        print(f"  ✉ aviso enviado para {DESTINO}")
        return True
    except Exception as e:
        print(f"  ⚠ e-mail falhou (o relatório está publicado): {str(e)[:160]}")
        return False


if __name__ == "__main__":
    print("escopo gmail.send presente:", tem_escopo_email())


# ───────── aviso do relatório DIÁRIO DA LOJA ─────────
def _corpo_loja(D, url):
    def br(v, n=2):
        if v is None: return "sem dado"
        return f"{v:,.{n}f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")
    r_ = D["rec"]; ra = D["rec_ant"]; lv = D["live"]; ads = D["ads"]; cr = D["creators"]
    from datetime import datetime
    dt = datetime.strptime(D["dia"], "%Y-%m-%d")
    liq = r_["contrib"] - (ads["total"]["custo"] if ads else 0)
    cor = "#0E9F6E" if liq > 0 else "#FE2C55"
    peso = (lv["gmv"] / r_["lista"] * 100) if r_["lista"] else 0
    def dl(a, b):
        if a is None or not b: return ""
        v = (a / b - 1) * 100
        c = "#0E9F6E" if v >= 0 else "#FE2C55"
        return f'<span style="color:{c};font-size:12px"> {br(v,1)}%</span>'
    linhas = "".join(
        f'<tr><td style="padding:6px 0;color:#6B6B76">{k}</td>'
        f'<td style="text-align:right"><b>{p}{br(v)}</b>{d}</td></tr>'
        for k, v, p, d in [
            ("Receita de lista", r_["lista"], "R$ ", dl(r_["lista"], ra["lista"] if ra else None)),
            ("Peças pagas", r_["pecas"], "", dl(r_["pecas"], ra["pecas"] if ra else None)),
            ("Pedidos", r_["pedidos"], "", dl(r_["pedidos"], ra["pedidos"] if ra else None)),
            ("AOV por pedido", r_["aov_lista"], "R$ ", dl(r_["aov_lista"], ra["aov_lista"] if ra else None)),
            ("Mídia", ads["total"]["custo"] if ads else None, "R$ ", ""),
            ("Contribuição bruta", r_["contrib"], "R$ ", dl(r_["contrib"], ra["contrib"] if ra else None)),
        ])
    extras = []
    if lv["n"]:
        extras.append(f"Live: R$ {br(lv['gmv'])} ({br(peso,1)}% do total) em {lv['n']} transmissão(ões).")
    else:
        extras.append("Sem live neste dia.")
    if cr:
        extras.append(f"{cr['n_creators']} creators com venda · GMV de afiliadas R$ {br(cr['gmv'])}.")
    if r_["nao_virou"]:
        extras.append(f"<b>{r_['nao_virou']} peças ({br(r_['nao_virou_pct']*100,1)}%) não viraram receita.</b>")
    return f"""<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:560px;color:#1A1A1E">
<p style="margin:0 0 4px"><b style="font-size:17px">Relatório da loja — {dt.strftime('%d/%m/%Y')}</b></p>
<p style="margin:0 0 16px;color:#6B6B76;font-size:13px">Comparado com {D['anterior']}</p>
<table style="border-collapse:collapse;font-size:14px;width:100%">{linhas}
<tr style="border-top:1px solid #EFEFF2"><td style="padding:10px 0"><b>Contribuição após mídia</b></td>
<td style="text-align:right"><b style="color:{cor};font-size:16px">R$ {br(liq)}</b></td></tr>
</table>
<p style="font-size:13px;color:#6B6B76;margin:10px 0 16px">{"<br>".join(extras)}</p>
<p style="margin:22px 0"><a href="{url}" style="background:#FE2C55;color:#fff;padding:11px 20px;
border-radius:7px;text-decoration:none;font-weight:600;font-size:14px">Abrir o relatório</a></p>
<p style="font-size:12px;color:#9A9AA5;margin-top:22px;border-top:1px solid #EFEFF2;padding-top:12px">
Receita de LISTA = pago + cupom subsidiado pelo TikTok · settlement 0,7084 · CPV R$ 45,40.<br>
Conversão, CPM, retenção e pico de audiência não existem em fonte alguma — ver aba Premissas.</p></div>"""


def avisar_loja(D, url):
    """Aviso do relatório diário da loja. Nunca levanta."""
    try:
        cred = _cred()
        if not tem_escopo_email(cred):
            print("  ⚠ token sem escopo gmail.send — e-mail não enviado")
            return False
        from googleapiclient.discovery import build
        from datetime import datetime
        r_ = D["rec"]; ads = D["ads"]
        liq = r_["contrib"] - (ads["total"]["custo"] if ads else 0)
        dt = datetime.strptime(D["dia"], "%Y-%m-%d")
        msg = EmailMessage()
        msg["To"] = DESTINO
        val = f"{liq:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        msg["Subject"] = f"Loja {dt.strftime('%d/%m')} — contribuição após mídia R$ {val}"
        msg.set_content(f"Relatório diário da loja — {dt.strftime('%d/%m/%Y')}\n\n"
                        f"Contribuição após mídia: R$ {val}\n\n{url}")
        msg.add_alternative(_corpo_loja(D, url), subtype="html")
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        build("gmail", "v1", credentials=cred).users().messages().send(
            userId="me", body={"raw": raw}).execute()
        print(f"  ✉ aviso da loja enviado para {DESTINO}")
        return True
    except Exception as e:
        print(f"  ⚠ e-mail falhou (o relatório está publicado): {str(e)[:160]}")
        return False
