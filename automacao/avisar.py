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
