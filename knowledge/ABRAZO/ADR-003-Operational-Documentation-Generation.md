# ADR-003 — Generazione della Documentazione Operativa

**Status**: Accepted  
**Date**: 2026-07-06  
**Authors**: Art&Tango / ABRAZO  
**Relazioni**: ADR-001 (payment ledger), ADR-002 (pratica partecipante)

---

## 1. Motivazione

ABRAZO è progettato per la gestione operativa di festival internazionali di tango. Un festival di questo tipo si svolge in un contesto fisico — una villa, un albergo, un centro congressi — dove la connessione di rete non può essere data per scontata. La dipendenza dalla connettività durante le operazioni live è un rischio operativo inaccettabile.

Durante un evento di tre o quattro giorni con centinaia di partecipanti provenienti da più paesi, si possono verificare simultaneamente:

- **Assenza o instabilità della rete** — hotspot mobili che saturano, reti Wi-Fi inadeguate per le strutture, aree dello stabile senza copertura
- **Necessità di documentazione cartacea** — liste di accoglienza, fogli per le sale stage, elenchi di emergenza, documentazione di servizio per i volontari
- **Lavoro distribuito e simultaneo** — la segreteria gestisce i pagamenti, la direzione artistica monitora il bilanciamento dei ruoli, i volontari verificano le prenotazioni in sala, l'accoglienza controlla le presenze
- **Necessità di snapshot immutabili** — documentazione che fotografa lo stato dell'evento in un momento preciso e non cambia, indipendentemente da aggiornamenti successivi nel sistema

La risposta a questi requisiti non è un'applicazione offline complessa. È la possibilità di generare, in qualsiasi momento e con un singolo click, un insieme di documenti pronti per essere stampati e distribuiti allo staff.

Excel e PDF non sono la stessa cosa e non si sostituiscono a vicenda. Hanno destinatari, utilizzi e formati differenti e complementari. L'architettura della documentazione operativa deve trattarli come strumenti distinti, ciascuno con il proprio ruolo.

---

## 2. Principi

### 2.1 Una sola fonte di verità

Tutta la documentazione operativa — Excel, PDF singoli, Book Operativo — è generata a partire dal database di ABRAZO nel momento della richiesta. Non esistono documenti master separati, fogli condivisi con dati inseriti manualmente, o copie sincronizzate. La fonte è sempre e solo il database.

Conseguenza diretta: un documento generato alle 08:00 di domenica mattina riflette lo stato del sistema a quell'ora. Se alle 09:00 viene registrato un nuovo pagamento, il documento generato alle 08:00 rimane valido e immutabile come snapshot.

### 2.2 Excel per il lavoro operativo

Il file Excel è lo strumento di lavoro della segreteria e della direzione. È filtrabile, ordinabile, copiabile, modificabile manualmente per annotazioni. Contiene tutti i fogli operativi dell'evento in un unico file scaricabile.

Excel non è il documento definitivo da stampare. È lo strumento da tenere aperto sul portatile della segreteria.

### 2.3 PDF per la stampa

I PDF sono ottimizzati per la stampa. Layout fisso, dimensioni pagina definite (A4 o formato registro), font leggibili a stampa. Non contengono elementi interattivi. Non si modificano dopo la generazione.

Un PDF non è mai generato per essere lavorato digitalmente — è generato per essere stampato e distribuito.

### 2.4 Book Operativo come raccolta completa

Il Book Operativo è un unico PDF che aggrega tutti i report dell'evento in un documento strutturato e numerato. È il documento di riferimento ufficiale dell'evento: la sua copertina porta data e ora di generazione come elemento di versioning implicito.

Il Book Operativo non è un'alternativa ai PDF singoli — è la loro raccolta ordinata. I PDF singoli rimangono utili per aggiornamenti rapidi di un singolo report; il Book è il documento da consegnare alla direzione o da archiviare.

### 2.5 I PDF non si modificano

Nessun documento PDF generato da ABRAZO è pensato per essere modificato a mano. Se un dato è sbagliato nel PDF, si corregge nel database e si rigenera il documento. Un PDF con dati scritti a penna perde il suo valore come documento ufficiale del sistema.

Eccezione accettata: i campi "Note" nei fallback cartacei sono esplicitamente previsti come spazio per annotazioni manuali durante l'evento. Questa è una scelta progettuale deliberata, non una concessione alla modifica del documento.

### 2.6 Generazione deterministica

Lo stesso insieme di dati, generato in momenti diversi, produce documenti identici. Nessuna componente aleatoria (ordine non deterministico, valori calcolati diversamente). Il timestamp di generazione è l'unico elemento che cambia tra due generazioni successive.

### 2.7 Timestamp e versione su ogni documento

Ogni documento generato riporta, nella sua intestazione o nel footer:

- Data e ora di generazione
- Nome dell'evento
- Titolo del documento

Questi elementi permettono allo staff di identificare immediatamente quale versione di un documento hanno in mano, anche dopo ore di utilizzo in sala.

---

## 3. Excel — Kit Operativo Evento

Il file Excel è il punto di partenza dell'operatività digitale. È scaricabile in qualsiasi momento dalla dashboard amministrativa dell'evento.

### 3.1 Scopo

Il Kit Operativo Excel è lo strumento di lavoro della segreteria durante l'evento. Permette di:

- avere una visione aggregata di tutti gli iscritti con i relativi stati
- filtrare e ordinare per stato pagamento, ruolo, attività
- annotare manualmente informazioni locali (presenze, note operative)
- lavorare anche in assenza di connessione dopo il download

### 3.2 Fogli previsti

| N. | Foglio | Destinatario | Utilizzo |
|---|---|---|---|
| 1 | Numeri del Festival | Direzione | KPI sintetici: iscritti, ruoli, incassi, accoglienza, stage |
| 2 | Riepilogo | Direzione / Segreteria | Panoramica completa con stati pagamento |
| 3 | Controllo Artistico | Direzione Artistica | Bilanciamento leader/follower per stage con stato |
| 4 | Partecipanti | Segreteria | Anagrafica completa con pacchetti e attività |
| 5 | Acquisti | Segreteria | Dettaglio acquisti per partecipante |
| 6 | Attività | Staff / Volontari | Cross-reference attività per verifiche |
| 7 | Segreteria | Segreteria | Ordinato per saldo residuo, con "Da incassare oggi" |
| 8 | Fallback Accoglienza | Accoglienza | Solo dati porta: EVP, nome, ruolo, stato, colonna Note |
| 9 | Fallback Sale | Volontari sala | Per attività, con colonna ampia per segno di presenza |
| 10 | Elenco alfabetico | Staff | Ricerca rapida per cognome: EVP, nome, spazio Note |

### 3.3 Caratteristiche tecniche

- Generato server-side tramite `GET /api/events/[id]/export-xlsx`
- Nome file con date stamp: `{slug}-kit-{YYYYMMDD}.xlsx`
- Intestazioni in grassetto, freeze header, autoFilter attivo su ogni foglio
- Stampa configurata: formato A4, orientamento appropriato per contenuto
- Separatori grafici tra gruppi di attività (Fallback Sale)
- Colori coerenti con palette ABRAZO per i badge di stato pagamento

---

## 4. PDF Operativi

I PDF singoli sono generati su richiesta per utilizzi specifici. Ciascuno è ottimizzato per il proprio destinatario e contesto d'uso.

### 4.1 Lista dei PDF previsti

#### PDF — Accoglienza

| | |
|---|---|
| **Destinatario** | Staff accoglienza all'ingresso dell'evento |
| **Utilizzo** | Lista cartacea per verificare le presenze in assenza di connessione o come backup allo scanner QR |
| **Contenuto** | EVP, Cognome, Nome, Ruolo, Stato pagamento, Colonna "Accolto ✓" vuota, Colonna Note. Ordinato per cognome. Nessun dato economico. |

#### PDF — Segreteria

| | |
|---|---|
| **Destinatario** | Operatori di segreteria durante l'evento |
| **Utilizzo** | Gestione dei pagamenti residui, verifica acconti, annotazioni |
| **Contenuto** | EVP, Cognome, Nome, Email, Totale, Pagato, Residuo, Da incassare, Stato, Ultima operazione. Ordinato per saldo residuo decrescente. |

#### PDF — Controllo Artistico

| | |
|---|---|
| **Destinatario** | Direzione artistica |
| **Utilizzo** | Monitoraggio bilanciamento leader/follower per ogni stage durante il festival |
| **Contenuto** | Per ogni stage: titolo, orario, sala, maestri, contatori Leader/Follower/Entrambi, differenza, fabbisogno, capienza, posti residui, stato (bilanciato/lieve/importante), colonna Note Direzione. |

#### PDF — Lista per attività (uno per attività)

| | |
|---|---|
| **Destinatario** | Volontario assegnato alla sala |
| **Utilizzo** | Verifica prenotazioni e presenze in sala durante lo stage o la milonga |
| **Contenuto** | Intestazione con titolo attività, sala, orario, maestri. Tabella con EVP, Cognome, Nome, Ruolo, Colonna "Entrato ✓" ampia per segno manuale. Un PDF per ogni attività pubblica dell'evento. |

#### PDF — Elenco alfabetico

| | |
|---|---|
| **Destinatario** | Staff generico, reception struttura, direzione |
| **Utilizzo** | Ricerca rapida di un partecipante per cognome |
| **Contenuto** | EVP, Cognome, Nome, Colonna Note. Nessun dato economico o di stato. Ordinato alfabeticamente per cognome. |

#### PDF — Situazione economica

| | |
|---|---|
| **Destinatario** | Direzione, tesoriere associazione |
| **Utilizzo** | Snapshot dello stato finanziario dell'evento al momento della generazione |
| **Contenuto** | KPI economici (totale atteso, incassato, residuo), distribuzione per stato pagamento, riepilogo per pacchetto, eventuali anomalie rilevate. |

### 4.2 Caratteristiche tecniche comuni

- Generazione server-side tramite endpoint dedicati: `GET /api/events/[id]/pdf/{tipo}`
- Nome file descrittivo con data stamp
- Nessuna dipendenza da librerie lato client
- Layout A4, margini definiti, font leggibile a stampa
- Intestazione con logo ABRAZO, nome evento, titolo documento, data generazione
- Footer con numero pagina e timestamp
- Ottimizzato per stampa in bianco e nero (nessun elemento grafico che perde leggibilità senza colore)

---

## 5. Book Operativo

### 5.1 Definizione

Il Book Operativo è un unico file PDF che raccoglie automaticamente tutti i report dell'evento in un documento strutturato, numerato e con indice. Rappresenta la **fotografia ufficiale dell'evento** nel momento esatto della sua generazione.

Il Book non è una somma meccanica di PDF singoli. Ha una copertina propria, un indice cliccabile, una numerazione di pagina unificata e una identità grafica coerente dall'inizio alla fine.

### 5.2 Indice previsto

| Sezione | Contenuto |
|---|---|
| **Copertina** | Nome evento, date, sede, data e ora di generazione, logo ABRAZO e logo evento |
| **Numeri del Festival** | KPI sintetici dell'evento (iscritti, ruoli, incassi, accoglienza, statistiche stage) |
| **Dashboard artistica** | Bilanciamento leader/follower per ogni stage con stato visivo |
| **Situazione economica** | Snapshot finanziario: incassi, residui, distribuzione per stato |
| **Partecipanti** | Lista completa partecipanti con pacchetti e stato |
| **Accoglienza** | Lista ordinata per cognome per l'ingresso evento |
| **Stage** | Una sezione per ogni stage con lista prenotati |
| **Milonghe** | Una sezione per ogni milonga con lista prenotati |
| **Elenco alfabetico** | Ricerca rapida per cognome |
| **Contatti utili** | Recapiti organizzazione, emergenze, struttura (configurabili) |
| **Colophon** | Data e ora di generazione, versione software, evento |

### 5.3 Utilizzo

Il Book è il documento da:
- consegnare alla direzione prima dell'inizio del festival
- stampare in copie limitate per la segreteria e la direzione artistica
- archiviare come documentazione ufficiale dell'evento
- distribuire ai referenti della struttura ospitante

### 5.4 Caratteristiche tecniche

- Generazione server-side tramite `GET /api/events/[id]/book-operativo`
- La generazione può richiedere alcuni secondi: il server aggrega tutti i dati e compone il documento
- Nome file: `{slug}-book-operativo-{YYYYMMDD-HHmm}.pdf`
- Dimensione stimata: 20–80 pagine a seconda della dimensione dell'evento
- Il Book è generabile in qualsiasi momento; si raccomanda di generarne una copia definitiva la sera prima dell'evento e una il giorno di apertura dopo l'ultima conferma pagamenti

---

## 6. Layout grafico

Tutti i documenti generati da ABRAZO — Excel e PDF — condividono un'identità grafica coerente. Non si tratta di un requisito estetico secondario: la coerenza visiva permette allo staff di riconoscere immediatamente un documento ufficiale ABRAZO da una stampa non aggiornata o da un documento esterno.

### 6.1 Elementi comuni a tutti i PDF

Ogni pagina di ogni documento PDF include:

- **Intestazione**: logo ABRAZO (in basso a sinistra rispetto al titolo) + nome evento + titolo documento
- **Numero pagina**: in basso a destra, formato "Pagina N di M"
- **Data e ora di generazione**: in basso al centro o a sinistra
- **Footer**: separatore sottile + nome organizzazione

### 6.2 Identità grafica

| Elemento | Specifica |
|---|---|
| Font titoli | Cormorant Garamond o equivalente, peso 600–700 |
| Font testo | Geist Sans o equivalente system font, leggibile a piccoli corpi |
| Font monospace | Geist Mono per codici EVP e dati tecnici |
| Colore primario | `#C89A4A` (oro ABRAZO) per intestazioni e accenti |
| Colore testo | Nero su bianco per la stampa |
| Sfondo | Bianco puro (`#FFFFFF`) per tutti i PDF — nessuno sfondo scuro |
| Bordi tabelle | Sottili, colore neutro scuro |

### 6.3 Ottimizzazione per stampa

I PDF di ABRAZO devono essere leggibili in stampa in bianco e nero. Nessun elemento informativo critico è veicolato solo dal colore. I badge di stato (pagamento, bilanciamento stage) usano il colore come rinforzo visivo, ma il testo del badge è sempre sufficiente a trasmettere l'informazione.

### 6.4 Identità visiva di evento

Ogni evento in ABRAZO può avere un proprio logo (campo `logo_url` previsto nel modello dati). Se disponibile, il logo dell'evento appare in copertina del Book Operativo e nell'intestazione dei PDF dell'evento. In assenza del logo evento, appare solo il logo ABRAZO.

---

## 7. Estensioni future

Le seguenti estensioni non sono parte della presente decisione architetturale ma sono state valutate come coerenti con il modello e non richiedono refactoring strutturale per essere implementate.

### 7.1 QR code nei report

I PDF di accoglienza e i PDF per sala potrebbero includere un QR code per ogni partecipante, da usare come punto di scan alternativo allo scanner principale. Richiede solo l'aggiunta del QR PNG già disponibile su Supabase Storage all'interno del template PDF.

### 7.2 Firma digitale

Il Book Operativo e i PDF economici possono essere firmati digitalmente come documenti ufficiali dell'associazione. La firma è applicabile a livello di file PDF finale senza modificare il pipeline di generazione.

### 7.3 Watermark di stato

I documenti possono ricevere un watermark dinamico che ne indica lo stato al momento della generazione: "BOZZA", "VERSIONE UFFICIALE", "NON AGGIORNATO — Generato il {data}". Utile per distinguere versioni intermedie da documenti definitivi.

### 7.4 Export ZIP con tutti i PDF

Un endpoint `GET /api/events/[id]/export-all-pdf` genera un archivio ZIP contenente tutti i PDF singoli dell'evento. Permette di scaricare l'intera documentazione in un unico download, per backup o distribuzione interna.

### 7.5 Invio automatico via email

Il Book Operativo e la Situazione Economica possono essere inviati automaticamente via email a una lista di destinatari configurata per evento (direzione, tesoriere, referente struttura). Trigger configurabili: generazione manuale, apertura evento, chiusura evento.

### 7.6 Esportazione multilingua

I report destinati ai partecipanti internazionali (lista per sala, PDF personali) possono essere generati in italiano e in inglese. Il modello dati supporta già il campo `language` su `event_participants`. I template dovranno prevedere la variante EN.

---

## 8. Decisione

ABRAZO adotta un modello di documentazione operativa strutturato in quattro livelli complementari e non sostituibili:

| Livello | Strumento | Scopo | Formato |
|---|---|---|---|
| **Fonte dati** | Database Supabase | Unica fonte di verità per tutti i documenti | — |
| **Operativo digitale** | Excel — Kit Operativo | Lavoro di segreteria, filtri, annotazioni, analisi | `.xlsx` |
| **Stampa selettiva** | PDF Operativi | Documenti per ruolo specifico, ottimizzati per stampa | `.pdf` |
| **Documento ufficiale** | Book Operativo | Fotografia completa dell'evento, archivio | `.pdf` |

Questa architettura garantisce:

- **Continuità operativa** anche in assenza totale di connettività, grazie ai documenti scaricabili e stampabili
- **Separazione dei destinatari** — ogni documento è progettato per chi lo usa, non per tutti
- **Immutabilità degli snapshot** — un documento generato è la fotografia di quel momento
- **Coerenza della fonte** — tutti i documenti derivano dallo stesso dato, eliminando le discrepanze tra copie diverse

---

> *"ABRAZO non deve dipendere dalla disponibilità della rete durante un evento. Ogni informazione necessaria alla gestione operativa deve poter essere prodotta, stampata e consultata in qualsiasi momento. La documentazione operativa diventa parte integrante del sistema e non un semplice export."*

---

## Stabilità di questa ADR

Le ADR documentano decisioni architetturali al momento in cui vengono prese. Questa ADR è da considerarsi stabile.

- Modifiche all'architettura della documentazione (nuovi strumenti, nuovi livelli, abbandono di un livello) → nuova ADR con campo `Supersedes: ADR-003`
- Aggiunta di nuovi fogli Excel o nuovi PDF → aggiornamento di `docs/` e `CLAUDE.md`, non di questa ADR
- Modifiche al layout grafico specifico → aggiornamento dei template, non di questa ADR
- Correzioni di fatto (errori materiali nel testo) → modifica diretta con nota in commit message

Le decisioni architetturali documentate qui — complementarità Excel/PDF, fonte dati unica, generazione deterministica, timestamp su ogni documento, separazione per destinatario — richiedono una nuova ADR per essere cambiate.
