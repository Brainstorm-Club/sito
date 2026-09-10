# Sito del Brainstorm Club — istruzioni di progetto

Sito dell'**associazione ludica faentina Brainstorm Club** (dal 1989, Palazzo Laderchi, Faenza).
Una **home mono-pagina** (`index.html`, HTML5 self-contained costruito sul design system del club) più
due sezioni di lettura generate da script: i **libri** delle collane in `leggi/` e i **fascicoli** —
avventure e manuali da tavolo — in `avventure/`. Si lavora in **italiano**, anche nel codice e nei
commenti.

## La cosa da sapere prima di tutte

**Il dominio si aggiorna via FTP, a mano, dall'utente.** Non è GitHub Pages, non si deploya dal
repository `Brainstorm-Club/sito`. Il lavoro di una sessione arriva fino ai **file pronti in locale**;
il caricamento lo fa l'utente.

Conseguenza pratica: **una correzione committata o costruita non è una correzione pubblicata.** In una
sola sessione è successo due volte che una cosa fosse vera nel repository e falsa per chi apriva il
sito. Prima di dire «fatto», vedi *Verificare* in fondo.

## Struttura

```
sito/
├── index.html          la home: tavoli, #libri, #avventure, programma. Mono-pagina, full-document
├── lettore.py          impalcatura condivisa delle pagine di lettura (testa, briciole, indice, dati strutturati)
├── build_leggi.py      genera leggi/** e llms.txt dal registro COLLANE
├── leggi/
│   ├── lettore.css     stile del lettore — UNICA COPIA
│   ├── lettore.js      comportamento del lettore — UNICA COPIA
│   └── <collana>/      index.html + <volume>.html + <volume>-<racconto>.html + <volume>-cover.jpg
├── avventure/          <slug>-web.html + <slug>.pdf + <slug>-stampa.pdf + <slug>-cover.jpg
├── libri/              <slug>.epub + <slug>.jpg (copertine full-size)
├── design-system/      copia vendorizzata del design system del club
├── llms.txt            mappa del sito in Markdown, per chi lo legge con una macchina
├── robots.txt · sitemap.xml
```

Le campagne-sorgente stanno **fuori di qui**: `../brancalonia/`, `../roguetrader/ciclo-korvaal/`,
`../roguetrader/dark-heresy/`, `../dnd-jr/`, `../apocalisse/`, `../heroes/`. Il sito non contiene testo
originale: lo **rigenera** dalle stesse fonti degli EPUB. Non ricopiare mai un racconto qui dentro.

## Il lettore è uno solo

`leggi/lettore.css` + `leggi/lettore.js` (stile e comportamento) e `lettore.py` (impalcatura). Li usano:

- **`build_leggi.py`** per i libri, che **collegano** i due file (con `?v=<mtime>`, per bucare la cache
  dei browser dopo un caricamento FTP);
- **`../impaginatore/lettore_web.py`** per i fascicoli, che li **incorporano**: un fascicolo resta un
  file solo, da mandare per posta o aprire da una chiavetta al tavolo.

Se tocchi il lettore, tocchi entrambi. Dopo una modifica a `lettore.py` **rigenera e confronta**: i
libri devono restare identici byte per byte se il cambiamento non li riguardava.

Cosa fa: barra con le briciole di pane, indice laterale (cassetto sotto i 1180px), avanzamento,
ripresa della lettura, corpo del testo in tre passi, tema chiaro/scuro/auto, note a comparsa. Chiavi in
`localStorage`: `bsc-theme-pref` e `bsc-theme` **condivise con la home**, più `bsc-read-size` e
`bsc-read-pos:<pagina>`. Il segnalibro si legge **prima** del primo `suScroll()` e non si tocca finché
il lettore non scorre: altrimenti si cancella da solo.

## I libri — `python3 sito/build_leggi.py [collana]`

Tutto sta nel registro `COLLANE` in cima allo script: aggiungere una collana è una voce, il resto è già
scritto. Sei collane: `regno-di-taglia`, `ciclo-di-korvaal`, `acta-heretica`, `tiro-salvezza`,
`terre-desolate`, `dossier-scavengers`.

Due **schemi** di composizione, perché i progetti-libro non sono tutti uguali:

- `volumi` (default): `volumi/<vol>/manifest.txt` compone i racconti da `racconti/`, con prefisso-note,
  esattamente come `build_epub.sh`;
- `capitoli` (Brancalonia): `libri/<nome>/` con epigrafe e `NN_*.md` in ordine di nome. Niente manifest
  perché un libro è un racconto solo; le note non si prefissano, non collidono.

Una voce di volume è `"slug"` oppure `("slug-pagina", "cartella-sorgente")` più marcatori:

| Marcatore | Effetto |
|---|---|
| `"extra"` | fuori numerazione (`la-rosa-davorio`): kicker «extra · fuori continuity» |
| `"spezza"` | ogni racconto del manifest diventa una pagina; la pagina del volume tiene solo l'apparato e l'elenco. **Un volume con un racconto solo non si spezza** (sarebbe uno stub più un URL doppio) |

`"cronologia": "assets/canone_serie.md"` legge la tabella **Timeline** della bibbia di serie e ne ricava
«Il filo degli eventi» in fondo all'indice di collana **più il prev/next cronologico**, che scavalca i
volumi. Serve dove i volumi sono tematici ma la storia è una sola (Korvaal). Lo script avvisa se un
racconto non è in Timeline o viceversa: quegli avvisi vanno guardati, non ignorati.

Insidie già pagate: i titoli vanno passati per `raffina()` (pandoc `+smart` trasforma `'` in `’` e i
confronti non combaciano); le sinossi dei racconti si pescano dalle righe `- **Titolo** *(contesto)* —
descrizione` di `front.md`, scritte dal curatore, non inventate.

**Gli omnibus non hanno pagina propria** — ripeterebbero per intero gli altri volumi, e due URL con lo
stesso testo si fanno concorrenza. Sulla card della home il loro «Leggi online» punta all'**indice della
collana**, che è l'equivalente in lettura dell'edizione completa.

## I fascicoli — `../impaginatore/impagina.sh`

Li costruisce il `build*.sh` dentro la cartella del fascicolo. La versione da schermo passa per il
lettore, non per il CSS di stampa.

**La regola che conta:**

| Il documento dichiara… | Uscita | Che cos'è |
|---|---|---|
| `--url https://…` | `<nome>-web.html` | pubblicabile: canonical, Open Graph, `index, follow`, scheda nei dati strutturati |
| nessun `--url` | `<nome>-interno.html` | copia di servizio del club: `noindex, nofollow`, avviso in testa, nessuna scheda |

Nasce da un caso vero: il **Grimorio di Bassa Lega** completo riassume 58 incantesimi dei manuali di
Acheron e **al club resta, online non va**; pubblicabile è solo la variante `-regole`, generata al volo
dal build. Prima uscivano entrambi come `-web.html` e a distinguerli c'era solo la memoria di chi
caricava — e il file completo esisteva davvero sul disco. `build_grimorio.sh` ora **verifica anche il
contenuto** delle uscite pubblicabili (niente «Appendice», «Tempo di lancio», «Componenti:») e si ferma
se rientrano.

Sul sito i fascicoli mantengono gli URL di sempre (`avventure/<slug>-web.html`): sono indicizzati, non
si spostano.

## La home

Nella sezione `#libri`, ogni card ha «**Leggi online**» come link primario e l'EPUB retrocesso a
`.dl.dl--alt` tratteggiato. Regole dell'utente:

- sul link di lettura **solo «Leggi online»**, senza KB né conteggi: le etichette lunghe mandavano il
  pulsante a capo. Il peso resta sul link EPUB e sui PDF delle avventure;
- **i pesi non si scrivono a mano**: si rileggono dal disco a ogni rigenerazione;
- ordine dei libri **cronologico della storia**, non di pubblicazione;
- niente spoiler nelle sinossi: sono ganci, non rivelazioni. Chi legge può essere un giocatore.

## SEO e GEO

Un solo `<script type="application/ld+json">` per pagina con `@graph`, e **una sola entità del club**:
`@id` `https://www.brainstormclub.it/#organizzazione`, dichiarata per esteso sulla home e **richiamata
per `@id`** da tutte le altre pagine. Mai ricopiarne i dati.

Ogni opera porta `@id`, `mainEntityOfPage`, `datePublished`, `dateModified`, `wordCount`,
`timeRequired` ISO, `isBasedOn` (il gioco con editore e URL), `about`, `associatedMedia` (EPUB o PDF),
`isPartOf` verso volume e collana; l'indice di collana porta la `BookSeries` e, dove c'è, il filo
cronologico come `ItemList` ordinata. Niente `temporalCoverage` con gli anni imperiali: sono finzione,
non date ISO.

`robots.txt` **ammette esplicitamente** i crawler dei motori di risposta (scelta dell'utente: non
bloccarli). `llms.txt` è la mappa in Markdown e si rigenera **solo quando si costruiscono tutte le
collane** — i fascicoli li rilegge dai `-web.html` in `avventure/`.

Invarianti da non rompere: title ≤ 75 caratteri, description ≤ 165 (la sinossi intera resta in pagina,
nel `<meta>` va la versione tagliata a fine frase), canonical su ogni pagina, `og:url` uguale al
canonical, nessun duplicato di title o description, sitemap allineata alle pagine che esistono davvero.

## Accessibilità

Sono vincoli, non preferenze: **una sola `h1` per pagina** (il corpo di pandoc scende di un livello) e
**nessun salto di livello** nei titoli; le etichette dell'indice laterale sono `<p class="toc-tit">`,
non titoli, per non sporcare la gerarchia; il piede sta fuori da `<main>`; la nota a comparsa è
`visibility:hidden` da chiusa, così il suo bottone non è raggiungibile col tab.

**Contrasti:** `--primary` (#C2332B) su carbone sta a 3,26:1, sotto la soglia AA. Per il **testo** in
rosso esiste `--accento`; `--primary` è il rosso dei **fondi**. Se aggiungi testo colorato, misura.

## Verificare, prima di dire «fatto»

1. Rigenera e controlla la struttura: HTML ben formato, una `h1`, nessun salto di livello, nessuna
   ancora morta, JSON-LD che si parsifica, link locali che risolvono.
2. Guarda le pagine in un browser, in **entrambi i temi** e a **larghezza di telefono**.
3. Dopo che l'utente ha caricato, **verifica sul dominio**: le URL della sitemap devono rispondere,
   il lettore dev'essere servito, e le pagine che non devono esistere devono dare **404**.

## Non va online

- gli `-interno.html` e i loro PDF (Grimorio completo);
- le pagine degli omnibus;
- qualunque cosa riassuma o riproduca il contenuto dei manuali degli editori.

In caso di dubbio su un documento nuovo: se non ha un `--url`, non è pubblicabile. Chiedi.
