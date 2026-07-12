# Manuali operativi ABRAZO

Documentazione operativa interna per lo staff di Art&Tango.

Ogni manuale ha un codice stabile `MAN-NNN` che non cambia nel tempo.

---

## Elenco manuali

| Codice | File | Destinatari | Stato |
|---|---|---|---|
| MAN-001 | [MAN-001-start-here.md](MAN-001-start-here.md) | Tutto lo staff | ✅ Esistente |
| MAN-002 | [MAN-002-manuale-segreteria.md](MAN-002-manuale-segreteria.md) | Personale di segreteria | ✅ Esistente |
| MAN-003 | [MAN-003-manuale-checkin.md](MAN-003-manuale-checkin.md) | Staff front desk e staff di sala | ✅ Esistente |
| MAN-004 | [MAN-004-pratica-partecipante.md](MAN-004-pratica-partecipante.md) | Tutto lo staff | ✅ Esistente |
| MAN-005 | [MAN-005-manuale-esportazioni-report.md](MAN-005-manuale-esportazioni-report.md) | Segreteria, direzione | ⬜ Placeholder — Da completare in DOC 1.x |
| MAN-006 | [MAN-006-manuale-configurazione-evento.md](MAN-006-manuale-configurazione-evento.md) | Amministratore tecnico | ⬜ Placeholder — Da completare in DOC 1.x |
| MAN-007 | [MAN-007-manuale-gdpr-operativo.md](MAN-007-manuale-gdpr-operativo.md) | Responsabile privacy, direzione | ⬜ Placeholder — Da completare in DOC 1.x |
| MAN-008 | [MAN-008-risoluzione-problemi.md](MAN-008-risoluzione-problemi.md) | Tutto lo staff | ⬜ Placeholder — Da completare in DOC 1.x |

---

## Descrizione sintetica

| Codice | Scopo in una riga |
|---|---|
| MAN-001 | Panoramica di ABRAZO: chi usa cosa e quando, orientamento rapido per chi inizia |
| MAN-002 | Gestione pagamenti, inbox operativa segreteria, conferme bonifici |
| MAN-003 | Accoglienza all'ingresso evento (QR scanner) e accesso alle singole attività |
| MAN-004 | Pratica partecipante: come leggere la scheda iscritto, stati, audit trail, modifica iscrizione |
| MAN-005 | Export Excel iscrizioni e attività, lettura fogli report |
| MAN-006 | Configurazione nuovo evento: pacchetti, attività, maestri, apertura iscrizioni |
| MAN-007 | Consensi GDPR, diritti degli interessati, audit trail, conservazione dati |
| MAN-008 | Problemi comuni durante check-in, segreteria, iscrizioni, export |

---

## Generazione PDF

I PDF vengono generati automaticamente a partire dai file Markdown con il comando:

```bash
npm run docs:pdf
```

I PDF vengono salvati in `docs/generated/pdf/` con lo stesso nome del file Markdown.

**Prima esecuzione** — il tool scarica Chromium (~200 MB, una tantum):

```bash
npm install          # installa le dipendenze incluso md-to-pdf
npm run docs:pdf     # genera i PDF
```

I PDF in `docs/generated/pdf/` non sono versionati in git (aggiunti a `.gitignore`).

---

*ABRAZO · Art&Tango · DOC 1.0 · Luglio 2026*
