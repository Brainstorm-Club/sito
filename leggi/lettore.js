/* ============================================================
   Brainstorm Club — lettore web dei libri
   Tema (condiviso col sito), corpo del testo, indice, avanzamento,
   ripresa della lettura, note a comparsa. Nessuna dipendenza.
   Tutto degrada: senza JS la pagina resta un testo leggibile con
   indice ad ancore e note in coda.
   ============================================================ */
(function () {
  'use strict';
  var root = document.documentElement;
  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) {} },
    del: function (k) { try { localStorage.removeItem(k); } catch (e) {} }
  };

  /* ---------- TEMA (stesse chiavi del sito: scuro → chiaro → auto) ---------- */
  var PREF = ['dark', 'light', 'auto'];
  var ETICHETTA = { dark: 'scuro', light: 'chiaro', auto: 'automatico' };
  function effettivo(p) {
    if (p !== 'auto') return p;
    return matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  }
  function applicaTema(p, salva) {
    var eff = effettivo(p);
    root.setAttribute('data-theme', eff);
    root.setAttribute('data-theme-pref', p);
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', eff === 'light' ? '#EFEAE1' : '#181617');
    if (salva) { store.set('bsc-theme-pref', p); store.set('bsc-theme', eff); }
    var b = document.getElementById('themeBtn');
    if (b) b.setAttribute('aria-label', 'Tema: ' + ETICHETTA[p] + ' (cambia)');
  }
  var pref = store.get('bsc-theme-pref') || store.get('bsc-theme') || 'dark';
  if (PREF.indexOf(pref) < 0) pref = 'dark';
  applicaTema(pref, false);
  matchMedia('(prefers-color-scheme: light)').addEventListener('change', function () {
    if (root.getAttribute('data-theme-pref') === 'auto') applicaTema('auto', false);
  });
  var themeBtn = document.getElementById('themeBtn');
  if (themeBtn) themeBtn.addEventListener('click', function () {
    pref = PREF[(PREF.indexOf(pref) + 1) % PREF.length];
    applicaTema(pref, true);
  });

  /* ---------- CORPO DEL TESTO ---------- */
  var TAGLIE = ['s', 'm', 'l'];
  var taglia = store.get('bsc-read-size');
  if (TAGLIE.indexOf(taglia) < 0) taglia = 's';
  root.setAttribute('data-read-size', taglia);
  var sizeBtn = document.getElementById('sizeBtn');
  function etichettaTaglia() {
    if (sizeBtn) sizeBtn.setAttribute('aria-label', 'Dimensione del testo: ' + (taglia === 's' ? 'normale' : taglia === 'm' ? 'grande' : 'molto grande') + ' (cambia)');
  }
  etichettaTaglia();
  if (sizeBtn) sizeBtn.addEventListener('click', function () {
    taglia = TAGLIE[(TAGLIE.indexOf(taglia) + 1) % TAGLIE.length];
    root.setAttribute('data-read-size', taglia);
    store.set('bsc-read-size', taglia);
    etichettaTaglia();
  });

  var testo = document.querySelector('.testo');
  if (!testo) return;

  /* ---------- INDICE: cassetto su schermo stretto, evidenza della sezione ---------- */
  var toc = document.getElementById('toc');
  var tocBtn = document.getElementById('tocBtn');
  var stretto = matchMedia('(max-width:1179px)');
  function sistemaIndice() {
    if (!toc) return;
    if (stretto.matches) { toc.hidden = true; if (tocBtn) tocBtn.setAttribute('aria-expanded', 'false'); }
    else { toc.hidden = false; }
  }
  sistemaIndice();
  stretto.addEventListener('change', sistemaIndice);
  if (tocBtn && toc) {
    tocBtn.addEventListener('click', function () {
      var apri = toc.hidden;
      toc.hidden = !apri;
      tocBtn.setAttribute('aria-expanded', apri ? 'true' : 'false');
    });
    toc.addEventListener('click', function (e) {
      if (e.target.closest('a') && stretto.matches) { toc.hidden = true; tocBtn.setAttribute('aria-expanded', 'false'); }
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && stretto.matches && !toc.hidden) { toc.hidden = true; tocBtn.setAttribute('aria-expanded', 'false'); tocBtn.focus(); }
    });
  }

  var voci = toc ? Array.prototype.slice.call(toc.querySelectorAll('a[href^="#"]')) : [];
  var bersagli = voci.map(function (a) { return document.getElementById(decodeURIComponent(a.getAttribute('href').slice(1))); });
  function evidenzia() {
    var y = window.scrollY + window.innerHeight * 0.28;
    var i, corrente = -1;
    for (i = 0; i < bersagli.length; i++) {
      if (bersagli[i] && bersagli[i].offsetTop <= y) corrente = i;
    }
    for (i = 0; i < voci.length; i++) voci[i].classList.toggle('on', i === corrente);
  }

  /* ---------- AVANZAMENTO + RIPRESA ---------- */
  var barra = document.querySelector('.progress > i');
  var chiaveLettura = 'bsc-read-pos:' + (document.body.getAttribute('data-slug') || location.pathname);
  function quota() {
    var alto = document.documentElement.scrollHeight - window.innerHeight;
    return alto > 0 ? Math.min(1, Math.max(0, window.scrollY / alto)) : 0;
  }
  var ultimoSalvataggio = 0;
  var haScorso = false;   // finché il lettore non scorre non si tocca il segnalibro
  function suScroll() {
    var q = quota();
    if (barra) barra.style.width = (q * 100).toFixed(2) + '%';
    evidenzia();
    if (!haScorso) return;
    var ora = Date.now();
    if (ora - ultimoSalvataggio > 900) {
      ultimoSalvataggio = ora;
      if (q > 0.02 && q < 0.985) store.set(chiaveLettura, String(Math.round(window.scrollY)));
      else store.del(chiaveLettura);
    }
  }
  // la posizione va letta PRIMA del primo suScroll(): a pagina appena aperta
  // siamo in cima, e suScroll() cancellerebbe il segnalibro che stiamo cercando
  var salvato = parseInt(store.get(chiaveLettura) || '0', 10);

  var attesa = false;
  window.addEventListener('scroll', function () {
    haScorso = true;
    if (attesa) return;
    attesa = true;
    requestAnimationFrame(function () { attesa = false; suScroll(); });
  }, { passive: true });
  window.addEventListener('resize', suScroll, { passive: true });
  suScroll();

  var chip = document.querySelector('.resume');
  if (chip && salvato > window.innerHeight * 0.75 && !location.hash) {
    var alto = document.documentElement.scrollHeight - window.innerHeight;
    var perc = alto > 0 ? Math.round((salvato / alto) * 100) : 0;
    var q = chip.querySelector('.q');
    if (q) q.textContent = perc + '%';
    chip.hidden = false;
    chip.querySelector('.go').addEventListener('click', function () {
      window.scrollTo({ top: salvato, behavior: 'auto' });
      chip.hidden = true;
    });
    chip.querySelector('.no').addEventListener('click', function () {
      chip.hidden = true;
      store.del(chiaveLettura);
    });
    setTimeout(function () { chip.hidden = true; }, 12000);
  }

  /* ---------- NOTE A COMPARSA ---------- */
  var pannello = document.querySelector('.nota');
  if (pannello) {
    var corpo = pannello.querySelector('.corpo');
    var etichetta = pannello.querySelector('.n');
    var ultimoRimando = null;
    function chiudiNota(rifocalizza) {
      pannello.classList.remove('on');
      pannello.setAttribute('aria-hidden', 'true');
      if (rifocalizza && ultimoRimando) ultimoRimando.focus();
      ultimoRimando = null;
    }
    testo.addEventListener('click', function (e) {
      var a = e.target.closest('a.footnote-ref');
      if (!a) return;
      var nota = document.getElementById(decodeURIComponent(a.getAttribute('href').slice(1)));
      if (!nota) return;                       // senza la nota, lascia fare al browser
      e.preventDefault();
      var copia = nota.cloneNode(true);
      var back = copia.querySelector('.footnote-back');
      if (back) back.remove();
      corpo.innerHTML = copia.innerHTML;
      etichetta.textContent = 'Nota ' + (a.textContent || '').replace(/[^\d]/g, '');
      pannello.classList.add('on');
      pannello.setAttribute('aria-hidden', 'false');
      ultimoRimando = a;
    });
    pannello.querySelector('.x').addEventListener('click', function () { chiudiNota(true); });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && pannello.classList.contains('on')) chiudiNota(true);
    });
    document.addEventListener('click', function (e) {
      if (!pannello.classList.contains('on')) return;
      if (pannello.contains(e.target) || e.target.closest('a.footnote-ref')) return;
      chiudiNota(false);
    });
  }
})();
