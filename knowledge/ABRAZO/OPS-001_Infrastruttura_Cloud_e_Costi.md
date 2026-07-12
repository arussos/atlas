# Proposta tecnica ed economica — Infrastruttura Cloud e Costi Operativi

**Destinatari**: Consiglio Direttivo di Art&Tango.

---

## 1. Introduzione

ABRAZO è stato costruito utilizzando un insieme ristretto di servizi cloud, selezionati con un criterio preciso: ciascuno deve fare una sola cosa, farla bene, e poter essere sostituito indipendentemente dagli altri.

Questa impostazione risponde a sei obiettivi progettuali:

| Obiettivo | Significato pratico |
|---|---|
| **Semplicità** | Pochi strumenti, facili da gestire anche senza competenze specialistiche |
| **Affidabilità** | Tutti i servizi offrono garanzie di disponibilità superiori al 99,9% |
| **Scalabilità** | L'infrastruttura si adatta automaticamente al numero di iscritti e di eventi, senza interventi manuali |
| **Costi sostenibili** | Il costo mensile nella fase attuale è zero; la crescita futura è prevedibile e programmabile |
| **Facilità di manutenzione** | Nessun server fisico da gestire, nessun aggiornamento manuale, nessun hardware da acquistare |
| **Assenza di lock-in** | Ogni componente è uno standard di mercato: può essere sostituito senza perdere i dati né il software sviluppato |

L'Associazione Art&Tango non gestisce alcuna infrastruttura fisica: nessun server, nessun data center, nessun cavo. Tutto avviene nel cloud, accessibile da qualsiasi browser, in qualsiasi luogo, in qualsiasi momento.

---

## 2. Panoramica dell'infrastruttura

La tabella seguente permette di comprendere l'intera architettura di ABRAZO in un colpo d'occhio: cosa fa ciascun componente, com'è configurato oggi e dove è diretta la sua evoluzione.

| Componente | Funzione | Situazione attuale | Evoluzione prevista |
|---|---|---|---|
| **Dominio internet** | Indirizzo web di ABRAZO e mittente delle email ai partecipanti | Passaggio amministrativo da completare prima della produzione | Registrazione intestata all'Associazione; configurazione come mittente ufficiale delle email |
| **Vercel** | Ospita e distribuisce l'applicazione web in tutto il mondo, gestisce i picchi di traffico | Piano gratuito attivo — sufficiente per sviluppo e test | Mantenimento del piano gratuito per il lancio iniziale; rivalutazione dopo il primo evento sulla base del traffico reale |
| **Supabase** | Conserva tutti i dati: iscritti, eventi, pagamenti, check-in, QR code; gestisce l'accesso dello staff | Piano gratuito attivo — sufficiente per sviluppo e test | Attivazione del piano Pro prima della produzione; include backup automatici giornalieri e database sempre attivo |
| **Resend** | Invia le email automatiche ai partecipanti: conferme iscrizione con QR code, ricevute di pagamento | Piano gratuito attivo — sufficiente per Epico Tango Fest 2027 | Mantenimento del piano gratuito; eventuale upgrade solo se i volumi email crescessero significativamente |

---

## 3. Architettura attuale

ABRAZO è composto da quattro componenti indipendenti che collaborano in sequenza per gestire ogni iscrizione e ogni evento.

<div style="display:flex;flex-direction:column;align-items:center;gap:0;margin:2.2em auto;max-width:460px;font-family:system-ui,-apple-system,sans-serif;">
<div style="background:#f4efe7;border:1.5px solid #c89a4a;border-radius:8px;padding:14px 36px;text-align:center;font-weight:700;font-size:0.92em;color:#0f0f0f;min-width:220px;">Partecipante</div>
<div style="color:#c89a4a;font-size:1.6em;line-height:1.1;font-weight:300;margin:2px 0;">↓</div>
<div style="background:#fff8f8;border:1.5px solid #ef3340;border-radius:8px;padding:14px 36px;text-align:center;min-width:220px;"><div style="font-weight:700;font-size:0.92em;color:#0f0f0f;">Vercel</div><div style="font-size:0.78em;color:#555;margin-top:3px;">Applicazione web</div></div>
<div style="color:#c89a4a;font-size:1.6em;line-height:1.1;font-weight:300;margin:2px 0;">↓</div>
<div style="background:#fff8f8;border:1.5px solid #ef3340;border-radius:8px;padding:14px 36px;text-align:center;min-width:220px;"><div style="font-weight:700;font-size:0.92em;color:#0f0f0f;">Supabase</div><div style="font-size:0.78em;color:#555;margin-top:3px;">Database · Storage · Autenticazione</div></div>
<div style="color:#c89a4a;font-size:1.6em;line-height:1.1;font-weight:300;margin:2px 0;">↓</div>
<div style="background:#fff8f8;border:1.5px solid #ef3340;border-radius:8px;padding:14px 36px;text-align:center;min-width:220px;"><div style="font-weight:700;font-size:0.92em;color:#0f0f0f;">Resend</div><div style="font-size:0.78em;color:#555;margin-top:3px;">Invio email</div></div>
<div style="color:#c89a4a;font-size:1.6em;line-height:1.1;font-weight:300;margin:2px 0;">↓</div>
<div style="background:#f4efe7;border:1.5px solid #c89a4a;border-radius:8px;padding:14px 36px;text-align:center;font-weight:700;font-size:0.92em;color:#0f0f0f;min-width:220px;">Partecipante</div>
</div>

### Vercel — Applicazione web

Vercel ospita e distribuisce l'applicazione ABRAZO in tutto il mondo. Quando un partecipante apre il form di iscrizione, o quando un operatore accede alla dashboard, è Vercel a rispondere alla richiesta.

**Ruolo**: mostrare le pagine dell'applicazione agli utenti, ricevere le iscrizioni, comunicare con il database.

### Supabase — Database e servizi dati

Supabase conserva tutti i dati: gli iscritti, i pagamenti, le attività prenotate, i check-in. Gestisce anche i QR code e l'autenticazione dello staff amministrativo.

**Ruolo**: custodire in modo sicuro e affidabile tutte le informazioni dell'Associazione.

### Resend — Invio email

Resend è il servizio che invia le email automatiche: la conferma di iscrizione con QR code, la ricevuta di pagamento, e in futuro i reminder e le comunicazioni di massa.

**Ruolo**: consegnare le email ai partecipanti con alta affidabilità, evitando che finiscano nello spam.

### Dominio internet

Il dominio è l'indirizzo web di ABRAZO: quello che i partecipanti digitano nel browser per iscriversi, e quello che compare nel mittente delle email. Il dominio deve essere intestato all'Associazione Art&Tango.

**Ruolo**: identificare ABRAZO come strumento ufficiale dell'Associazione, non come un servizio generico.

---

## 4. I servizi utilizzati

### Vercel

Vercel è la piattaforma scelta per eseguire ABRAZO. Si occupa di tutto ciò che serve per rendere l'applicazione disponibile su internet: installazione, aggiornamenti, distribuzione in tutto il mondo, gestione dei picchi di traffico.

**Perché è stato scelto**

Next.js — il framework con cui è scritto ABRAZO — è sviluppato dalla stessa azienda che ha creato Vercel. L'integrazione è nativa e ottimizzata, il deploy avviene con un singolo click, e le prestazioni sono superiori rispetto a qualsiasi alternativa.

**Vantaggi**

- Nessun server da configurare o aggiornare
- Distribuisce automaticamente l'applicazione su server in Europa, minimizzando i tempi di caricamento
- Gestisce da solo i picchi di traffico: se cento persone si iscrivono nello stesso momento, non rallenta
- Ogni modifica al software viene pubblicata in pochi secondi

**Sostituibilità**: Vercel è sostituibile in qualsiasi momento. L'applicazione ABRAZO funziona su qualsiasi piattaforma compatibile con Next.js — incluse soluzioni auto-ospitate. Cambiare piattaforma non richiede modifiche al software.

> **Nota**: oggi viene utilizzato il piano gratuito. È sufficiente per la fase attuale di sviluppo e test. Prima del deploy in produzione con dati reali, si valuterà l'eventuale passaggio a un piano a pagamento in base al traffico effettivo.

---

### Supabase

Supabase è il cuore di ABRAZO: ospita il database con tutti i dati dell'Associazione, gestisce l'autenticazione dello staff e conserva i QR code generati per i partecipanti.

**Componenti utilizzati**

| Componente | Utilizzo in ABRAZO |
|---|---|
| **Database PostgreSQL** | Iscritti, eventi, pacchetti, attività, pagamenti, check-in |
| **Autenticazione** | Accesso sicuro per lo staff amministrativo |
| **Storage** | Conservazione dei QR code in formato immagine |
| **API automatica** | Comunicazione sicura tra l'applicazione e il database |
| **Backup** | Snapshot giornalieri automatici del database |
| **Sicurezza** | Crittografia dei dati, accessi per ruolo, conformità GDPR |

**Perché è stato scelto**

Supabase ha permesso di costruire un sistema completo — database, autenticazione, storage, sicurezza — senza dover acquistare, configurare e mantenere infrastrutture separate. Questo ha ridotto significativamente i tempi di sviluppo e il costo totale del progetto.

Il database di Supabase è PostgreSQL: lo standard open-source più diffuso al mondo per applicazioni professionali. I dati sono sempre di proprietà dell'Associazione e possono essere esportati in qualsiasi momento.

**Protezione dei dati e backup**

Il database viene sottoposto a backup automatici giornalieri gestiti direttamente da Supabase, senza alcun intervento manuale. L'infrastruttura è gestita professionalmente da un'azienda con datacenter in Europa, con certificazioni di sicurezza riconosciute a livello internazionale. ABRAZO è stato progettato seguendo criteri di sicurezza e protezione dei dati fin dalle prime fasi di sviluppo: i dati dei partecipanti sono separati dai dati di sistema, gli accessi sono differenziati per ruolo, e ogni operazione viene tracciata in un registro immutabile. Prima del passaggio alla produzione con dati reali, saranno completate le normali attività amministrative previste dalla normativa europea per i servizi cloud — documentate in dettaglio nel capitolo dedicato alla conformità GDPR.

**Sostituibilità**: Supabase può essere sostituito con qualsiasi altro database PostgreSQL — incluse soluzioni completamente auto-ospitate — senza modificare il software ABRAZO. I dati rimangono sempre dell'Associazione.

---

### Resend

Resend è il servizio che garantisce la consegna delle email ai partecipanti. Non è un semplice "invio email": è un'infrastruttura professionale che gestisce la reputazione del mittente, il monitoraggio delle consegne, e la conformità agli standard anti-spam.

**Utilizzo attuale**

- Email di conferma iscrizione con QR code personale
- Email di conferma pagamento
- Comunicazioni operative agli iscritti

**Utilizzi futuri previsti**

- Reminder pre-evento (es. "l'evento inizia tra 7 giorni")
- Comunicazioni di massa a tutti gli iscritti di un evento
- Notifiche allo staff per nuove iscrizioni o pagamenti ricevuti

**Perché è stato scelto**: Resend è progettato per sviluppatori che integrano l'email nelle applicazioni. L'integrazione con ABRAZO è semplice, affidabile, e garantisce che le email raggiungano la casella di posta dei partecipanti senza essere classificate come spam.

---

### Dominio internet

Il dominio è l'identità pubblica di ABRAZO su internet. È l'indirizzo che i partecipanti digitano per iscriversi e il mittente delle email di conferma.

**Esempi di dominio possibili**

- `abrazo.artetango.it`
- `eventi.artetango.it`
- `iscrizioni.artetango.it`

Il dominio deve essere intestato all'Associazione Art&Tango, non al responsabile tecnico. Questo garantisce che l'Associazione mantenga sempre il controllo della propria identità digitale, indipendentemente da chi gestisce il software.

> **Attenzione**: finché il dominio non è configurato, le email di ABRAZO vengono inviate da un indirizzo di test del fornitore. Questo è accettabile in fase di sviluppo, ma non in produzione: i partecipanti devono ricevere email da un indirizzo riconoscibile e professionale.

---

## 5. Situazione economica attuale

Nella fase attuale di sviluppo e collaudo, tutti i servizi funzionano con piani gratuiti.

| Servizio | Piano | Costo mensile |
|---|---|---|
| Dominio internet | Non ancora acquistato | € 0 |
| Vercel | Free | € 0 |
| Supabase | Free | € 0 |
| Resend | Free | € 0 |
| **Totale** | | **€ 0 / mese** |

Questa configurazione è intenzionale: nella fase di prototipazione non ha senso sostenere costi fissi prima di aver validato il sistema con un evento reale.

> **Nota**: i piani gratuiti hanno limitazioni (numero di utenti, volume di email, spazio di archiviazione) che sono adeguate per lo sviluppo, ma non per un utilizzo in produzione continuativo. La transizione ai piani a pagamento è parte del piano di rilascio.

---

## 6. Configurazione consigliata per la messa in produzione

Prima di utilizzare ABRAZO con partecipanti reali per Epico Tango Fest 2027, è necessario attivare i piani a pagamento per i servizi che lo richiedono.

| Servizio | Piano consigliato | Costo indicativo |
|---|---|---|
| Dominio internet | Registrazione `.it` o `.org` | 10–20 € / anno |
| Vercel | Hobby (gratuito) o Pro se necessario | 0–20 € / mese |
| Supabase | Pro | circa 25 USD / mese |
| Resend | Free (sufficiente per RC1) | 0 USD |

**Chiarimento su Vercel Pro**

Il piano Pro di Vercel **non è obbligatorio** per il lancio. Il piano gratuito supporta applicazioni in produzione senza limiti di traffico per un singolo progetto. Il passaggio a Pro potrebbe diventare necessario solo se l'Associazione decidesse di gestire più eventi in parallelo su domini separati, o se il traffico superasse soglie molto elevate. Questa valutazione verrà fatta sulla base dei dati reali dopo il primo evento.

**Chiarimento su Supabase Pro**

Il piano Pro di Supabase è necessario in produzione per due motivi: i backup automatici giornalieri con ripristino point-in-time (non disponibili nel piano gratuito), e l'assenza di pausa automatica del database dopo periodi di inattività. Il costo è fisso e prevedibile.

---

## 7. Evoluzione futura

ABRAZO è stato progettato fin dall'inizio per gestire tutti gli eventi di Art&Tango, non solo Epico Tango Fest. La stessa infrastruttura supporterà senza modifiche:

- **Epico Tango Fest** — festival annuale con iscrizioni complesse, pacchetti e stage
- **Milonghe** — serate di ballo con biglietteria semplice e check-in rapido
- **Workshop e stage** — attività didattiche a capienza limitata
- **Corsi ricorrenti** — gestione abbonamenti e iscrizioni abituali
- **Qualsiasi formato futuro** — l'architettura è parametrica e non dipende da un tipo specifico di evento

Ogni nuovo evento viene creato nel sistema senza modifiche al software: si configurano date, pacchetti e attività, e il form di iscrizione pubblica si aggiorna automaticamente.

L'infrastruttura cloud si scala in modo trasparente: che ci siano 50 iscritti o 500, il sistema si comporta allo stesso modo senza richiedere interventi tecnici o costi aggiuntivi al di fuori delle soglie previste dal piano Pro.

---

## 8. Stima dei costi annuali

Le stime seguenti sono indicative e basate sui listini ufficiali dei fornitori a luglio 2026. I costi in USD sono indicati a cambio orientativo 1:1 con l'euro per semplicità.

### Scenario minimo

Adatto per Associazioni che utilizzano già Vercel gratuito e vogliono minimizzare i costi fissi.

| Voce | Costo annuo |
|---|---|
| Dominio internet `.it` | ~15 € |
| Supabase Pro (25 USD/mese × 12) | ~300 € |
| Vercel Hobby (gratuito) | € 0 |
| Resend Free | € 0 |
| **Totale scenario minimo** | **~315 € / anno** |

> **Consiglio**: per avere un riferimento immediato — lo scenario minimo (≈ **315 €/anno**) equivale a circa **26 € al mese**: meno del costo di una singola iscrizione a uno stage professionale.

### Scenario consigliato

Include Vercel Pro per garantire SLA completo, supporto prioritario e funzionalità avanzate di monitoraggio.

| Voce | Costo annuo |
|---|---|
| Dominio internet `.it` | ~15 € |
| Supabase Pro (25 USD/mese × 12) | ~300 € |
| Vercel Pro (20 USD/mese × 12) | ~240 € |
| Resend Free o Starter | 0–96 € |
| **Totale scenario consigliato** | **~555–651 € / anno** |

**Raccomandazione**: partire con lo scenario minimo per Epico Tango Fest 2027. Rivalutare Vercel Pro solo dopo aver misurato il traffico reale del primo evento.

<div style="border:2px solid #c89a4a;border-radius:10px;padding:24px 28px;margin:2.5em 0;background:#111;">
<div style="color:#c89a4a;font-size:0.75em;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:16px;">Decisione proposta al Consiglio Direttivo</div>
<ul style="margin:0;padding-left:1.4em;color:#f4efe7;line-height:2.2;">
<li>Registrazione del dominio ufficiale dell'Associazione</li>
<li>Attivazione del piano Supabase Pro</li>
<li>Mantenimento del piano gratuito Vercel nella fase iniziale</li>
<li>Mantenimento del piano gratuito Resend</li>
<li>Rivalutazione dei costi dopo il primo Epico Tango Fest</li>
</ul>
</div>

---

## 9. Conformità GDPR e responsabilità dell'Associazione

ABRAZO è stato progettato tenendo conto dei principi del Regolamento Europeo per la Protezione dei Dati (GDPR) fin dalle prime fasi di sviluppo. Questa sezione illustra la situazione attuale e le attività amministrative da completare prima del passaggio alla produzione con dati reali di partecipanti.

Le attività descritte sono la normale documentazione amministrativa richiesta da qualsiasi servizio digitale che tratti dati personali. Non richiedono modifiche al software, non bloccano lo sviluppo, e non impediscono la demo.

### Come ABRAZO gestisce i dati dei partecipanti

I dati raccolti al momento dell'iscrizione sono limitati allo stretto necessario: nome, cognome, email, ruolo nel ballo (leader o follower) e lingua di preferenza. Nessun dato aggiuntivo viene richiesto né conservato.

I QR code generati per ciascun partecipante non contengono dati personali leggibili: sono codici identificativi opachi, nel formato `ABRAZO:EVP:EVP-XXXXXX`. Chiunque fotografasse il QR di un partecipante non otterrebbe alcuna informazione personale.

Ogni operazione sui dati — iscrizione, modifica dello stato di pagamento, check-in — viene registrata in un archivio immutabile con data, ora e operatore. Questo registro è la prova documentale di ogni trattamento effettuato.

I consensi al trattamento dei dati vengono raccolti in modo esplicito e separato durante l'iscrizione: tre consensi distinti (trattamento dati per gestione evento, accettazione del regolamento, utilizzo di foto e video) ciascuno con il proprio timestamp.

I dati rimangono sempre di proprietà dell'Associazione Art&Tango e possono essere esportati in qualsiasi momento in formato aperto, senza dipendere dal fornitore del software.

### I fornitori cloud e la documentazione GDPR

I fornitori scelti per ABRAZO — Supabase, Vercel, Resend — mettono già a disposizione tutta la documentazione normalmente richiesta dalla normativa europea per i trattamenti affidati a fornitori esterni.

Il documento principale è il **Data Processing Agreement (DPA)**, cioè l'accordo con cui un fornitore cloud si impegna formalmente a trattare i dati personali nel rispetto del Regolamento Europeo GDPR. Questo accordo non deve essere scritto dall'Associazione: è predisposto dal fornitore, normalmente scaricabile dal sito web o accettabile con un click dall'area clienti. Non comporta costi aggiuntivi e non richiede consulenze tecniche. Fa parte della normale documentazione amministrativa di qualsiasi servizio cloud professionale.

Accanto al Data Processing Agreement (DPA), ciascun fornitore mette a disposizione: l'elenco dei propri subfornitori, la localizzazione geografica dei datacenter, le politiche di sicurezza e le certificazioni ottenute, e le procedure in caso di Data Breach.

### Attività previste prima della produzione

Le attività da completare prima di utilizzare ABRAZO con dati reali di partecipanti sono prevalentemente di natura documentale e amministrativa. Nessuna di esse richiede modifiche al software.

<div style="border:2px solid #ef3340;border-radius:10px;padding:24px 28px;margin:2.5em 0;background:#111;">
<div style="color:#ef3340;font-size:0.75em;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:16px;">Cosa dovrà fare concretamente l'Associazione</div>
<ul style="margin:0 0 18px 0;padding-left:1.4em;color:#f4efe7;line-height:2.2;">
<li>Acquisire la documentazione GDPR resa disponibile dai fornitori (Data Processing Agreement e documentazione allegata)</li>
<li>Conservarla insieme alla documentazione di ABRAZO</li>
<li>Aggiornare l'informativa privacy dell'evento, includendo i riferimenti ai fornitori cloud utilizzati</li>
<li>Aggiornare il Registro dei Trattamenti dell'Associazione</li>
<li>Formalizzare, ove previsto, la nomina dei fornitori cloud come Responsabili del trattamento</li>
</ul>
<div style="border-top:1px solid #2a2a2a;padding-top:14px;color:#d8d0c8;font-style:italic;">Queste attività sono prevalentemente amministrative e documentali, non richiedono modifiche al software e normalmente vengono completate in poche ore.</div>
</div>

### Riepilogo delle attività amministrative GDPR

| Attività | Chi la fornisce | Chi la conserva | Costo previsto | Quando |
|---|---|---|---|---|
| Data Processing Agreement Supabase | Supabase | Associazione | Nessun costo | Prima della produzione |
| Data Processing Agreement Vercel | Vercel | Associazione | Nessun costo | Prima della produzione |
| Data Processing Agreement Resend | Resend | Associazione | Nessun costo | Prima della produzione |
| Aggiornamento Informativa Privacy | Associazione | Associazione | Nessun costo (salvo diversa scelta dell'Associazione) | Prima della produzione |
| Aggiornamento Registro dei Trattamenti | Associazione | Associazione | Nessun costo | Prima della produzione |
| Definizione tempi di conservazione dati | Associazione | Associazione | Nessun costo | Prima della produzione |

---

## 10. Conclusioni

ABRAZO è oggi una piattaforma tecnicamente pronta. Il software è sviluppato, testato e funzionante. Le iscrizioni, il check-in, la gestione dei pagamenti, le email automatizzate e la dashboard operativa sono già operative. Le attività ancora previste riguardano principalmente il completamento della documentazione amministrativa e l'attivazione dei servizi cloud nella loro configurazione definitiva — passi ordinari nel percorso di messa in esercizio di qualsiasi sistema digitale.

Il costo annuo di esercizio — tra 315 e 650 euro a seconda della configurazione scelta — è contenuto rispetto al valore operativo che il sistema produce: iscrizioni automatizzate, check-in digitale, email di conferma, gestione pagamenti, reportistica, e storico completo di tutti gli eventi dell'Associazione.

I servizi scelti — Vercel, Supabase, Resend — sono standard di mercato utilizzati da migliaia di organizzazioni in tutto il mondo. Hanno team di supporto attivi, documentazione estesa, e una comunità di sviluppatori ampia. Non sono prodotti di nicchia o startup a rischio.

L'infrastruttura è stata progettata fin dall'inizio affinché possa evolvere negli anni senza creare dipendenza verso uno specifico fornitore. Tutti i dati dell'Associazione — iscritti, pagamenti, presenze, storico eventi — risiedono in un database PostgreSQL di proprietà dell'Associazione. Possono essere esportati in qualsiasi momento, in formato aperto, senza dipendere dal fornitore.

---

> **Consiglio**: il vero patrimonio dell'Associazione non risiede nei servizi cloud utilizzati, ma nei dati raccolti, nell'esperienza organizzativa consolidata e nella continuità operativa che ABRAZO garantisce nel tempo. I fornitori potranno cambiare; i dati, il dominio e le configurazioni resteranno sempre dell'Associazione.

---

## Appendice — Documentazione da acquisire prima della produzione

La seguente checklist riassume la documentazione da raccogliere e conservare prima di utilizzare ABRAZO con dati reali di partecipanti. Tutti i documenti elencati sono normalmente già predisposti dai fornitori e disponibili sul loro sito web o area clienti.

### Supabase

- □ Data Processing Agreement (DPA)
- □ Elenco Subprocessors (subfornitori)
- □ Localizzazione geografica dei datacenter
- □ Politica di backup e ripristino
- □ Sicurezza e cifratura dei dati
- □ Certificazioni disponibili (es. SOC 2, ISO 27001)
- □ Procedure di gestione Data Breach

### Vercel

- □ Data Processing Agreement (DPA)
- □ Elenco Subprocessors
- □ Localizzazione hosting e datacenter
- □ Sicurezza e protezione dell'applicazione
- □ Certificazioni disponibili
- □ Procedure di gestione Data Breach

### Resend

- □ Data Processing Agreement (DPA)
- □ Elenco Subprocessors
- □ Politica di conservazione delle email inviate
- □ Politica privacy
- □ Certificazioni disponibili
- □ Procedure di gestione Data Breach

### Dominio internet

- □ Intestazione all'Associazione (non al responsabile tecnico)
- □ Credenziali custodite dall'Associazione
- □ Rinnovo automatico attivato

---

## Continuità operativa

ABRAZO è stato progettato per evitare qualsiasi dipendenza tecnologica che potesse limitare la libertà dell'Associazione nel tempo.

I dati sono conservati in formato aperto (PostgreSQL) ed esportabili integralmente in qualsiasi momento. Il dominio internet e gli account dei servizi cloud sono intestati all'Associazione. I fornitori cloud sono sostituibili: il software utilizza tecnologie standard che funzionano su decine di piattaforme diverse. La documentazione tecnica è completa e aggiornata. Qualunque professionista qualificato può subentrare nella gestione senza perdita di dati né di operatività.

La proprietà intellettuale del software ABRAZO rimane al suo autore, secondo gli accordi che le parti definiranno. Questo non incide in alcun modo sulla disponibilità dei dati, sull'accesso all'infrastruttura, né sulla continuità delle operazioni dell'Associazione: il patrimonio informativo e operativo di Art&Tango è e rimane dell'Associazione.

---

## Domande frequenti

### Se un domani cambiamo sviluppatore, perdiamo tutto?

No. Tutti i dati dell'Associazione sono esportabili in qualsiasi momento in formato aperto: iscritti, pagamenti, presenze, storico completo di tutti gli eventi. Il dominio internet e gli account dei servizi cloud (Supabase, Vercel, Resend) sono intestati all'Associazione e rimangono nella sua piena disponibilità, indipendentemente da chi sviluppa o mantiene il software. Il database è in formato PostgreSQL e il software è scritto con tecnologie standard (Next.js, PostgreSQL) ampiamente diffuse: qualunque professionista qualificato può subentrare nella manutenzione e continuare il lavoro senza ricominciare da zero. La documentazione tecnica è completa e aggiornata. La proprietà intellettuale del software rimane al suo autore, ma ciò non limita in alcun modo la continuità operativa dell'Associazione.

### Se un fornitore cloud interrompe il servizio, cosa succede?

I dati dell'Associazione non andrebbero persi: sono conservati nel database PostgreSQL, che può essere esportato e spostato su un altro servizio. Vercel e Supabase sono entrambi sostituibili senza modificare il software. ABRAZO è stato scritto in modo da non dipendere da funzionalità proprietarie: usa tecnologie standard che funzionano su decine di fornitori diversi. In caso di necessità, la migrazione richiederebbe settimane di lavoro tecnico, non mesi — e i dati sarebbero al sicuro durante tutto il processo.

### Ci sono server da acquistare o da gestire?

No. L'Associazione non acquista, installa, aggiorna né gestisce alcun server fisico. Tutto avviene nel cloud: i fornitori si occupano di tutta l'infrastruttura tecnica, degli aggiornamenti di sicurezza, dei backup, e della disponibilità del servizio. L'Associazione paga un abbonamento mensile e utilizza il servizio, esattamente come avviene con qualsiasi altro strumento digitale in cloud.

### Quanto costa realmente mantenere ABRAZO?

Nella configurazione minima, il costo è di circa **315 euro all'anno** (circa 26 euro al mese), che copre principalmente il piano Pro di Supabase per i backup automatici e la continuità del database. Non ci sono costi variabili legati al numero di iscritti o al numero di eventi gestiti: il piano Pro è fisso e prevedibile. La registrazione del dominio aggiunge circa 15 euro annui. Tutti gli altri servizi (Vercel, Resend) rimangono gratuiti per i volumi tipici di Art&Tango.

---

*ABRAZO — OPS-001 · Documento istituzionale · Art&Tango · Versione 1.0 · Luglio 2026*
