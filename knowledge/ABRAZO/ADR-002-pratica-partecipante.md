# ADR-002 — La Pratica Partecipante come centro operativo del Backoffice

**Status**: Accepted
**Date**: 2026-07-05
**Authors**: Art&Tango / ABRAZO
**Relazioni**: ADR-001 (payment ledger)

---

## Contesto

Il backoffice di ABRAZO si è sviluppato con una logica function-first: ogni area operativa (Segreteria, Pagamenti, Ricerca, Partecipanti) è una pagina con le proprie azioni dirette. Questa architettura genera frammentazione del workflow. La segreteria deve navigare tra più superfici per completare il lavoro su un singolo partecipante, e non esiste un punto unico che ne rappresenti lo stato completo.

Con RC1, ABRAZO non è più un MVP sperimentale. È un prodotto operativo che la segreteria di Art&Tango usa quotidianamente. La coerenza dell'interfaccia e la semplicità operativa diventano requisiti primari.

---

## Decisione

La **Pratica Partecipante** — la pagina `/admin/events/[id]/participants/[participantId]` — è il centro operativo del backoffice. Ogni registrazione ha una pratica unica che ne contiene tutte le informazioni e tutte le azioni disponibili.

**Principio architetturale fondamentale:**

> Nessuna lista del backoffice deve contenere logiche operative primarie.
> Le liste servono esclusivamente a ricercare, filtrare, monitorare e aprire la pratica.

---

## Struttura del backoffice

### Centro Operativo `/admin`

Punto di ingresso generale. Mostra lo stato sintetico dell'evento attivo e permette di scegliere l'evento. Non è un luogo operativo di dettaglio.

### Dashboard Evento `/admin/events/[id]`

Hub dell'evento. Accesso rapido a tutte le aree operative e di configurazione. Non è il luogo dove si lavora sulla singola registrazione.

### Liste operative

Le seguenti pagine servono esclusivamente a trovare, filtrare e aprire la pratica:

| Pagina | Funzione |
|---|---|
| Segreteria | Inbox filtrata per stato pagamento |
| Situazione economica | Monitoraggio economico aggregato |
| Ricerca | Ricerca libera per nome, email, codice |
| Partecipanti | Lista completa con filtro visivo |

**Le liste non devono contenere pulsanti di azione primaria.** Possono contenere al massimo operazioni eccezionali amministrative, esplicitamente marcate come tali e visivamente distinte.

### Pratica Partecipante `/admin/events/[id]/participants/[participantId]`

Centro operativo della singola registrazione. Organizzata in macro-sezioni:

**IDENTITÀ**
QR code, nome, ruolo, contatti, codice partecipante.

**ISCRIZIONE**
Pacchetti acquistati, attività prenotate, riepilogo iscrizione.

**SITUAZIONE ECONOMICA**
Ledger pagamenti da `registration_payments`, outstanding calcolato, stato pagamento, azioni operative condizionali (conferma acconto, conferma saldo).

**OPERAZIONI**
Sezione predisposta per crescita futura. In RC1: azioni di pagamento. Futuro: aggiungi attività, aggiungi pacchetto, invia email, rigenera QR, cambio ruolo, rimborsi, ecc.

**STORICO**
Timeline audit, eventi GDPR, note staff.

---

## Navigazione

Ogni link verso la pratica porta `?from=` per il link di ritorno contestuale. La pratica legge il parametro da `searchParams` e renderizza il back link appropriato.

| Origine | Parametro | Link di ritorno mostrato |
|---|---|---|
| Segreteria | `?from=segreteria` | ← Segreteria |
| Situazione economica | `?from=payments` | ← Situazione economica |
| Partecipanti | `?from=participants` | ← Partecipanti |
| Ricerca | `?from=search` | ← Ricerca |
| Assente o non valido | — | ← Partecipanti (fallback) |

**Breadcrumb secondario**: la pratica mostra sempre il nome dell'evento come link verso la dashboard evento, indipendentemente dal `from`.

**Nessuna logica server**: il `?from=` è letto solo per costruire il link di ritorno. Non influenza dati, azioni o redirect. Valori non riconosciuti cadono nel fallback.

---

## Non cambia

Schema DB, Server Actions, ADR-001 (payment ledger), QR code, flusso di iscrizione pubblica, layout base delle pagine lista.

---

## Conseguenze

### Positive

- Punto unico di operatività: la segreteria sa sempre dove trovare e usare tutte le funzioni su un partecipante.
- Le liste diventano più leggibili: nessun pulsante, solo dati e link.
- La pratica è progettata per crescere: la sezione OPERAZIONI accoglierà funzioni future senza cambiare la struttura della pagina.
- Coerenza del linguaggio: tutti i link verso la pratica usano "Apri pratica" come testo.
- Il rename "Pagamenti" → "Situazione economica" chiarisce il ruolo della pagina.

### Negative / Attenzioni

- **Transizione**: durante il refactoring, alcune liste mantengono temporaneamente pulsanti operativi per non degradare la funzionalità. La rimozione avviene solo dopo che la pratica li ha. Sequenza obbligata: implementare nella pratica → rimuovere dalle liste.
- **"Rimetti pending"**: rimane in "Situazione economica" come operazione eccezionale amministrativa finché la pratica non la include esplicitamente. È l'unica eccezione temporanea al principio "nessuna azione nelle liste".

---

## Stabilità

Questa ADR è stabile. Richiedono una nuova ADR che la supera o integra:

- Aggiungere un nuovo livello di navigazione nel backoffice
- Modificare il principio "nessuna lista contiene logiche operative primarie"
- Introdurre una seconda tipologia di pratica (es. pratica evento, pratica volontario)

Non richiedono una nuova ADR:

- Aggiungere sezioni o azioni all'interno della pratica partecipante
- Modificare il layout delle sezioni esistenti
- Aggiungere filtri o colonne alle liste
