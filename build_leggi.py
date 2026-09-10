#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera la versione web («Leggi online») dei libri del Brainstorm Club.

Stessa fonte degli EPUB — i racconti in <progetto>/racconti/ composti dai
manifest dei volumi — passata per pandoc e impaginata nel lettore del sito
(sito/leggi/lettore.css + lettore.js). Una pagina per volume, con indice dei
capitoli, note a comparsa, avanzamento e ripresa della lettura.

    python3 sito/build_leggi.py                     # tutte le collane registrate
    python3 sito/build_leggi.py dossier-scavengers  # una sola collana

Uscita, per ogni collana:
    sito/leggi/<collana>/index.html        indice della collana
    sito/leggi/<collana>/<volume>.html     un volume per pagina
    sito/leggi/<collana>/<volume>-cover.jpg  miniatura 2:3

Aggiungere una collana = una voce in COLLANE. Il resto è già scritto.
"""

import glob
import html
import os
import re
import subprocess
import sys

from PIL import Image

from lettore import (CLUB, DOMINIO, abbassa_titoli, barra, briciole_ld, club_minimo,
                     dati_strutturati, durata_iso, e, gioco, guscio, indice,
                     intestazioni_tabelle, opera, peso, per_snippet, tabelle_scorrevoli,
                     tempo_di_lettura, testa, titolo_note, versione)

QUI = os.path.dirname(os.path.abspath(__file__))          # …/sito
RADICE = os.path.dirname(QUI)                             # …/brainstorm

# --------------------------------------------------------------------------
# Registro delle collane. `volumi` è in ordine CRONOLOGICO della storia, come
# sul sito; `prefisso` è quello degli slug in sito/libri/.
# --------------------------------------------------------------------------
COLLANE = {
    # --- Brancalonia ---------------------------------------------------------
    "regno-di-taglia": {
        "titolo": "Regno di Taglia",
        "progetto": "brancalonia",
        "schema": "capitoli",          # libri/<nome>/ con epigrafe + NN_*.md
        "prefisso": "",
        "etichetta": "racconto",
        "curatore": "Nanoc Orabrabli",
        "occhiello": (
            "Le sganassate della Cricca nel Regno di Taglia, messe in carta da Nanoc "
            "Orabrabli come le ha sentite raccontare all'osteria: canaglie squattrinate, "
            "lavoretti che si storcono e conti che si pagano sempre due volte."
        ),
        "sistema": "Brancalonia", "editore": "Acheron Games",
        "editore_url": "https://www.acheron.it/brancalonia/",
        "volumi": [
            ("la-rosaspina", "rosaspina"),
            ("il-figlio-del-burattinaio", "burattinaio"),
            ("la-guerra-dei-cinghiali", "cinghiali"),
            ("la-cena-delle-zitellone", "zitellone"),
            ("le-cinque-teste", "5-teste"),
            ("il-grigione", "grigione"),
            ("grosso-guaio-a-castellammare", "castellammare"),
            ("la-rosa-davorio", "rosa-davorio", "extra"),
        ],
    },
    # --- Rogue Trader --------------------------------------------------------
    "ciclo-di-korvaal": {
        "titolo": "Il ciclo di Korvaal",
        "progetto": "roguetrader/ciclo-korvaal",
        "prefisso": "korvaal-",
        "etichetta": "volume",
        "curatore": "",                # ogni volume dichiara la propria voce
        "occhiello": (
            "Il corsaro Korvaal raccontato da chi gli è cresciuto attorno: le sue memorie, "
            "la santa e le sue ancelle, i registri del contabile, le voci dell'equipaggio. "
            "Volumi tematici, una voce per volume, dagli angoli più bui dell'Imperium."
        ),
        "sistema": "Rogue Trader", "editore": "Warhammer 40.000",
        "editore_url": "",
        "conclusa": True,
        # l'omnibus non ha pagina web: ripeterebbe per intero i racconti degli altri
        # quattro volumi, e due URL con lo stesso testo si fanno concorrenza da sole.
        # I volumi sono tematici (una voce ciascuno) ma la storia è una sola:
        # ogni racconto ha la sua pagina e, accanto alla catena del volume, esiste
        # il filo cronologico degli eventi. Fonte: la Timeline della bibbia di serie.
        "cronologia": "assets/canone_serie.md",
        "volumi": [("origini", "origini", "spezza"),
                   ("estarosa", "estarosa", "spezza"),
                   ("cronache", "cronache", "spezza"),
                   ("jen-lo-xenocida", "jen-lo-xenocida", "spezza")],
    },
    # --- Dark Heresy ---------------------------------------------------------
    "acta-heretica": {
        "titolo": "ACTA HERETICA",
        "progetto": "roguetrader/dark-heresy",
        "prefisso": "dh-",
        "etichetta": "fascicolo",
        "curatore": "a cura del sapiente Eruditus, Ordo Hereticus",
        "occhiello": (
            "Gli atti dell'Ordo Calixis su una cellula di accoliti inquisitoriali: "
            "deposizioni raccolte e messe in ordine dal sapiente Eruditus, dalle miniere "
            "di Sepheris Secundus fino a dove l'ordine non arriva più."
        ),
        "sistema": "Dark Heresy", "editore": "Warhammer 40.000 · Settore Calixis",
        "editore_url": "",
        "volumi": ["miniera", "relitto", "carnevale", "cospirazione", "segreto"],
    },
    # --- D&D 5e, tavolo Under 16 --------------------------------------------
    "tiro-salvezza": {
        "titolo": "Tiro Salvezza",
        "progetto": "dnd-jr",
        "prefisso": "dnd-",
        "etichetta": "numero",
        "curatore": "Ozymandias il Grande",
        "occhiello": (
            "La fanzine della Compagnia del Bottino, battuta a macchina dal loro Master "
            "Ozymandias il Grande: le cerche di un gruppo di giovanissimi nel Vecchio "
            "Mondo, un numero per avventura, con tutte le digressioni del caso."
        ),
        "sistema": "D&D 5ª ed.", "editore": "Wizards of the Coast",
        "editore_url": "https://dnd.wizards.com/",
        "volumi": ["talabec", "torre", "principe", "diplomazia", "invasione"],
    },
    # --- Apocalisse ----------------------------------------------------------
    "terre-desolate": {
        "titolo": "Terre Desolate",
        "progetto": "apocalisse",
        "prefisso": "apoc-",
        "etichetta": "codice",
        "curatore": "a cura dell'Archivista",
        "occhiello": (
            "I «Codici del Silenzio»: quel che l'Archivista ha potuto salvare delle voci "
            "rimaste dopo l'Apocalisse — un appestato, un guerriero, uno scriba — "
            "ricopiate una per una prima che il silenzio se le riprendesse."
        ),
        "sistema": "Apocalisse", "editore": "Acheron",
        "editore_url": "https://www.acheron.it/apocalisse/",
        "volumi": ["appestato", ("ronan", "ronan-di-kimmeria"), "tolomeo"],
    },
    # --- Heroes Unlimited ----------------------------------------------------
    "dossier-scavengers": {
        "titolo": "Dossier Scavengers",
        "progetto": "heroes",
        "prefisso": "hu-",
        "etichetta": "fascicolo",
        "curatore": "a cura dell'Analista",
        "occhiello": (
            "Il fascicolo dei Cavalieri della Corona sulla banda detta «Scavengers»: "
            "deposizioni, referti e ritagli di stampa da una Londra che, dopo l'evento "
            "zero, ha imparato a mettere una taglia sui mostri — e a farsela pagare."
        ),
        "sistema": "Heroes Unlimited", "editore": "Palladium Books",
        "editore_url": "https://www.palladiumbooks.com/",
        "conclusa": True,
        "volumi": ["taglie-di-londra", "la-caccia-ai-cinque", "il-panfilo"],
    },
}


def maiuscola(t):
    """Solo la prima lettera: .capitalize() ridurrebbe «III» a «iii»."""
    return t[:1].upper() + t[1:]


def numero(coll, v):
    """«fascicolo III», «racconto V», «extra fuori continuity»: l'etichetta la
    decide la collana, e gli extra non entrano nella numerazione."""
    if v["extra"]:
        return "extra · fuori continuity"
    return "%s %s" % (coll.get("etichetta", "volume"), ROMANI[v["n"]])


ROMANI = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]


# --------------------------------------------------------------------------
# Fonti
# --------------------------------------------------------------------------
def leggi_meta(percorso):
    """meta.yaml dei volumi: blocco pandoc semplice, chiave: "valore"."""
    dati = {}
    with open(percorso, encoding="utf-8") as f:
        for riga in f:
            riga = riga.rstrip("\n")
            if riga.strip() in ("---", "...", ""):
                continue
            m = re.match(r'^([A-Za-z_-]+):\s*(.*)$', riga)
            if not m:
                continue
            valore = m.group(2).strip()
            if len(valore) >= 2 and valore[0] == valore[-1] and valore[0] in "\"'":
                valore = valore[1:-1]
            dati[m.group(1)] = valore
    return dati


def componi_volumi(progetto, dir_volume):
    """Schema «volumi»: front + timeline + racconti dal manifest (con prefisso-note)
    + colofone. Stessa composizione di build_epub.sh — fonte unica in racconti/."""
    vdir = os.path.join(progetto, "volumi", dir_volume)
    pezzi = []
    for opzionale in ("front.md", "timeline.md"):
        p = os.path.join(vdir, opzionale)
        if os.path.exists(p):
            pezzi.append(open(p, encoding="utf-8").read().strip())

    for riga in open(os.path.join(vdir, "manifest.txt"), encoding="utf-8"):
        riga = riga.strip()
        if not riga or riga.startswith("#"):
            continue
        parti = riga.split()
        nome = parti[0]
        prefisso = parti[1] if len(parti) > 1 else ""
        testo = open(os.path.join(progetto, "racconti", nome + ".md"), encoding="utf-8").read()
        if prefisso:
            testo = re.sub(r'\[\^([0-9A-Za-z]+)\]', lambda m: "[^%s%s]" % (prefisso, m.group(1)), testo)
        pezzi.append(testo.strip())
    return pezzi


def leggi_cronologia(progetto, percorso):
    """La tabella «Timeline» della bibbia di serie: | Anno | Racconto | Voce |.
    È il canone della collana, non una lista da riscrivere qui: il titolo si
    prende dal corsivo (l'ultimo *…* della cella), che è il titolo del racconto."""
    voci = []
    dentro = False
    for riga in open(os.path.join(progetto, percorso), encoding="utf-8"):
        if riga.startswith("## "):
            dentro = riga.lower().startswith("## timeline")
            continue
        if not dentro or not riga.strip().startswith("|"):
            continue
        celle = [c.strip() for c in riga.strip().strip("|").split("|")]
        if len(celle) < 3 or celle[0].lower() == "anno" or set(celle[0]) <= set("-: "):
            continue
        corsivi = re.findall(r'\*([^*]+)\*', celle[1])
        if not corsivi:
            continue
        voci.append({"anno": celle[0], "titolo": raffina(corsivi[-1].strip()), "voce": celle[2]})
    return voci


def leggi_manifest(progetto, dir_volume):
    """[(nome-racconto, prefisso-note)] nell'ordine del manifest."""
    voci = []
    for riga in open(os.path.join(progetto, "volumi", dir_volume, "manifest.txt"), encoding="utf-8"):
        riga = riga.strip()
        if not riga or riga.startswith("#"):
            continue
        parti = riga.split()
        voci.append((parti[0], parti[1] if len(parti) > 1 else ""))
    return voci


def raffina(t):
    """L'apostrofo dritto del sorgente diventa ’ nel corpo (pandoc +smart):
    i titoli vanno raffinati allo stesso modo, o i confronti non combaciano."""
    return t.replace("'", "\u2019").replace("...", "\u2026")


def slugifica(nome_file):
    return re.sub(r'[^a-z0-9]+', '-', nome_file.lower()).strip('-')


def titolo_markdown(md, ripiego):
    m = re.search(r'^#\s+(.+)$', md, re.M)
    return raffina(m.group(1).strip()) if m else ripiego


def descrizione_racconto(front_md, titolo, md):
    """L'indice scritto dal curatore in front.md dà già una riga per racconto:
    «- **Titolo** *(contesto)* — descrizione». Si usa quella; se non c'è, si
    ripiega sul primo capoverso del racconto."""
    for riga in front_md.splitlines():
        m = re.match(r'^\s*[-*]\s+\*\*(.+?)\*\*(.*)$', riga)
        if m and raffina(m.group(1).strip()) == titolo:
            coda = m.group(2)
            coda = re.sub(r'^\s*\*\([^)]*\)\*', '', coda)          # via il contesto fra parentesi
            coda = re.sub(r'^\s*[—–-]\s*', '', coda).strip()
            if coda:
                return raffina(re.sub(r'[*_`]', '', coda))
    for blocco in md.split("\n\n"):
        b = blocco.strip()
        if b and not b.startswith(("#", ">", "-", "*", "**RISERVATO")):
            b = re.sub(r'\[\^[0-9A-Za-z]+\]', '', re.sub(r'[*_`]', '', b)).strip()
            return (b[:180].rsplit(" ", 1)[0] + "…") if len(b) > 180 else b
    return ""


def componi_capitoli(progetto, dir_volume):
    """Schema «capitoli» (Brancalonia): epigrafe + NN_*.md in ordine. Come in
    build_epub.sh le note NON vengono prefissate: i capitoli non le ripetono."""
    ldir = os.path.join(progetto, "libri", dir_volume)
    pezzi = []
    epigrafe = os.path.join(ldir, "epigrafe.md")
    if os.path.exists(epigrafe):
        pezzi.append(open(epigrafe, encoding="utf-8").read().strip())
    capitoli = sorted(f for f in os.listdir(ldir) if re.match(r'^[0-9].*\.md$', f))
    if not capitoli:
        sys.exit("nessun capitolo NN_*.md in %s: il testo sorgente non c'è" % ldir)
    for f in capitoli:
        pezzi.append(open(os.path.join(ldir, f), encoding="utf-8").read().strip())
    return pezzi


SCHEMI = {"volumi": componi_volumi, "capitoli": componi_capitoli}


def componi_sorgente(coll, progetto, dir_volume):
    pezzi = SCHEMI[coll.get("schema", "volumi")](progetto, dir_volume)
    colofone = os.path.join(progetto, "assets", "colophon.md")
    if os.path.exists(colofone):
        pezzi.append(open(colofone, encoding="utf-8").read().strip())
    return "\n\n\n".join(pezzi) + "\n"


def pandoc(markdown):
    p = subprocess.run(
        ["pandoc", "--from", "markdown+smart+footnotes", "--to", "html5", "--wrap=none"],
        input=markdown.encode("utf-8"), capture_output=True,
    )
    if p.returncode != 0:
        sys.exit("pandoc: " + p.stderr.decode("utf-8", "replace"))
    return p.stdout.decode("utf-8")


# --------------------------------------------------------------------------
# Ritocchi all'HTML di pandoc
# --------------------------------------------------------------------------
def miniatura(sorgente, destinazione, larghezza=320):
    """Ritaglia a 2:3 e scala. Copertine più strette del 2:3 si tagliano in
    basso (il titolo sta in alto), più larghe ai lati, centrate."""
    im = Image.open(sorgente).convert("RGB")
    w, h = im.size
    voluto = 2 / 3
    if abs(w / h - voluto) > 0.005:
        if w / h > voluto:                        # troppo larga → taglio ai lati
            nuova_w = int(round(h * voluto))
            x = (w - nuova_w) // 2
            im = im.crop((x, 0, x + nuova_w, h))
        else:                                     # troppo stretta → taglio in basso
            nuova_h = int(round(w / voluto))
            y = min(20, max(0, h - nuova_h))
            im = im.crop((0, y, w, y + nuova_h))
    im = im.resize((larghezza, int(round(larghezza * 1.5))), Image.LANCZOS)
    im.save(destinazione, "JPEG", quality=76, optimize=True, progressive=True)


# --------------------------------------------------------------------------
# Pezzi di pagina comuni
# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# Pagina di un volume
# --------------------------------------------------------------------------
def pagina_volume(coll, slug_coll, v, precedente, successivo):
    parte = v["tipo"] == "parte"
    padre = v.get("padre")
    corpo = tabelle_scorrevoli(intestazioni_tabelle(titolo_note(v["corpo"])))

    righe = []
    for livello, ancora, testo in indice(v["corpo"]):
        righe.append('<li class="lv%d"><a href="#%s">%s</a></li>' % (livello, e(ancora), e(testo)))
    toc = '<nav class="toc" id="toc" aria-label="Indice della pagina">'
    toc += '<p class="toc-tit">%s</p><ol>%s</ol>' % ("In questo racconto" if parte else "In questo volume", "".join(righe))
    if v["parti"]:
        toc += '<p class="toc-tit dopo">I racconti</p><ol>%s</ol>' % "".join(
            '<li class="lv1"><a href="%s.html">%s</a></li>' % (e(p["slug"]), e(p["titolo"])) for p in v["parti"])
    if parte:
        toc += '<p class="toc-tit dopo">Il volume</p><ol>%s</ol>' % "".join(
            '<li class="lv1"><a href="%s.html"%s>%s</a></li>'
            % (e(p["slug"]), ' aria-current="page"' if p["slug"] == v["slug"] else "", e(p["titolo"]))
            for p in padre["parti"])
    toc += '</nav>'

    if v["parti"]:
        facts = ['<li>%d racconti</li>' % len(v["parti"]),
                 '<li>≈ %d min in tutto</li>' % (v["minuti"] + sum(p["minuti"] for p in v["parti"]))]
    else:
        facts = ['<li>≈ %d min di lettura</li>' % v["minuti"]]
    if v["autore"] and not parte:
        facts.append('<li>%s</li>' % e(v["autore"]))
    facts.append('<li>dalle partite a %s</li>' % e(coll["sistema"]))
    if v["epub_peso"]:
        facts.append('<li><a href="../../libri/%s.epub" download>%s in EPUB, %s</a></li>'
                     % (e(v["slug_sito"]), "il volume" if parte else "anche", v["epub_peso"]))

    def salto(pag, direzione):
        anno = ""
        if parte and pag is padre:
            testo = "‹ torna al volume"
        elif not parte and pag.get("padre") is v and pag.get("i") == 1:
            testo = "comincia il volume ›"
        elif v.get("crono") and pag.get("crono"):
            testo = "‹ prima nel ciclo" if direzione == "prev" else "poi nel ciclo ›"
            anno = '<span class="anno">%s</span>' % e(pag["anno"])
        else:
            etichetta = "racconto" if pag["tipo"] == "parte" else "volume"
            testo = ("‹ %s precedente" % etichetta) if direzione == "prev" else ("%s successivo ›" % etichetta)
        return ('<a class="%s" href="%s.html"><span class="dir">%s</span><span class="tit">%s</span>%s</a>'
                % (direzione, e(pag["slug"]), e(testo), e(pag["titolo"]), anno))

    salti = []
    if precedente:
        salti.append(salto(precedente, "prev"))
    if successivo:
        salti.append(salto(successivo, "next"))
    if not salti:
        salti.append('<a href="index.html"><span class="dir">collana</span>'
                     '<span class="tit">%s</span></a>' % e(coll["titolo"]))

    # blocco dei racconti, sulla pagina del volume spezzato
    elenco = ""
    if v["parti"]:
        voci = "".join(
            '<li><a href="%s.html"><span class="i">%d</span>'
            '<span class="t">%s</span><span class="d">%s</span>'
            '<span class="m">≈ %d min</span></a></li>'
            % (e(p["slug"]), p["i"], e(p["titolo"]), e(p["descrizione"]), p["minuti"])
            for p in v["parti"])
        elenco = ('<nav class="parti" aria-label="I racconti del volume">'
                  '<h2 class="parti-tit">I racconti di questo volume</h2><ol>%s</ol></nav>' % voci)

    scarica = ""
    if v["epub_peso"]:
        quale = "Tutto il volume, da leggere nel tuo lettore o da portarti offline." if parte \
            else "Preferisci leggerlo nel tuo lettore, o portartelo offline?"
        scarica = ('<div class="epub"><p>%s</p>'
                   '<a class="dl" href="../../libri/%s.epub" download>⤓ EPUB <span class="sz">%s</span></a></div>'
                   % (quale, e(v["slug_sito"]), v["epub_peso"]))

    if parte:
        kicker = "%s · racconto %d di %d" % (padre["titolo"], v["i"], len(padre["parti"]))
        briciole = [("Brainstorm Club", "../../index.html#libri"),
                    (coll["titolo"], "index.html"),
                    (padre["titolo"], padre["slug"] + ".html"),
                    (v["titolo"], None)]
        titolo_pagina = "%s · %s · Brainstorm Club" % (v["titolo"], coll["titolo"])
    else:
        kicker = "%s · %s" % (coll["titolo"], numero(coll, v))
        briciole = [("Brainstorm Club", "../../index.html#libri"),
                    (coll["titolo"], "index.html"),
                    (v["titolo"], None)]
        titolo_pagina = "%s · %s · Brainstorm Club" % (v["titolo"], coll["titolo"])

    dentro = ({"@type": "Book", "@id": padre["url"] + "#opera", "name": padre["titolo"], "url": padre["url"]}
              if parte else
              {"@type": "BookSeries", "@id": "%s/leggi/%s/#collana" % (DOMINIO, slug_coll),
               "name": coll["titolo"], "url": "%s/leggi/%s/" % (DOMINIO, slug_coll)})
    strada = [("Brainstorm Club", DOMINIO + "/"),
              (coll["titolo"], "%s/leggi/%s/" % (DOMINIO, slug_coll))]
    if parte:
        strada.append((padre["titolo"], padre["url"]))
    strada.append((v["titolo"], v["url"]))

    ld = dati_strutturati(
        club_minimo(),
        opera("Chapter" if parte else "Book", v["titolo"], v["url"], v["descrizione"], v["og"],
              isPartOf=dentro,
              position=v.get("i") if parte else v["n"],
              author=({"@type": "Person", "name": v["autore"]} if v["autore"] else {"@id": CLUB}),
              datePublished=v.get("pubblicato"),
              dateModified=v.get("aggiornato"),
              wordCount=v["parole"],
              timeRequired=durata_iso(v["minuti"]),
              bookFormat=None if parte else "https://schema.org/EBook",
              genre=["narrativa", "gioco di ruolo"],
              isBasedOn=gioco(coll["sistema"], coll["editore"], coll.get("editore_url")),
              about=[{"@type": "Thing", "name": coll["sistema"]},
                     {"@type": "Thing", "name": coll["titolo"]}],
              associatedMedia=({"@type": "MediaObject", "encodingFormat": "application/epub+zip",
                                "contentUrl": "%s/libri/%s.epub" % (DOMINIO, v["slug_sito"])}
                               if v["epub_peso"] else None)),
        briciole_ld(strada))

    return (
        testa(titolo_pagina, v["descrizione"], v["url"], v["og"], "../")
        + '<body data-slug="%s-%s">\n' % (slug_coll, v["slug"])
        + '<a class="skip" href="#testo">Vai al testo</a>\n'
        + barra(briciole, True)
        + '<div class="wrap"><div class="reading">\n'
        + toc + "\n"
        + '<main>\n<article>\n'
        + '<header class="opening">\n'
        + '<img class="cover" src="%s-cover.jpg" alt="Copertina di %s" width="320" height="480">\n' % (e(v["cover"]), e(padre["titolo"] if parte else v["titolo"]))
        + '<p class="kicker">%s</p>\n' % e(kicker)
        + '<h1>%s</h1>\n' % e(v["titolo"])
        + ('<p class="sub">%s</p>\n' % e(v["descrizione"]) if v["descrizione"] else "")
        + '<ul class="facts">%s</ul>\n' % "".join(facts)
        + '</header>\n'
        + '<div class="testo" id="testo">\n' + corpo + '\n</div>\n'
        + '<div class="coda">\n' + elenco + scarica
        + '<nav class="salti" aria-label="Continua a leggere">%s</nav>\n' % "".join(salti)
        + '</div>\n</article>\n</main>\n'
        + '<footer class="piede">'
        + '<p><a href="index.html">Tutti i volumi della collana</a> · '
        + '<a href="../../index.html#libri">I libri del Brainstorm Club</a> · '
        + '<a href="../../index.html">brainstormclub.it</a></p>'
        + '<p>Fan-fiction amatoriale, uso personale e gratuito. Sistema «%s» di %s; '
          'ambientazione e testi del Brainstorm Club — Faenza (RA).</p>' % (e(coll["sistema"]), e(coll["editore"]))
        + '</footer>\n</div></div>\n'
        + '<div class="resume" aria-live="polite" hidden><span>Eri arrivato al <span class="q">—</span></span>'
          '<button class="go" type="button">riprendi</button>'
          '<button class="no" type="button" aria-label="Ricomincia da capo">✕</button></div>\n'
        + '<aside class="nota" aria-label="Nota a piè di pagina" aria-live="polite">'
          '<button class="x" type="button" aria-label="Chiudi la nota">✕</button>'
          '<span class="n"></span><div class="corpo"></div></aside>\n'
        + ld + "\n"
        + '<script src="../%s"></script>\n</body>\n</html>\n' % versione("lettore.js")
    )


# --------------------------------------------------------------------------
# Indice della collana
# --------------------------------------------------------------------------
def pagina_collana(coll, slug_coll, volumi):
    url = "%s/leggi/%s/" % (DOMINIO, slug_coll)
    carte = []
    for v in volumi:
        alt = ""
        if v["epub_peso"]:
            alt = ('<a class="alt" href="../../libri/%s.epub" download>⤓ EPUB <span class="sz">%s</span></a>'
                   % (e(v["slug_sito"]), v["epub_peso"]))
        mini = ""
        if v["parti"]:
            mini = ('<p class="parti-mini">%s</p>' % '<span class="sep">·</span>'.join(
                '<a href="%s.html">%s</a>' % (e(p["slug"]), e(p["titolo"])) for p in v["parti"]))
        durata = sum(p["minuti"] for p in v["parti"]) + v["minuti"] if v["parti"] else v["minuti"]
        etichetta_leggi = "Apri il volume" if v["parti"] else "Leggi online"
        carte.append(
            '<li><div><img src="%s-cover.jpg" alt="Copertina di %s" width="320" height="480" loading="lazy"></div>'
            '<div><p class="num">%s</p><h2><a href="%s.html">%s</a></h2>'
            '<p class="sin">%s</p><div class="azioni">'
            '<a class="leggi" href="%s.html">%s</a>%s'
            '<span class="durata">≈ %d min</span></div>%s</div></li>'
            % (e(v["slug"]), e(v["titolo"]), e(maiuscola(numero(coll, v))), e(v["slug"]), e(v["titolo"]),
               e(v["descrizione"]), e(v["slug"]), etichetta_leggi, alt, durata, mini))

    url_collana = "%s/leggi/%s/" % (DOMINIO, slug_coll)
    dentro = []
    for v in volumi:
        dentro.append(opera("Book", v["titolo"], v["url"], v["descrizione"], v["og"],
                            position=v["n"], bookFormat="https://schema.org/EBook",
                            author=({"@type": "Person", "name": v["autore"]} if v["autore"] else {"@id": CLUB}),
                            timeRequired=durata_iso(v["minuti"] + sum(p["minuti"] for p in v["parti"])),
                            hasPart=[{"@type": "Chapter", "@id": p["url"] + "#opera",
                                      "name": p["titolo"], "url": p["url"], "position": p["i"]}
                                     for p in v["parti"]] or None))
    collana = {
        "@type": "BookSeries", "@id": url_collana + "#collana",
        "name": coll["titolo"], "url": url_collana,
        "description": coll["occhiello"], "inLanguage": "it-IT", "isAccessibleForFree": True,
        "publisher": {"@id": CLUB}, "author": {"@id": CLUB},
        "genre": ["narrativa", "gioco di ruolo"],
        "isBasedOn": gioco(coll["sistema"], coll["editore"], coll.get("editore_url")),
        "about": [{"@type": "Thing", "name": coll["sistema"]}],
        "numberOfItems": len(volumi),
        "hasPart": dentro,
    }
    if coll.get("_crono"):
        collana["workExample"] = {
            "@type": "ItemList", "name": "Il filo degli eventi",
            "description": "I racconti della collana nell'ordine in cui i fatti accadono, "
                           "che non è quello dei volumi.",
            "numberOfItems": len(coll["_crono"]),
            "itemListOrder": "https://schema.org/ItemListOrderAscending",
            "itemListElement": [{"@type": "ListItem", "position": i, "name": p["titolo"], "url": p["url"]}
                                for i, p in enumerate(coll["_crono"], start=1)],
        }
    jsonld = dati_strutturati(club_minimo(), collana,
                              briciole_ld([("Brainstorm Club", DOMINIO + "/"),
                                           (coll["titolo"], url_collana)]))

    # il filo degli eventi: i volumi sono tematici, la storia no
    filo = ""
    if coll.get("_crono"):
        righe = "".join(
            '<li><span class="anno">%s</span><a href="%s.html">%s</a>'
            '<span class="voce">voce di %s</span>%s</li>'
            % (e(p["anno"]), e(p["slug"]), e(p["titolo"]), e(p["voce"]),
               ('<span class="vol">in %s</span>' % e(p["padre"]["titolo"])) if p.get("padre") else "")
            for p in coll["_crono"])
        filo = ('<section class="filo" aria-labelledby="filo-tit">'
                '<h2 id="filo-tit">Il filo degli eventi</h2>'
                '<p class="filo-nota">Ogni volume raccoglie una voce sola, e le voci non si susseguono '
                'in ordine di tempo. Questo è l\'ordine in cui i fatti sono accaduti: da qui il ciclo '
                'si legge di seguito, e ogni racconto porta al successivo.</p>'
                '<ol>%s</ol></section>' % righe)

    badge = ' <span class="durata">◆ collana completa</span>' if coll.get("conclusa") else ""
    editore = ('<a href="%s" target="_blank" rel="noopener">%s ↗</a>' % (e(coll["editore_url"]), e(coll["editore"]))
               if coll.get("editore_url") else e(coll["editore"]))

    return (
        testa("%s · Leggi online · Brainstorm Club" % coll["titolo"], coll["occhiello"], url,
              volumi[0]["og"], "../")
        + '<body>\n<a class="skip" href="#volumi">Vai ai volumi</a>\n'
        + barra([("Brainstorm Club", "../../index.html#libri"), (coll["titolo"], None)], False)
        + '<div class="wrap">\n<header class="collana-hero">\n'
        + '<p class="kicker">Collana · Brainstorm Club%s</p>\n' % badge
        + '<h1>%s</h1>\n' % e(coll["titolo"])
        + '<p class="occhiello">%s</p>\n' % e(coll["occhiello"])
        + '<p class="credito">Tratto dalle campagne di <strong>%s</strong> · %s%s. '
          'Lettura libera dal browser; ogni volume è disponibile anche in EPUB.</p>\n'
          % (e(coll["sistema"]), editore, (" — " + e(coll["curatore"])) if coll.get("curatore") else "")
        + '</header>\n<main><ol class="volumi" id="volumi">%s</ol>%s</main>\n' % ("".join(carte), filo)
        + '<footer class="piede"><p><a href="../../index.html#libri">Tutti i libri del Brainstorm Club</a> · '
          '<a href="../../index.html">brainstormclub.it</a></p>'
          '<p>Fan-fiction amatoriale, uso personale e gratuito. Sistema «%s» di %s; '
          'ambientazione e testi del Brainstorm Club — Faenza (RA).</p></footer>\n'
          % (e(coll["sistema"]), e(coll["editore"]))
        + '</div>\n' + jsonld + '\n<script src="../%s"></script>\n</body>\n</html>\n' % versione("lettore.js")
    )


# --------------------------------------------------------------------------
def ultima_modifica(percorso):
    """La data dell'ultima modifica al sorgente: serve a `dateModified`, che per
    un motore generativo è il segnale di quanto è fresco quello che legge."""
    if not os.path.exists(percorso):
        return ""
    if os.path.isdir(percorso):
        istanti = [os.path.getmtime(os.path.join(percorso, f)) for f in os.listdir(percorso)]
        if not istanti:
            return ""
        quando = max(istanti)
    else:
        quando = os.path.getmtime(percorso)
    import datetime
    return datetime.date.fromtimestamp(quando).isoformat()


def _pagina_base(coll, slug_coll, slug, titolo, descrizione, md, corpo, cover_slug, slug_sito,
                 epub_peso, autore, pubblicato="", aggiornato=""):
    minuti, parole = tempo_di_lettura(md)
    return {
        "pubblicato": pubblicato, "aggiornato": aggiornato,
        "slug": slug, "titolo": titolo, "descrizione": descrizione,
        "corpo": corpo, "minuti": minuti, "parole": parole,
        "autore": autore, "cover": cover_slug,
        "slug_sito": slug_sito, "epub_peso": epub_peso,
        "url": "%s/leggi/%s/%s.html" % (DOMINIO, slug_coll, slug),
        "og": "%s/libri/%s.jpg" % (DOMINIO, slug_sito),
    }


def costruisci(slug_coll):
    coll = COLLANE[slug_coll]
    progetto = os.path.join(RADICE, coll["progetto"])
    cartella = "libri" if coll.get("schema") == "capitoli" else "volumi"
    uscita = os.path.join(QUI, "leggi", slug_coll)
    os.makedirs(uscita, exist_ok=True)

    volumi = []
    n = 0
    for voce in coll["volumi"]:
        # "slug" | ("slug-pagina", "cartella-sorgente") | (…, …, "extra"|"spezza"|…)
        if isinstance(voce, str):
            slug, sorgente, segni = voce, voce, ()
        else:
            slug, sorgente, segni = voce[0], voce[1], tuple(voce[2:])
        extra = "extra" in segni
        spezza = "spezza" in segni
        if not extra:
            n += 1

        meta = leggi_meta(os.path.join(progetto, cartella, sorgente, "meta.yaml"))
        aggiornato = ultima_modifica(os.path.join(progetto, cartella, sorgente))
        slug_sito = coll["prefisso"] + slug
        epub = os.path.join(QUI, "libri", slug_sito + ".epub")
        epub_peso = peso(epub) if os.path.exists(epub) else ""
        autore = meta.get("author", coll.get("curatore", ""))

        # copertina: quella di sito/libri/ (già ottimizzata), altrimenti l'originale
        sorgente_cover = os.path.join(QUI, "libri", slug_sito + ".jpg")
        if not os.path.exists(sorgente_cover):
            for est in (".jpg", ".png"):
                p = os.path.join(progetto, "copertine", sorgente + est)
                if os.path.exists(p):
                    sorgente_cover = p
                    break
        if not os.path.exists(sorgente_cover):
            sys.exit("manca la copertina di %s (cercata in sito/libri/ e in %s/copertine/)" % (slug, coll["progetto"]))
        miniatura(sorgente_cover, os.path.join(uscita, slug + "-cover.jpg"))

        if not spezza:
            md = componi_sorgente(coll, progetto, sorgente)
            v = _pagina_base(coll, slug_coll, slug, meta.get("title", slug), meta.get("description", ""),
                             md, abbassa_titoli(pandoc(md)), slug, slug_sito, epub_peso, autore,
                             meta.get("date", ""), aggiornato)
            v.update({"n": n, "extra": extra, "tipo": "volume", "parti": []})
            volumi.append(v)
            continue

        # --- volume spezzato: la pagina del volume tiene solo l'apparato,
        #     ogni racconto del manifest diventa una pagina a sé ------------
        racconti_del_volume = leggi_manifest(progetto, sorgente)
        if len(racconti_del_volume) < 2:
            md = componi_sorgente(coll, progetto, sorgente)
            v = _pagina_base(coll, slug_coll, slug, meta.get("title", slug), meta.get("description", ""),
                             md, abbassa_titoli(pandoc(md)), slug, slug_sito, epub_peso, autore,
                             meta.get("date", ""), aggiornato)
            v.update({"n": n, "extra": extra, "tipo": "volume", "parti": []})
            volumi.append(v)
            continue

        vdir = os.path.join(progetto, "volumi", sorgente)
        front = ""
        apparato = []
        for opzionale in ("front.md", "timeline.md"):
            f = os.path.join(vdir, opzionale)
            if os.path.exists(f):
                testo = open(f, encoding="utf-8").read().strip()
                apparato.append(testo)
                if opzionale == "front.md":
                    front = testo
        colofone = os.path.join(progetto, "assets", "colophon.md")
        if os.path.exists(colofone):
            apparato.append(open(colofone, encoding="utf-8").read().strip())
        md_vol = "\n\n\n".join(apparato) + "\n"

        v = _pagina_base(coll, slug_coll, slug, meta.get("title", slug), meta.get("description", ""),
                         md_vol, abbassa_titoli(pandoc(md_vol)), slug, slug_sito, epub_peso, autore,
                         meta.get("date", ""), aggiornato)
        v.update({"n": n, "extra": extra, "tipo": "volume", "parti": []})

        for i, (nome, prefisso) in enumerate(racconti_del_volume, start=1):
            md_r = open(os.path.join(progetto, "racconti", nome + ".md"), encoding="utf-8").read()
            if prefisso:
                md_r = re.sub(r'\[\^([0-9A-Za-z]+)\]', lambda m: "[^%s%s]" % (prefisso, m.group(1)), md_r)
            titolo_r = titolo_markdown(md_r, nome)
            base = slugifica(nome)
            slug_r = base if base.startswith(slug + "-") else "%s-%s" % (slug, base)
            md_p = md_r.strip() + "\n\n\n" + (open(colofone, encoding="utf-8").read().strip() if os.path.exists(colofone) else "")
            corpo_r = pandoc(md_p)
            # il titolo del racconto è già la testata della pagina: nel corpo si toglie
            corpo_r = re.sub(r'^\s*<h1 id="[^"]*"[^>]*>%s</h1>' % re.escape(e(titolo_r)), '', corpo_r, count=1)
            corpo_r = abbassa_titoli(corpo_r, solo_h1=True)
            parte = _pagina_base(coll, slug_coll, slug_r, titolo_r,
                                 descrizione_racconto(front, titolo_r, md_r),
                                 md_p, corpo_r, slug, slug_sito, epub_peso, autore,
                                 meta.get("date", ""),
                                 ultima_modifica(os.path.join(progetto, "racconti", nome + ".md")))
            parte.update({"tipo": "parte", "i": i, "padre": v, "extra": False, "n": n, "parti": []})
            v["parti"].append(parte)

        # l'indice scritto dal curatore in front.md diventa navigabile
        for parte in v["parti"]:
            grassetto = "<strong>%s</strong>" % e(parte["titolo"])
            if grassetto in v["corpo"]:
                v["corpo"] = v["corpo"].replace(
                    grassetto, '<strong><a href="%s.html">%s</a></strong>' % (e(parte["slug"]), e(parte["titolo"])), 1)
        volumi.append(v)

    # --- il filo degli eventi: la Timeline canonica lega i racconti fra volumi ---
    crono = []
    if coll.get("cronologia"):
        per_titolo = {p["titolo"]: p for v in volumi for p in v["parti"]}
        per_titolo.update({v["titolo"]: v for v in volumi if not v["parti"]})
        for riga in leggi_cronologia(progetto, coll["cronologia"]):
            pag = per_titolo.pop(riga["titolo"], None)
            if pag is None:
                print("  ! cronologia: nessuna pagina per «%s»" % riga["titolo"])
                continue
            pag["anno"], pag["voce"] = riga["anno"], riga["voce"]
            crono.append(pag)
            pag["crono"] = len(crono)
        for rimasto in per_titolo:
            print("  ! cronologia: «%s» non compare nella Timeline" % rimasto)
    coll["_crono"] = crono

    # --- chi viene prima e chi dopo -------------------------------------------
    # Volume: i volumi vicini (e il proprio primo racconto come «comincia»).
    # Racconto: se la collana ha una cronologia, i vicini sono quelli del filo
    # degli eventi — anche se stanno in un altro volume; altrimenti i fratelli.
    pagine = []
    for idx, v in enumerate(volumi):
        prec_v = volumi[idx - 1] if idx else None
        succ_v = volumi[idx + 1] if idx + 1 < len(volumi) else None
        if v.get("crono"):
            j = v["crono"] - 1
            pagine.append((v, crono[j - 1] if j else prec_v,
                           crono[j + 1] if j + 1 < len(crono) else succ_v))
        else:
            pagine.append((v, prec_v, v["parti"][0] if v["parti"] else succ_v))
        for k, pag in enumerate(v["parti"]):
            if crono and pag.get("crono"):
                j = pag["crono"] - 1
                prima = crono[j - 1] if j else v
                dopo = crono[j + 1] if j + 1 < len(crono) else None
            else:
                prima = v["parti"][k - 1] if k else v
                dopo = v["parti"][k + 1] if k + 1 < len(v["parti"]) else succ_v
            pagine.append((pag, prima, dopo))

    for pag, prima, dopo in pagine:
        percorso = os.path.join(uscita, pag["slug"] + ".html")
        with open(percorso, "w", encoding="utf-8") as f:
            f.write(pagina_volume(coll, slug_coll, pag, prima, dopo))
        segno = "   └ " if pag["tipo"] == "parte" else "  "
        print("%s%-30s %6s  ≈%3d min  %5d parole" % (segno, pag["slug"] + ".html", peso(percorso), pag["minuti"], pag["parole"]))

    percorso = os.path.join(uscita, "index.html")
    with open(percorso, "w", encoding="utf-8") as f:
        f.write(pagina_collana(coll, slug_coll, volumi))
    print("  %-30s %6s" % ("index.html", peso(percorso)))
    return volumi


def scrivi_llms(tutte):
    """/llms.txt — la mappa del sito in Markdown, per chi legge il sito con una
    macchina: cos'è questo posto, che cosa ci si trova e a quale indirizzo.
    Convenzione llmstxt.org: un H1, un sommario, poi sezioni di link con una
    riga di descrizione ciascuno."""
    r = []
    r.append("# Brainstorm Club — Associazione Ludica Faentina\n")
    r.append("> Associazione di gioco di Faenza (RA) attiva dal 1989. Questo sito pubblica, "
             "gratuitamente e per intero, i racconti nati dalle campagne giocate al club e i "
             "fascicoli che se ne portano al tavolo. Ogni testo si legge dal browser e si scarica "
             "in EPUB o PDF.\n")
    r.append("Che cosa sono questi testi: **narrativa amatoriale**, scritta dai giocatori a partire "
             "dalle partite vere di un tavolo, ordinata e riscritta dopo. Non sono materiale "
             "ufficiale degli editori dei giochi citati, non sono in vendita e non sostituiscono i "
             "manuali. Lingua: italiano. Le date interne alle storie sono finzione.\n")
    r.append("Come è organizzato: i racconti stanno in **collane**, una per campagna; una collana "
             "raccoglie **volumi**, e un volume può essere un racconto solo o raccoglierne più "
             "d'uno, ciascuno con la sua pagina.\n")

    for slug_coll, volumi in tutte:
        coll = COLLANE[slug_coll]
        r.append("## %s — dalle campagne di %s (%s)\n" % (coll["titolo"], coll["sistema"], coll["editore"]))
        r.append("%s\n" % coll["occhiello"])
        r.append("- [Indice della collana](%s/leggi/%s/): tutti i volumi, con le sinossi.%s\n"
                 % (DOMINIO, slug_coll,
                    " Include «Il filo degli eventi», l'ordine cronologico in cui i fatti accadono."
                    if coll.get("_crono") else ""))
        for v in volumi:
            etichetta = "extra fuori continuity" if v["extra"] else numero(coll, v)
            r.append("- [%s](%s): %s _(%s%s, ≈%d min)_"
                     % (v["titolo"], v["url"], v["descrizione"], etichetta,
                        ", %s" % v["autore"] if v["autore"] else "",
                        v["minuti"] + sum(p["minuti"] for p in v["parti"])))
            for p in v["parti"]:
                r.append("  - [%s](%s): %s _(%s%s, ≈%d min)_"
                         % (p["titolo"], p["url"], p["descrizione"],
                            "in «%s»" % v["titolo"],
                            ", anno %s, voce di %s" % (p["anno"], p["voce"]) if p.get("anno") else "",
                            p["minuti"]))
        r.append("")

    fascicoli = sorted(glob.glob(os.path.join(QUI, "avventure", "*-web.html")))
    if fascicoli:
        r.append("## Avventure e materiali da portare al tavolo\n")
        r.append("Fascicoli giocabili e dispense scritte al club: si leggono online e si scaricano "
                 "in PDF (una versione per lo schermo e una per la stampa).\n")
        for f in fascicoli:
            t = open(f, encoding="utf-8").read(4000)
            titolo = re.search(r'<title>(.*?)(?: · Brainstorm Club)?</title>', t, re.S)
            descr = re.search(r'<meta name="description" content="([^"]*)"', t)
            r.append("- [%s](%s/avventure/%s): %s"
                     % (html.unescape(titolo.group(1)) if titolo else os.path.basename(f),
                        DOMINIO, os.path.basename(f),
                        html.unescape(descr.group(1)) if descr else ""))
        r.append("")

    r.append("## Il club\n")
    r.append("- [Home](%s/): chi siamo, i tavoli aperti, il programma, dove ci si trova." % DOMINIO)
    r.append("- [Mappa del sito](%s/sitemap.xml): tutte le pagine." % DOMINIO)
    r.append("- Contatto: ciao@brainstormclub.it — Palazzo Laderchi, Via Laderchi 3, Faenza (RA).")
    r.append("")

    percorso = os.path.join(QUI, "llms.txt")
    with open(percorso, "w", encoding="utf-8") as f:
        f.write("\n".join(r))
    print("  %-32s %6s" % ("llms.txt", peso(percorso)))


if __name__ == "__main__":
    scelte = sys.argv[1:] or list(COLLANE)
    fatte = []
    for scelta in scelte:
        if scelta not in COLLANE:
            sys.exit("collana sconosciuta: %s (registrate: %s)" % (scelta, ", ".join(COLLANE)))
        print("== %s ==" % scelta)
        fatte.append((scelta, costruisci(scelta)))
    if len(scelte) == len(COLLANE):      # la mappa si riscrive solo quando ci sono tutte
        print("== mappa per le macchine ==")
        scrivi_llms(fatte)
