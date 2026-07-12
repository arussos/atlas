# Manuale operativo — Centro Operativo

**Per chi è questo manuale**: tutto lo staff di Art&Tango. Panoramica delle funzioni disponibili e quando usarle.

---

## Cos'è il Centro Operativo

Il **Centro Operativo** è la schermata principale dell'area amministrativa di ABRAZO. Da qui si accede a tutte le funzioni per gestire un evento.

Per accederci: apri ABRAZO nell'area admin, poi clicca sull'evento attivo (es. Epico Tango Fest 2027).

---

## Funzioni disponibili

### Partecipanti
**Descrizione**: Lista iscritti, pratiche e riepiloghi

Mostra tutti gli iscritti all'evento con badge di stato pagamento, ruolo e data iscrizione. Da qui puoi aprire la **Pratica partecipante** di qualsiasi iscritto.

**Quando usarla**: per avere una visione d'insieme di tutte le iscrizioni, per navigare alla pratica di un partecipante specifico quando ne conosci già il nome.

---

### Accoglienza
**Descrizione**: QR, accredito e saldo all'ingresso

Console operativa per il **front desk**. Supporta tre modalità: lettore USB HID (consigliato), fotocamera del dispositivo (scelta esplicita, non si apre da sola), inserimento manuale del codice EVP. Verifica il QR personale del partecipante, mostra lo stato del pagamento (saldato, acconto, da verificare) e registra la presenza all'evento.

**Quando usarla**: all'ingresso principale dell'evento, per tutta la durata dell'accoglienza. È distinta dall'accesso alle singole attività.

Per il manuale dettagliato: [CHECKIN.md — sezione Accoglienza](CHECKIN.md).

---

### Accesso attività
**Descrizione**: Scanner per sale, stage e milonghe

Lista di tutte le attività con metriche (iscritti, presenti, assenti) e due azioni per riga: **"Apri accesso attività"** per aprire lo scanner direttamente, **"Copia link staff"** per copiare il link della pagina scanner da inviare al volontario di sala. Il volontario apre il link sul proprio cellulare e trova lo scanner già impostato sulla sua attività. Non mostra lo stato del pagamento — verifica solo che il partecipante sia iscritto a quell'attività specifica.

**Quando usarla**: prima dell'evento per distribuire i link ai volontari di sala; durante l'evento per monitorare l'affluenza per attività in tempo reale. Non sostituisce l'accoglienza principale.

Per il manuale dettagliato: [CHECKIN.md — sezione Accesso attività](CHECKIN.md).

---

### Ricerca
**Descrizione**: Cerca per nome, email o codice iscrizione

Ricerca rapida su tutti gli iscritti. Supporta nome, cognome, email e codice iscrizione (formato EVP-XXXXXX).

**Quando usarla**: per trovare un partecipante specifico senza scorrere tutta la lista. Utile al banco accoglienza, alla Segreteria o quando un partecipante non ha il QR.

---

### Segreteria
**Descrizione**: Inbox pagamenti e conferme rapide

Inbox operativa con le iscrizioni che richiedono attenzione: chi non ha ancora pagato, chi ha pagato solo l'acconto. Permette di registrare acconti e confermare pagamenti con un click.

**Quando usarla**: ogni mattina per processare i bonifici arrivati. È il punto di lavoro principale per il personale di segreteria.

Per il manuale dettagliato: [SEGRETERIA.md](SEGRETERIA.md).

---

### Situazione economica
**Descrizione**: Incassi, saldi residui e anomalie

Dashboard finanziaria con totale atteso, importo incassato e saldo residuo complessivo. Tabella completa di tutti gli iscritti con importi e stato. Permette di correggere uno stato di pagamento errato (operazione eccezionale).

**Quando usarla**: per avere una visione finanziaria aggregata, per verificare il totale dei saldi ancora aperti, per correggere un errore di stato.

---

### Comunicazioni
**Descrizione**: Anteprima e template email

Anteprima dei template email automatici inviati da ABRAZO (conferma iscrizione, conferma pagamento). Utile per verificare il contenuto prima di un evento.

**Quando usarla**: prima di un evento, per controllare che i template email siano corretti. Non invia email — è solo un'anteprima.

---

### Export Excel
**Descrizione**: Scarica iscrizioni aggiornate

Genera e scarica un file Excel con tre fogli: Iscrizioni, Attività, Riepilogo. I dati sono aggiornati al momento del download.

**Quando usarla**: per reportistica, per condividere i dati con la direzione, per avere una copia offline della lista iscritti.

---

## Riepilogo: chi usa cosa

| Ruolo staff | Funzioni principali |
|---|---|
| **Segreteria** | Segreteria (inbox), Ricerca, Pratica partecipante |
| **Front desk / Accoglienza** | Accoglienza (console scanner ingresso evento) |
| **Staff di sala** | Link distribuito per singola sala (Accesso attività) |
| **Direzione / admin** | Situazione economica, Partecipanti, Export Excel |
| **Tutti** | Ricerca, Pratica partecipante |

---

## Differenza chiave: Accoglienza vs Accesso attività

| | Accoglienza | Accesso attività |
|---|---|---|
| **Chi la usa** | Front desk, ingresso principale | Staff di sala |
| **Cosa verifica** | Iscrizione all'evento + stato pagamento | Iscrizione alla specifica attività |
| **Mostra pagamento** | Sì | No |
| **Dove si usa** | Ingresso del festival | Porta di ogni sala |
| **Sono collegate?** | No — indipendenti | No — indipendenti |

---

*Manuale operativo ABRAZO — Centro Operativo · Art&Tango · Versione RC1 · Luglio 2026*
