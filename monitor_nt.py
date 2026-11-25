#!/usr/bin/env python3
"""
Monitor de Notas Técnicas da NF-e -> Telegram

Uso:
    pip install requests beautifulsoup4
    export TELEGRAM_TOKEN="123456:ABC..."     # token do @BotFather
    export TELEGRAM_CHAT_ID="123456789"       # seu chat id (veja o README abaixo)
    export TELEGRAM_THREAD_ID="5"             # id do tópico caso queira enviar para um tópico especifico.
    python monitor_nt.py              # fica rodando e checando a cada INTERVALO
    python monitor_nt.py --uma-vez    # checa uma vez só (bom para cron)
    python monitor_nt.py --teste      # mostra o que o script enxerga na página
"""
import os
import sys
import json
import time
import logging
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

URL = "https://www.nfe.fazenda.gov.br/portal/listaConteudo.aspx?tipoConteudo=04BIflQt1aY="
INTERVALO = 240 * 60          # segundos entre checagens # verificação a cada 4 horas, ajuste conforme necessidade.
ESTADO = Path(__file__).resolve().parent / "estado_nt.json"
TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
THREAD_ID = os.environ.get("TELEGRAM_THREAD_ID", "")

# O site da Fazenda às vezes tem problema na cadeia de certificados (ICP-Brasil).
# Se der erro de SSL, mude para False (menos seguro) ou instale a cadeia correta.
VERIFICAR_SSL = True

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("monitor_nt")
sessao = requests.Session()
sessao.headers.update(HEADERS)


# ---------------------------------------------------------------- página
def baixar(url, **kw):
    r = sessao.get(url, timeout=60, verify=VERIFICAR_SSL, **kw)
    r.raise_for_status()
    return r


def extrair_itens(html, base):
    """Retorna dict {href_absoluto: texto} com os links de conteúdo da lista."""
    soup = BeautifulSoup(html, "html.parser")
    itens = {}
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        texto = " ".join(a.get_text(" ", strip=True).split())
        if not texto or href.startswith(("#", "javascript:", "mailto:")):
            continue
        h = href.lower()
        # Links de conteúdo/arquivo do portal NF-e
        if "exibirarquivo" in h or "visualizaconteudo" in h or "detalheconteudo" in h \
                or h.endswith((".pdf", ".zip", ".xsd", ".doc", ".docx", ".xls", ".xlsx")):
            itens[urljoin(base, href)] = texto
    return itens


def achar_arquivos(url):
    """Dado o link de um item, devolve lista de (nome, bytes) para anexar."""
    r = baixar(url, stream=True)
    ctype = r.headers.get("Content-Type", "").lower()
    if "text/html" not in ctype:
        return [(nome_arquivo(r, url), r.content)]
    # É uma página de detalhe: procura arquivos dentro dela
    soup = BeautifulSoup(r.text, "html.parser")
    arquivos = []
    for a in soup.find_all("a", href=True):
        h = a["href"].lower()
        if "exibirarquivo" in h or h.endswith((".pdf", ".zip", ".xsd", ".docx", ".doc")):
            link = urljoin(url, a["href"])
            try:
                rr = baixar(link)
                if "text/html" not in rr.headers.get("Content-Type", "").lower():
                    arquivos.append((nome_arquivo(rr, link), rr.content))
            except Exception as e:
                log.warning("Falha ao baixar %s: %s", link, e)
    return arquivos


def nome_arquivo(resp, url):
    cd = resp.headers.get("Content-Disposition", "")
    if "filename=" in cd:
        return cd.split("filename=")[-1].strip('"; ')
    nome = url.split("?")[0].rstrip("/").split("/")[-1]
    ctype = resp.headers.get("Content-Type", "")
    if "." not in nome:
        nome += ".pdf" if "pdf" in ctype else ".bin"
    return nome


# -------------------------------------------------------------- telegram
def tg(metodo, **kw):
    r = requests.post(f"https://api.telegram.org/bot{TOKEN}/{metodo}", timeout=120, **kw)
    if not r.ok:
        log.error("Telegram %s: %s", metodo, r.text)
    return r


def enviar_texto(msg):
    dados = {"chat_id": CHAT_ID, "text": msg,
                            "disable_web_page_preview": True}
    if THREAD_ID:
        dados["message_thread_id"] = THREAD_ID
    tg("sendMessage", data=dados)


def enviar_arquivo(nome, conteudo, legenda):
    if len(conteudo) > 50 * 1024 * 1024:
        enviar_texto(f"(arquivo {nome} acima de 50 MB, não enviado)")
        return
    dados = {"chat_id": CHAT_ID, "caption": legenda[:1000]}
    if THREAD_ID:
            dados["message_thread_id"] = THREAD_ID
    tg("sendDocument", data=dados,
       files={"document": (nome, conteudo)})


# ------------------------------------------------------------------ main
def carregar_estado():
    if ESTADO.exists():
        return json.loads(ESTADO.read_text(encoding="utf-8"))
    return None


def salvar_estado(vistos):
    ESTADO.write_text(json.dumps(vistos, ensure_ascii=False, indent=1), encoding="utf-8")


def checar():
    itens = extrair_itens(baixar(URL).text, URL)
    if not itens:
        log.warning("Nenhum item encontrado — a estrutura da página pode ter mudado "
                    "ou o acesso foi bloqueado. Rode com --teste.")
        return
    vistos = carregar_estado()
    if vistos is None:                       # primeira execução: só grava a base
        salvar_estado(itens)
        log.info("Base inicial salva com %d itens (sem notificar).", len(itens))
        return
    novos = {u: t for u, t in itens.items() if u not in vistos}
    for url, titulo in novos.items():
        log.info("Novo: %s", titulo)
        enviar_texto(f"📄 Nova publicação na página de Notas Técnicas (NF-e)\n\n"
                     f"{titulo}\n{url}")
        try:
            for nome, conteudo in achar_arquivos(url):
                enviar_arquivo(nome, conteudo, titulo)
        except Exception as e:
            log.warning("Não consegui anexar arquivo de %s: %s", url, e)
        vistos[url] = titulo
        salvar_estado(vistos)               # grava item a item
    if not novos:
        log.info("Sem novidades (%d itens).", len(itens))
        enviar_texto(f"Sem novas notas técnicas ("f"{len(itens)}" f" itens).")


def teste():
    itens = extrair_itens(baixar(URL).text, URL)
    print(f"{len(itens)} itens encontrados:")
    for u, t in list(itens.items())[:20]:
        print(f" - {t}\n   {u}")


if __name__ == "__main__":
    if "--teste" in sys.argv:
        teste()
        sys.exit()
    if not TOKEN or not CHAT_ID:
        sys.exit("Defina TELEGRAM_TOKEN e TELEGRAM_CHAT_ID.")
    if "--uma-vez" in sys.argv:
        checar()
        sys.exit()
    while True:
        try:
            checar()
        except Exception as e:
            log.error("Erro na checagem: %s", e)
        time.sleep(INTERVALO)
