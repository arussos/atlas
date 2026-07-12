# ADR-004 — Documentation Rendering Standard

**Status**: Accepted  
**Date**: 2026-07-08  
**Authors**: Art&Tango / ABRAZO  
**Relazioni**: ADR-003 (Operational Documentation Generation)  
**Riferimento visivo**: `docs/architecture/references/documentation-rendering-reference.png`

---

## 1. Contesto

### 1.1 La documentazione testuale non è più sufficiente

Fino a DOC 2.0, i manuali operativi di ABRAZO erano documenti di testo con formattazione Markdown. Lo screenshot della pagina era assente o, quando presente, non annotato. Il risultato era una documentazione che descriveva l'interfaccia invece di mostrarla: lo staff doveva leggere "il badge in alto a sinistra di colore rosso con la scritta Da verificare" e poi cercarlo a schermo autonomamente.

Con DOC 3.0, MAN-002 ha introdotto i primi screenshot con marker numerati sovrapposti. Questo ha dimostrato il valore delle figure illustrate, ma ha anche rivelato i limiti dell'approccio: i marker — cerchi rossi posizionati in percentuale sull'immagine — si sovrappongono al contenuto che dovrebbero evidenziare, riducono la leggibilità del dettaglio, e possono oscurare elementi importanti quando la posizione non è perfetta.

### 1.2 ABRAZO richiede una documentazione professionale orientata agli operatori

ABRAZO gestisce festival internazionali con centinaia di partecipanti, personale di segreteria non necessariamente tecnico, e volontari che si avvicinano al sistema per la prima volta il giorno dell'evento. In questo contesto, un manuale non è un documento accessorio: è uno strumento operativo che deve funzionare sotto pressione, con poco tempo a disposizione, da un tablet o da un foglio stampato.

La documentazione deve avere la stessa qualità del software che descrive. Un manuale con layout approssimativo, screenshot illeggibili o istruzioni ambigue indebolisce la fiducia nell'intero sistema.

### 1.3 Il momento della transizione

DOC 3.0 ha dimostrato che il sistema di generazione PDF è in grado di supportare figure illustrate. DOC 4.0 non è una revisione incrementale: è la definizione del **rendering standard definitivo** che tutti i manuali devono adottare — retroattivamente a partire da MAN-002 e prospetticamente per tutti i manuali futuri.

---

## 2. Decisione architetturale

Tutti i manuali operativi ABRAZO adottano il **Documentation Rendering Standard DOC 4.0** per la presentazione delle figure illustrate.

Lo standard si basa su tre pilastri:

1. **Callout esterni**: i numeri di riferimento non si sovrappongono mai al contenuto dell'immagine. Sono posizionati all'esterno del frame, collegati all'elemento evidenziato da una linea di richiamo sottile.

2. **Trattamento quasi impercettibile dell'immagine**: gli screenshot vengono presentati con fedeltà cromatica piena. L'unico aggiustamento applicato di default è un aumento della luminosità di +1%, sufficiente a compensare la resa su carta senza alterare i colori dell'interfaccia. Nessuna desaturazione, nessuna modifica al contrasto.

3. **Legenda strutturata**: ogni numero corrisponde a una voce di legenda con un titolo in grassetto e una spiegazione operativa sintetica. La legenda segue l'immagine, non la affianca.

Questo standard sostituisce il sistema DOC 3.0 di marker sovrapposti (cerchi con `position: absolute` all'interno del container immagine) e diventa il template di default per tutti i manuali generati dal motore PDF di ABRAZO.

---

## 3. Principi

### 3.1 Una figura, un concetto operativo

Ogni figura illustra un singolo concetto operativo, non una pagina intera. Se una pagina dell'interfaccia contiene più concetti distinti, questi vengono documentati con figure separate e dedicate.

Una figura non è una fotografia dell'interfaccia: è uno strumento didattico. La selezione del frame, la scelta dei callout e la scrittura della legenda sono atti editoriali, non di documentazione passiva.

### 3.2 Screenshot come asset condivisi

Ogni screenshot è un asset riutilizzabile e indipendente dal manuale in cui compare. Lo stesso screenshot (es. `SCN-101-dashboard-overview.png`) può essere annotato in modo diverso in MAN-001 e MAN-002, perché ogni manuale evidenzia elementi diversi per destinatari diversi.

Questa separazione tra l'asset (il PNG) e la sua annotazione (i callout generati a runtime) è il principio architetturale fondamentale del sistema di figure.

### 3.3 Libreria screenshot centralizzata

Tutti gli screenshot ufficiali risiedono in `docs/screenshots/` secondo la struttura e la convenzione documentata in `docs/screenshots/README.md`. Nessun manuale contiene screenshot propri al di fuori di questa libreria.

La libreria è la fonte unica di verità per gli screenshot. Aggiornare un'immagine nella libreria si riflette automaticamente su tutti i manuali che la referenziano alla successiva generazione PDF.

### 3.4 Figure numerate con riferimenti espliciti nel testo

Ogni figura ha un numero progressivo nel contesto del manuale in cui compare. Il testo del manuale riferisce la figura con la formula:

> vedi Figura N — Titolo (SCN-XXX)

I riferimenti non sono opzionali: ogni figura deve essere citata almeno una volta nel testo che la precede. Una figura senza riferimento nel testo è un'omissione editoriale.

Il formato del titolo figura è:

> Figura N — Titolo descrittivo (SCN-XXX)

dove `SCN-XXX` è il codice stabile dell'asset nella libreria screenshot.

### 3.5 Callout esterni con linee di richiamo

I numeri identificativi dei callout sono posizionati **all'esterno del frame dell'immagine**, sulla destra. Una linea sottile collega ogni numero al punto specifico nell'immagine che si intende evidenziare.

Questo approccio garantisce che nessun elemento dell'interfaccia sia oscurato dall'annotazione. Il contenuto dell'immagine rimane integralmente leggibile.

I callout sono generati come elementi SVG o HTML posizionati nel DOM attorno al container immagine, non come overlay sul PNG.

### 3.6 Legenda descrittiva sotto l'immagine

La legenda non è a lato dell'immagine: è sotto, dopo la didascalia. Ogni voce di legenda contiene:

- il numero del callout (come icona grafica, non come testo corrente)
- un **titolo breve in grassetto** che identifica l'elemento evidenziato
- una **spiegazione operativa sintetica** che spiega il perché di quell'elemento in quella schermata

La distinzione tra titolo e spiegazione è importante: il titolo nomina l'elemento, la spiegazione ne spiega il ruolo operativo per chi legge il manuale.

### 3.7 Rimandi incrociati tra sezioni e figure

Ogni volta che il testo di un manuale menziona un'operazione documentata altrove, il riferimento esplicito alla sezione e alla figura è obbligatorio. Il formato standard è:

> Per registrare un acconto, vedi §6 Come segnare un acconto ricevuto.  
> Per aprire la Pratica partecipante, vedi §10 (Figura 2 — SCN-201).

I rimandi incrociati riducono la necessità di ripetere le stesse istruzioni in più sezioni e permettono al lettore di navigare il manuale in modo non lineare, entrando dalla sezione rilevante per il proprio compito del momento.

### 3.8 Nessuna modifica ai PNG originali

I file PNG nella libreria screenshot non vengono mai modificati. Il trattamento cromatico (luminosità +1%), i callout e la legenda sono applicati esclusivamente durante la generazione PDF, a runtime.

Questo principio garantisce che:
- lo stesso PNG possa essere annotato diversamente in manuali diversi
- aggiornare uno screenshot richiede solo di sostituire il file nella libreria
- il processo di acquisizione degli screenshot è separato e indipendente dal processo di documentazione

### 3.9 Rendering esclusivamente durante la generazione PDF

Nessun elemento grafico del sistema di figure — callout, linee di richiamo, legenda — esiste come file separato o come modifica all'immagine originale. Tutto è generato a runtime da `scripts/generate-manual-pdfs.mjs` a partire dai parametri definiti nel sorgente Markdown del manuale.

Il sorgente Markdown è la definizione autoritativa del manuale: contiene i placeholder delle figure con i parametri di annotazione (quale screenshot, quali callout, quale legenda). Il PDF è il risultato della compilazione di quel sorgente.

---

## 4. Rendering grafico

### 4.1 Trattamento delle immagini

Il trattamento cromatico di default è quasi impercettibile. Gli screenshot vengono presentati con fedeltà cromatica piena: i colori dell'interfaccia ABRAZO — badge colorati, palette scure, testi semantici — appaiono nel PDF esattamente come nella UI reale.

I valori di seguito sono stati validati durante la fase DOC 4.1.1 e rappresentano i parametri definitivi del rendering standard:

| Parametro | Valore validato |
|---|---|
| Saturazione | 100% — nessuna variazione |
| Luminosità | +1% |
| Contrasto | 100% — nessuna variazione |
| Opacità | 100% |

L'unico aggiustamento attivo è la luminosità a +1%, che compensa la resa degli schermi scuri su carta o PDF senza alterare la riconoscibilità dell'interfaccia. Il colore degli screenshot è identico all'originale.

> **Nota — Trattamenti più marcati**: desaturazione, riduzione del contrasto e abbassamento dell'opacità non fanno parte del trattamento default e non devono diventarlo. Potranno essere introdotti in futuro esclusivamente come modalità opzionali esplicite (es. parametro `data-treatment="print"` nel placeholder Markdown), per contesti specifici come la stampa in scala di grigi o il risparmio di inchiostro. Qualunque modifica che degradi la fedeltà cromatica rispetto all'interfaccia originale richiede una scelta editoriale consapevole, non un default silenzioso.

### 4.2 Marker e cerchi numerati

I marker identificano i punti nell'immagine a cui si riferisce ciascun callout. Nel nuovo standard (DOC 4.0) i marker sono posizionati all'esterno del frame immagine, a destra, in colonna verticale.

| Parametro | Valore |
|---|---|
| Forma | Cerchio |
| Diametro | 14–16 px (su PDF A4) |
| Colore riempimento | `#D32F2F` opacità 85% |
| Colore testo | Bianco |
| Font | System font, 10–11 px, peso 800 |
| Posizione | Esterna al frame, colonna destra |

Il diametro di 14–16 px rappresenta una riduzione del 25% rispetto allo standard DOC 3.0 (22 px). La riduzione è necessaria per mantenere le proporzioni eleganti su PDF A4 e per evitare che i marker dominino visivamente sulla legenda.

### 4.3 Linee di richiamo

Ogni marker è collegato al punto nell'immagine che evidenzia tramite una linea sottile. La linea parte dal bordo sinistro del cerchio numerato e raggiunge il punto di destinazione con un tratto orizzontale o a gomito (orizzontale + verticale).

| Parametro | Valore |
|---|---|
| Colore | `#D32F2F` opacità 60% |
| Spessore | 1.5 px |
| Stile | Continua (no tratteggio) |
| Forma | Orizzontale o a gomito (L invertita) |
| Terminazione | Punto di arrivo senza freccia |

L'opacità ridotta (60%) rispetto ai marker (85%) mantiene la linea visibile senza che competa con i cerchi numerati nella gerarchia visiva.

### 4.4 Numerazione figure

Ogni figura porta un identificativo composto:

```
Figura N — Titolo descrittivo (SCN-XXX)
```

Dove:
- `N` è il numero progressivo della figura nel manuale corrente
- `Titolo descrittivo` è un nome operativo breve (3–6 parole)
- `SCN-XXX` è il codice stabile dell'asset nella libreria screenshot, in corpo ridotto e tra parentesi

Il codice SCN è incluso nel titolo per permettere allo staff tecnico di identificare immediatamente quale asset è referenziato, facilitando aggiornamenti futuri.

### 4.5 Impaginazione delle figure

| Regola | Dettaglio |
|---|---|
| Nuova pagina | Se la figura occupa più del 40% della pagina precedente, inizia su una nuova pagina |
| Sequenza | Titolo → Immagine → Didascalia → Legenda |
| Spaziatura | Margine superiore generoso (2em) prima del titolo figura |
| Interruzione di pagina | `page-break-inside: avoid` sull'intero blocco figura |
| Legenda | Sotto la didascalia, mai a lato |
| Colonne | La legenda è sempre a colonna singola, indipendentemente dalla larghezza disponibile |

---

## 5. Libreria screenshot

### 5.1 Struttura

```
docs/screenshots/
├── README.md                    ← catalogo, convenzioni, regole di acquisizione
│
├── public/                      ← SCN-001 … SCN-099: area pubblica
├── segreteria/                  ← SCN-101 … SCN-199: area segreteria
├── partecipante/                ← SCN-201 … SCN-299: pratica partecipante
├── checkin/                     ← SCN-301 … SCN-399: check-in e accoglienza
├── configurazione/              ← SCN-401 … SCN-499: configurazione evento
└── report/                      ← SCN-501 … SCN-599: esportazioni e report
```

### 5.2 Convenzione di naming

```
SCN-NNN-descrizione-kebab-case.png
```

- `SCN` è il prefisso fisso per tutti gli screenshot
- `NNN` è un identificativo numerico stabile che non cambia mai dopo l'assegnazione
- `descrizione` è un nome parlante in kebab-case che descrive il contenuto

Il codice `SCN-NNN` è la chiave di lookup usata dal motore PDF: i placeholder nel sorgente Markdown referenziano gli screenshot per codice, non per path. Questo rende i manuali immuni da riorganizzazioni della libreria.

### 5.3 Catalogo screenshot attivi

| Codice | File | Area | Utilizzato in |
|---|---|---|---|
| SCN-101 | `dashboard-overview.png` | Segreteria | MAN-001, MAN-002 |
| SCN-201 | `pratica-overview.png` | Partecipante | MAN-002, MAN-004 |
| SCN-202 | `pratica-identita-qr.png` | Partecipante | MAN-002, MAN-004 |
| SCN-203 | `pratica-iscrizione.png` | Partecipante | MAN-002, MAN-004 |
| SCN-204 | `pratica-timeline-storico.png` | Partecipante | MAN-002, MAN-004 |

### 5.4 Regole di acquisizione

Ogni screenshot deve essere acquisito rispettando le regole definite in `docs/screenshots/README.md`. In sintesi:

- Dati realistici ma non personali reali
- Nessun popup, tooltip o stato transitorio dell'interfaccia
- Tema grafico ufficiale ABRAZO (dark theme)
- Risoluzione massima disponibile
- Frame completo della sezione, senza ritagli arbitrari
- Nessuna annotazione aggiunta direttamente al PNG

---

## 6. Riutilizzabilità

Il sistema di figure è progettato per essere **completamente indipendente dai singoli manuali**.

### 6.1 Separazione asset / annotazione

Lo stesso PNG (`SCN-101-dashboard-overview.png`) viene usato in MAN-001 per introdurre la dashboard dell'evento e in MAN-002 per illustrare la Segreteria. I callout sono diversi — perché i destinatari sono diversi e le cose rilevanti da evidenziare sono diverse — ma l'asset è lo stesso.

Questa separazione significa che:
- Aggiornare un'immagine (nuova versione dell'interfaccia) richiede di sostituire un solo file
- La rigenerazione PDF di tutti i manuali che la referenziano è automatica e immediata
- Non esistono copie dell'immagine in luoghi diversi che possono andare fuori sincronia

### 6.2 Parametri nel sorgente Markdown

Ogni placeholder di figura nel sorgente Markdown contiene tutti i parametri necessari per la generazione:

```html
<div class="fig-ref"
     data-scn="SCN-101"
     data-title="Dashboard della Segreteria"
     data-caption="Didascalia operativa"
     data-markers="1:30%:50%:Descrizione callout uno|2:47%:17%:Descrizione callout due">
</div>
```

Il motore PDF (`scripts/generate-manual-pdfs.mjs`) legge questi parametri, carica il PNG dalla libreria, applica il rendering e produce l'HTML della figura. Il risultato non è persistito: viene ricalcolato a ogni generazione.

### 6.3 Indipendenza dal motore

Il formato del placeholder è intenzionalmente semplice: un `<div>` HTML standard con attributi `data-`. Questo lo rende:

- Visibile e modificabile in qualsiasi editor di testo
- Indipendente dall'implementazione specifica del motore PDF
- Migrabile su altri motori di rendering (es. Pandoc, WeasyPrint) senza modificare i sorgenti Markdown

---

## 7. Conseguenze

### 7.1 Benefici ottenuti

**Leggibilità operativa**: i callout esterni non occultano mai il contenuto dell'immagine. Un volontario che apre il manuale per la prima volta può vedere l'interfaccia per intero e identificare i punti evidenziati senza che i marker interferiscano con la lettura dello screenshot.

**Manutenibilità**: la libreria centralizzata degli screenshot garantisce che un aggiornamento dell'interfaccia si rifletta su tutta la documentazione rigenerando i PDF. Non esistono screenshot duplicati da aggiornare manualmente in più punti.

**Scalabilità**: il sistema è pronto per coprire tutti gli otto manuali (MAN-001 – MAN-008) senza modifiche strutturali. Ogni nuovo manuale eredita automaticamente lo standard.

**Professionalità**: la documentazione ha la stessa qualità del software che descrive. Questo rafforza la fiducia dello staff nel sistema e riduce la curva di apprendimento.

### 7.2 Limiti

**Posizionamento callout**: il sistema DOC 4.0 con linee di richiamo richiede la definizione delle coordinate del punto di destinazione nell'immagine (espresse in percentuale). Questo posizionamento non è verificabile durante la scrittura del Markdown — è visibile solo nel PDF finale. Aggiustamenti fini richiedono rigenerazioni successive.

**Resistenza ai restyling dell'interfaccia**: se l'interfaccia di ABRAZO cambia significativamente (es. cambio di layout della Segreteria), gli screenshot esistenti diventano obsoleti. Il sistema di libreria centralizzata facilita l'aggiornamento, ma la decisione di aggiornare uno screenshot è sempre manuale.

**Dimensione dei PDF**: ogni PNG embedded come base64 contribuisce alla dimensione del PDF. MAN-002 con 5 screenshot pesa circa 1.2 MB. Con 8 manuali completi e un numero maggiore di figure, la gestione delle dimensioni diventa un parametro da monitorare.

**Linee di richiamo su schermi complessi**: le linee di richiamo funzionano bene su layout con spazio bianco. Su screenshot molto densi (es. tabelle con molte righe), l'angolazione delle linee può creare ambiguità. In questi casi, è preferibile usare più figure separate con zoom su sottosezioni specifiche piuttosto che una figura unica con molti callout.

### 7.3 Evoluzioni future

**Numerazione figure automatica**: il motore attuale richiede che il numero della figura sia specificato nel titolo a mano. Una evoluzione desiderabile è la numerazione automatica progressiva per manuale, derivata dall'ordine di apparizione dei placeholder nel sorgente.

**Generazione delle linee di richiamo via SVG**: il rendering DOC 4.0 introduce le linee di richiamo come elemento tecnico nuovo. L'implementazione standard utilizzerà SVG embedded nell'HTML, con tratto sottile e opacità configurabile. L'SVG è generato a runtime dal motore PDF a partire dalle coordinate dei callout.

**Zoom su sottosezioni**: predisporre un parametro `data-crop` che permette di specificare un'area di ritaglio dell'immagine originale. La figura mostrerebbe solo la porzione rilevante, con callout ridotti. Utile per screenshot ad alta densità informativa.

**Screenshot in alta risoluzione per Retina/HiDPI**: acquisire gli screenshot a 2× risoluzione e scalare il display al 50% in CSS, per una nitidezza superiore su schermi ad alta densità di pixel e in stampa ad alta qualità.

**Versioning degli screenshot**: associare a ogni SCN-NNN una versione o una data di acquisizione, per identificare automaticamente screenshot potenzialmente obsoleti dopo un aggiornamento dell'interfaccia.

---

## 8. Relazione con ADR-003

ADR-003 definisce l'architettura della documentazione operativa di ABRAZO nel suo insieme: la complementarità tra Excel e PDF, il principio di fonte unica, la generazione deterministica, il Book Operativo.

ADR-004 è una specializzazione di ADR-003 limitata al **rendering delle figure illustrate** all'interno dei manuali operativi PDF. Non modifica nessuno dei principi di ADR-003:

- La fonte unica rimane il database (per i dati) e la libreria screenshot (per gli asset visivi)
- La generazione è ancora deterministica: gli stessi parametri nel Markdown producono sempre lo stesso PDF
- Il timestamp rimane presente in header e footer
- Il documento generato non si modifica a mano

ADR-004 aggiunge a ADR-003 la disciplina specifica del rendering illustrato, che ADR-003 non tratta. Le due ADR sono complementari e non si contraddicono.

---

## Stabilità di questa ADR

Questa ADR documenta il **rendering standard definitivo** della documentazione illustrata ABRAZO a partire da DOC 4.0.

- Modifiche ai parametri grafici di dettaglio (colori, dimensioni, spaziature) → aggiornamento di `manual.css` e del motore PDF, con nota nel commit. Non richiedono una nuova ADR.
- Aggiunta di nuovi tipi di figure (es. sequenze animate, diagrammi di flusso) → nuova ADR con campo `Relazioni: ADR-004`.
- Abbandono del motore md-to-pdf in favore di un altro motore → nuova ADR con campo `Supersedes: ADR-004`.
- Modifiche al formato del placeholder Markdown → nuova ADR se il cambiamento è incompatibile con i sorgenti esistenti.
- Correzioni di fatto nel testo → modifica diretta con nota nel commit message.

I principi architetturali documentati qui — callout esterni, separazione asset/annotazione, libreria centralizzata, rendering a runtime, nessuna modifica ai PNG originali — richiedono una nuova ADR per essere cambiati.
