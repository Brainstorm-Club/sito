#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Il lettore web del Brainstorm Club — pezzi condivisi.

Una sola implementazione della pagina di lettura, usata da:
  • sito/build_leggi.py      i libri delle collane (sito/leggi/)
  • impaginatore/impagina.sh i fascicoli: avventure e manuali del tavolo

Gli stili e il comportamento stanno in sito/leggi/lettore.css e lettore.js:
le pagine dei libri li collegano, i fascicoli — che viaggiano da soli — se li
incorporano (vedi `stile_incorporato`). Qui c'è solo ciò che costruisce la
pagina attorno al testo: testata, briciole di pane, indice, ritocchi all'HTML
di pandoc.
"""

import html
import json
import os
import re

DOMINIO = "https://www.brainstormclub.it"
QUI = os.path.dirname(os.path.abspath(__file__))

def indice(corpo, livelli="23"):
    """Voci d'indice dagli h1/h2, saltando le note in coda."""
    voci = []
    for m in re.finditer(r'<h([%s]) id="([^"]+)"[^>]*>(.*?)</h\1>' % livelli, corpo, re.S):
        livello, ancora, testo = int(m.group(1)) - int(livelli[0]) + 1, m.group(2), m.group(3)
        testo = re.sub(r'<[^>]+>', '', testo).strip()
        if not testo:
            continue
        voci.append((livello, ancora, testo))
    return voci



def abbassa_titoli(corpo, solo_h1=False):
    """Il titolo della pagina è l'unico h1, quindi il testo scende di un livello.
    Nelle pagine dei singoli racconti il titolo è già stato tolto dal corpo: lì
    basta abbassare gli h1 rimasti (il colofone), altrimenti si salterebbe da
    h1 a h3 — un buco che gli screen reader segnalano."""
    for liv in ((1,) if solo_h1 else (5, 4, 3, 2, 1)):
        corpo = re.sub(r'<(/?)h%d\b' % liv, r'<\g<1>h%d' % (liv + 1), corpo)
    return corpo



def intestazioni_tabelle(corpo):
    return corpo.replace("<th ", '<th scope="col" ').replace("<th>", '<th scope="col">')



def titolo_note(corpo):
    """pandoc apre le note in coda con un <hr /> e nessun titolo: gli diamo un
    titolo vero, così entra nella gerarchia che legge uno screen reader. La
    sostituzione è ancorata alla sezione: nel testo ci sono altri <hr />."""
    return re.sub(r'(<section id="footnotes"[^>]*)(>)\s*<hr\s*/?>',
                  r'\1 aria-labelledby="titolo-note"\2<h2 id="titolo-note" class="note-tit">Note</h2>',
                  corpo, count=1)



def tabelle_scorrevoli(corpo):
    return re.sub(r'<table\b', '<div class="tabellone"><table', corpo).replace("</table>", "</table></div>")



def tempo_di_lettura(markdown):
    parole = len(re.findall(r"[\w'’]+", markdown))
    return max(1, round(parole / 220.0)), parole



def peso(percorso):
    b = os.path.getsize(percorso)
    return (("%.1f MB" % (b / 1048576.0)).replace(".", ",")) if b >= 1048576 else ("%d KB" % round(b / 1024.0))



def per_snippet(t, limite=155):
    """La sinossi intera resta sulla pagina; nel <meta> va la versione che i
    motori mostrano davvero, tagliata a fine frase o a fine parola."""
    t = t.strip()
    if len(t) <= limite:
        return t
    taglio = t[:limite]
    for fine in (". ", "; ", " — ", ", "):
        if fine in taglio:
            testa = taglio.rsplit(fine, 1)[0]
            if len(testa) > limite * 0.6:
                return testa + ("." if fine.startswith(".") else "…")
    return taglio.rsplit(" ", 1)[0] + "…"



def e(t):
    return html.escape(t, quote=True)



def versione(nome):
    """?v=<mtime> su CSS e JS: dopo un caricamento FTP i browser che hanno la
    vecchia versione in cache prendono comunque quella nuova."""
    p = os.path.join(QUI, "leggi", nome)
    return "%s?v=%d" % (nome, int(os.path.getmtime(p))) if os.path.exists(p) else nome



TESTA_TEMA = (
    '<script>document.documentElement.className+=" js";'
    "try{var p=localStorage.getItem('bsc-theme-pref')||localStorage.getItem('bsc-theme')||'dark',"
    "x=p==='auto'?(matchMedia('(prefers-color-scheme: light)').matches?'light':'dark'):p,"
    "d=document.documentElement;d.setAttribute('data-theme',x);d.setAttribute('data-theme-pref',p);"
    "var s=localStorage.getItem('bsc-read-size');if(s)d.setAttribute('data-read-size',s);"
    "var m=document.querySelector('meta[name=theme-color]')}catch(e){}</script>"
)

FONT = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=Courier+Prime:ital,wght@0,400;0,700;1,400'
        '&family=Atkinson+Hyperlegible:wght@400;700&display=swap" rel="stylesheet">')

ICONA_TEMA = (
    '<svg class="bsc-tt-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">'
    '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/></svg>'
    '<svg class="bsc-tt-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">'
    '<circle cx="12" cy="12" r="5" stroke-width="2"/><path stroke-linecap="round" stroke-width="2" '
    'd="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>'
    '<svg class="bsc-tt-auto" viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">'
    '<circle cx="12" cy="12" r="9" stroke-width="2"/><path d="M12 3a9 9 0 0 0 0 18z" fill="currentColor" stroke="none"/></svg>'
)



def testa(titolo, descrizione, url, immagine, css_rel):
    return """<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{tema}
<title>{titolo}</title>
<meta name="description" content="{descr}">
<meta name="robots" content="index, follow">
<meta name="theme-color" content="#181617">
<meta name="author" content="Brainstorm Club — Associazione Ludica Faentina">
<link rel="canonical" href="{url}">
<link rel="apple-touch-icon" href="{css_rel}../assets/favicon.png">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Brainstorm Club">
<meta property="og:locale" content="it_IT">
<meta property="og:url" content="{url}">
<meta property="og:title" content="{titolo}">
<meta property="og:description" content="{descr}">
<meta property="og:image" content="{img}">
<meta name="twitter:card" content="summary_large_image">
{font}
<link rel="stylesheet" href="{css_rel}{css_file}">
</head>
""".format(tema=TESTA_TEMA, titolo=e(titolo), descr=e(per_snippet(descrizione)), url=e(url),
           img=e(immagine), font=FONT, css_rel=css_rel, css_file=versione("lettore.css"))



def barra(briciole, con_indice):
    """briciole = [(testo, href|None)] — l'ultima, senza href, è la pagina corrente.
    `.mid` e `.qui` servono al CSS per accorciare il percorso sugli schermi stretti."""
    voci = []
    for i, (testo, href) in enumerate(briciole):
        ultima = i == len(briciole) - 1
        classe = "qui" if ultima else ("radice" if i == 0 else "mid")
        if href:
            marchio = ('<span aria-hidden="true">‹</span> <span class="nome"><b>Brainstorm</b> Club</span>'
                       if i == 0 else e(testo))
            voci.append('<li class="%s"><a href="%s">%s</a></li>' % (classe, e(href), marchio))
        else:
            voci.append('<li class="%s"><span aria-current="page">%s</span></li>' % (classe, e(testo)))
    bottone_indice = ('<button class="btn-i" id="tocBtn" type="button" aria-expanded="false" '
                      'aria-controls="toc">Indice</button>') if con_indice else ""
    corta = " corta" if len(briciole) <= 2 else ""   # radice + pagina: non c'è niente da accorciare
    return """<div class="progress" aria-hidden="true"><i></i></div>
<header class="bar">
  <nav class="briciole{corta}" aria-label="Percorso"><ol>{voci}</ol></nav>
  <div class="tools">
    {toc}
    <button class="btn-i" id="sizeBtn" type="button" aria-label="Dimensione del testo"><span class="sz-l" aria-hidden="true">A</span><span class="sz-s" aria-hidden="true">a</span></button>
    <button class="btn-i" id="themeBtn" type="button" aria-label="Tema">{icona}</button>
  </div>
</header>
""".format(voci="".join(voci), toc=bottone_indice, icona=ICONA_TEMA, corta=corta)


# --------------------------------------------------------------------------
# Per chi la pagina se la porta via (i fascicoli): stile e script incorporati
# --------------------------------------------------------------------------
def stile_incorporato(dove=None):
    dove = dove or os.path.join(QUI, "leggi")
    css = open(os.path.join(dove, "lettore.css"), encoding="utf-8").read()
    js = open(os.path.join(dove, "lettore.js"), encoding="utf-8").read()
    return "<style>\n%s\n</style>" % css, "<script>\n%s\n</script>" % js


def guscio(slug, briciole, toc, apertura, corpo, coda_pagina, piede, con_indice=True):
    """Il corpo della pagina, uguale per libri e fascicoli."""
    return (
        '<body data-slug="%s">\n' % e(slug)
        + '<a class="skip" href="#testo">Vai al testo</a>\n'
        + barra(briciole, con_indice)
        + '<div class="wrap"><div class="reading">\n'
        + toc + "\n<main>\n<article>\n" + apertura
        + '<div class="testo" id="testo">\n' + corpo + '\n</div>\n'
        + '<div class="coda">\n' + coda_pagina + '</div>\n</article>\n</main>\n'
        + piede
        + '</div></div>\n'
        + '<div class="resume" aria-live="polite" hidden><span>Eri arrivato al <span class="q">—</span></span>'
          '<button class="go" type="button">riprendi</button>'
          '<button class="no" type="button" aria-label="Ricomincia da capo">✕</button></div>\n'
        + '<aside class="nota" aria-label="Nota a piè di pagina" aria-live="polite">'
          '<button class="x" type="button" aria-label="Chiudi la nota">✕</button>'
          '<span class="n"></span><div class="corpo"></div></aside>\n'
    )


# --------------------------------------------------------------------------
# Dati strutturati
# --------------------------------------------------------------------------
# Un'entità sola per il club, dichiarata sulla home e RICHIAMATA per @id da ogni
# altra pagina: i motori generativi che leggono il sito ricostruiscono un grafo,
# non cinquanta copie della stessa stringa «Brainstorm Club».
CLUB = DOMINIO + "/#organizzazione"


def dati_strutturati(*blocchi):
    """Un solo <script> con il grafo della pagina: meno rumore da leggere."""
    grafo = [b for b in blocchi if b]
    if not grafo:
        return ""
    dati = {"@context": "https://schema.org", "@graph": grafo}
    return ('<script type="application/ld+json">%s</script>'
            % json.dumps(dati, ensure_ascii=False, separators=(",", ":")))


def briciole_ld(voci):
    """voci = [(nome, url)] dalla radice alla pagina corrente."""
    return {"@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i, "name": n, "item": u}
                                for i, (n, u) in enumerate(voci, start=1)]}


def durata_iso(minuti):
    """«PT1H52M»: il tempo di lettura in un formato che una macchina sa confrontare."""
    if not minuti:
        return None
    ore, resto = divmod(int(minuti), 60)
    return "PT" + ("%dH" % ore if ore else "") + ("%dM" % resto if resto or not ore else "")


def opera(tipo, titolo, url, descrizione, immagine=None, **extra):
    """Lo scheletro comune a libri, racconti e fascicoli."""
    d = {
        "@type": tipo,
        "@id": url + "#opera",
        "name": titolo,
        "headline": titolo,
        "url": url,
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "inLanguage": "it-IT",
        "isAccessibleForFree": True,
        "publisher": {"@id": CLUB},
        "copyrightHolder": {"@id": CLUB},
    }
    if descrizione:
        d["description"] = descrizione
    if immagine:
        d["image"] = immagine
    d.update({k: v for k, v in extra.items() if v not in (None, "", [], {})})
    return d


def club_minimo():
    """Il riferimento all'entità del club: la scheda intera sta sulla home."""
    return {"@type": "Organization", "@id": CLUB, "name": "Brainstorm Club",
            "url": DOMINIO + "/"}


def gioco(sistema, editore, editore_url=None):
    """Il gioco da cui nasce il testo: serve a rispondere a «di cosa parla»."""
    if not sistema:
        return None
    d = {"@type": "CreativeWork", "name": sistema, "genre": "gioco di ruolo"}
    if editore:
        d["publisher"] = {"@type": "Organization", "name": editore}
    if editore_url:
        d["url"] = editore_url
    return d
