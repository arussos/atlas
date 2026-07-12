# FOUNDATION-002 — Architettura della Conoscenza dell'Ecosistema Atlas

| Campo         | Valore                                                                 |
|---------------|------------------------------------------------------------------------|
| **ID**        | FOUNDATION-002                                                         |
| **Titolo**    | Architettura della Conoscenza dell'Ecosistema Atlas                    |
| **Stato**     | Approved                                                               |
| **Versione**  | 1.0                                                                    |
| **Data**      | 2026-07-12                                                             |
| **Autore**    | Andrea Russos                                                          |
| **Riferimento** | FOUNDATION-001                                                       |
| **Nota**      | Contributo architetturale sviluppato attraverso un processo di progettazione collaborativa uomo–AI |

---

## 1. Scopo

FOUNDATION-001 ha dichiarato che il valore dell'ecosistema Atlas risiede nella conoscenza organizzata, nelle inferenze costruite nel tempo, nelle connessioni tra concetti elaborati attraverso l'esperienza. Ha stabilito che l'inferenza è il vero valore del sistema, e che questo valore deve sopravvivere a qualsiasi migrazione tecnologica.

FOUNDATION-002 definisce la struttura concettuale permanente che rende operativa questa visione: il modello della conoscenza all'interno dell'ecosistema Atlas.

Questo documento non descrive come la conoscenza viene tecnicamente archiviata, indicizzata o recuperata. Descrive cosa è la conoscenza in Atlas, come è strutturata, come è classificata, come è connessa, come viene interrogata e come evolve nel tempo. La struttura qui definita è indipendente da qualsiasi tecnologia e deve rimanere valida anche se ogni componente tecnologico dell'ecosistema venisse sostituito.

FOUNDATION-002 non introduce nuovi principi fondativi: li eredita da FOUNDATION-001 e li applica all'architettura della conoscenza.

---

## 2. Posizione nella Gerarchia Documentale

Secondo la gerarchia documentale definita in FOUNDATION-001, questo documento appartiene al Livello 1 — Foundation Documents.

Il modello concettuale della conoscenza è un principio fondativo, non una scelta implementativa. Definisce il vocabolario architetturale permanente con cui l'intero ecosistema pensa e organizza il proprio patrimonio. Ogni sistema di archiviazione, ogni strumento di interrogazione, ogni pipeline di acquisizione deve conformarsi a questo modello, non il contrario.

---

## 3. Entità Fondamentali del Modello della Conoscenza

Il modello della conoscenza di Atlas è composto da sei entità fondamentali. Ogni entità ha una responsabilità precisa e confini chiari rispetto alle altre.

### 3.1 Knowledge Object

Il Knowledge Object è l'unità atomica della conoscenza all'interno dell'ecosistema Atlas.

Un Knowledge Object rappresenta un singolo elemento di conoscenza che può essere identificato in modo univoco, classificato, collegato ad altri elementi e interrogato. Può corrispondere a un documento completo, a una sezione di documento, a una conversazione, a una decisione, a un frammento di configurazione, a un evento registrato, o a qualsiasi altra forma in cui la conoscenza può essere formalizzata e conservata.

Il Knowledge Object ha tre proprietà invarianti:

- **Identificabilità**: può essere individuato e distinto da qualsiasi altro Knowledge Object nell'ecosistema.
- **Classificabilità**: può essere assegnato a categorie descritte dal modello (dominio, tipo, sorgente).
- **Connettibilità**: può essere collegato ad altri Knowledge Object attraverso relazioni esplicite.

Un Knowledge Object non è necessariamente un file o un record in un database. È un concetto: la rappresentazione formale di un elemento di conoscenza, indipendentemente dal formato fisico in cui è memorizzato.

### 3.2 Knowledge Source

La Knowledge Source definisce l'origine di un Knowledge Object: il sistema, lo strumento o il contesto da cui il Knowledge Object è stato generato o estratto.

La Knowledge Source non descrive il contenuto della conoscenza. Descrive la sua provenienza. Due Knowledge Object con contenuto identico ma origini diverse hanno Knowledge Source diverse, e questa differenza è architetturalmente rilevante: la provenienza influenza l'affidabilità, il contesto di produzione e le modalità di aggiornamento della conoscenza.

La Knowledge Source è un attributo classificatorio, non un valore tecnico. Il riferimento non è all'indirizzo di un endpoint o al nome di una tabella, ma alla categoria del sistema o del processo che ha prodotto la conoscenza.

### 3.3 Knowledge Domain

Il Knowledge Domain definisce l'area tematica o il contesto concettuale a cui un Knowledge Object appartiene.

Il Domain non descrive la forma della conoscenza, ma il suo contenuto dal punto di vista dell'ecosistema. Un Knowledge Object appartiene a un Domain primario e può essere associato a Domain secondari quando il contenuto attraversa più aree tematiche.

Il Domain è lo strumento primario di organizzazione tematica della conoscenza. Permette di isolare e interrogare corpora distinti senza perdere la visibilità sull'intero patrimonio.

### 3.4 Knowledge Type

Il Knowledge Type descrive la natura o la forma di un Knowledge Object: ciò che il Knowledge Object è, indipendentemente dal suo contenuto specifico.

A differenza del Domain — che risponde alla domanda "di cosa tratta?" — il Type risponde alla domanda "cos'è?". Un documento che definisce una decisione architetturale e un documento che registra una conversazione su quella decisione appartengono allo stesso Domain ma hanno Type diversi. Questa distinzione consente di filtrare la conoscenza in base alla sua natura, non solo al suo contenuto.

Il Knowledge Type determina anche le aspettative comportamentali su un Knowledge Object: un ADR è immutabile una volta approvato; una Conversazione può essere aggiornata con trascrizioni successive; un Incident evolve nel tempo attraverso fasi distinte.

### 3.5 Knowledge Relationship

La Knowledge Relationship definisce la connessione tra due Knowledge Object.

La conoscenza non è un insieme di documenti isolati: è una rete. Ogni elemento di conoscenza esiste in relazione ad altri elementi, e la comprensione di quelle relazioni è parte integrante del patrimonio dell'ecosistema.

Le relazioni tra Knowledge Object non sono implicite o derivabili automaticamente dal solo contenuto: devono essere dichiarate, classificate e mantenute. Una relazione non documentata è una connessione che l'ecosistema non può attraversare.

Le Knowledge Relationship hanno una direzione (da un Knowledge Object verso un altro) e un tipo (la natura della relazione). Direzione e tipo sono entrambi parte del modello: non tutte le relazioni sono simmetriche, e non tutte le relazioni hanno lo stesso significato.

### 3.6 Knowledge Collection

Una Knowledge Collection è un raggruppamento coerente di Knowledge Object accomunati da criteri espliciti.

La Collection non è semplicemente una categoria: è un'aggregazione deliberata che serve un fine specifico. Una Collection può essere definita per Domain, per Type, per Source, per progetto, per periodo temporale, o per qualsiasi combinazione di questi criteri. Può includere Knowledge Object appartenenti a Domain o Type diversi quando esiste una ragione concettuale che li accomuna.

Le Collection sono strumenti di organizzazione e di interrogazione: consentono di operare su sottoinsiemi coerenti del patrimonio senza perdere l'accesso all'intero corpus. Una Collection non isola la conoscenza: la rende accessibile con maggiore precisione.

---

## 4. Tassonomia della Conoscenza

La tassonomia qui definita costituisce la classificazione iniziale del modello. Le liste non sono esaustive né definitive: rappresentano le categorie identificate al momento della stesura di questo documento. Nuove categorie possono essere aggiunte attraverso il processo documentale appropriato. Le categorie esistenti non vengono rimosse: se una categoria diventa obsoleta, viene marcata come tale con un riferimento alla categoria che la sostituisce.

### 4.1 Knowledge Sources

Le Knowledge Source identificano i sistemi o i contesti da cui proviene la conoscenza acquisita dall'ecosistema Atlas.

| Source       | Descrizione                                                                |
|--------------|----------------------------------------------------------------------------|
| Claude       | Conversazioni con il modello Claude di Anthropic                           |
| ChatGPT      | Conversazioni con il modello GPT di OpenAI                                 |
| Git Repository | Codice sorgente, commit history, branch e tag di repository versionati   |
| BookStack    | Documentazione strutturata proveniente da BookStack                        |
| Snipe-IT     | Informazioni su asset e inventario IT provenienti da Snipe-IT              |
| Markdown     | Documenti in formato testo strutturato Markdown                            |
| PDF          | Documenti in formato PDF                                                   |
| Word         | Documenti in formato Word o compatibili                                    |
| Email        | Messaggi di posta elettronica                                              |
| NOEMA        | Knowledge Object generati o gestiti dal componente NOEMA                   |
| ABRAZO       | Knowledge Object generati o gestiti dal componente ABRAZO                  |
| LibreNMS     | Dati di monitoraggio e inventario di rete provenienti da LibreNMS          |
| Zabbix       | Dati di monitoraggio infrastrutturale provenienti da Zabbix                |

*Questa lista è estendibile. Ogni nuova Source deve essere documentata con descrizione e motivazione dell'aggiunta.*

### 4.2 Knowledge Domains

I Knowledge Domain definiscono le aree tematiche principali del corpus di conoscenza dell'ecosistema.

| Domain        | Descrizione                                                             |
|---------------|-------------------------------------------------------------------------|
| Foundation    | Principi fondativi, costituzione architetturale, manifesti              |
| Atlas         | Architettura, decisioni e documentazione relativi alla piattaforma Atlas |
| NOEMA         | Tutto ciò che riguarda il componente NOEMA                              |
| ABRAZO        | Tutto ciò che riguarda il componente ABRAZO                             |
| Networking    | Reti, protocolli, topologie, configurazioni di rete                     |
| Hardware      | Componenti fisici, inventario, asset IT                                 |
| Ricerca       | Analisi, esperimenti, indagini esplorative                              |
| Clienti       | Informazioni relative a clienti o progetti per clienti                  |
| Documentazione | Documentazione tecnica e operativa non classificabile altrimenti       |

*Questa lista è estendibile. I Domain riflettono l'organizzazione tematica del corpus nel tempo e possono essere ampliati al crescere dell'ecosistema.*

### 4.3 Knowledge Types

I Knowledge Type descrivono la natura di ogni Knowledge Object.

| Type          | Descrizione                                                                    |
|---------------|--------------------------------------------------------------------------------|
| Foundation    | Documento fondativo dell'ecosistema                                            |
| ADR           | Architectural Decision Record: decisione architetturale documentata e immutabile |
| Decision      | Decisione significativa non necessariamente di natura architetturale           |
| Manual        | Documentazione procedurale o operativa                                         |
| Conversation  | Trascrizione o sintesi di una conversazione con un agente AI o tra persone     |
| Meeting       | Note o verbale di una riunione                                                 |
| Incident      | Registrazione di un incidente, con timeline e analisi                          |
| Configuration | Configurazione di un sistema o di un componente                                |
| Code          | Codice sorgente o frammento di codice rilevante                                |
| Repository    | Riferimento a un repository di codice nella sua interezza                      |
| Experiment    | Analisi esplorativa, ipotesi, test non ancora consolidati                      |
| Reference     | Riferimento a una risorsa esterna o a uno standard                             |

*Questa lista è estendibile. Ogni nuovo Type deve specificare la propria natura e le aspettative comportamentali che comporta.*

---

## 5. Metadato Minimo

Ogni Knowledge Object deve poter essere descritto attraverso un insieme minimo di metadati. Questi metadati non definiscono il contenuto del Knowledge Object, ma ne definiscono l'identità, il contesto e la posizione all'interno del modello della conoscenza.

I metadati qui elencati sono il minimo necessario affinché un Knowledge Object possa essere classificato, connesso e interrogato in modo coerente. Ogni implementazione può estendere questo insieme; non può ridurlo.

Il formato tecnico di questi metadati non è oggetto di questo documento. Questo documento definisce esclusivamente il significato concettuale di ciascun campo.

| Campo          | Significato concettuale                                                                                                                                                                |
|----------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **id**         | Identificatore univoco e permanente del Knowledge Object nell'ecosistema. Non cambia nel tempo, anche se il contenuto o i metadati vengono aggiornati.                                 |
| **title**      | Nome leggibile del Knowledge Object. Descrive il contenuto in forma sintetica, comprensibile senza necessità di aprire il documento.                                                   |
| **source**     | La Knowledge Source da cui il Knowledge Object è stato generato o estratto. Corrisponde a una delle categorie definite nella tassonomia delle Knowledge Source.                        |
| **project**    | Il progetto o il contesto operativo a cui il Knowledge Object è associato. Permette di aggregare Knowledge Object che condividono un contesto di produzione, indipendentemente dal Domain. |
| **domain**     | Il Knowledge Domain primario a cui il Knowledge Object appartiene. Corrisponde a una delle categorie definite nella tassonomia dei Knowledge Domain.                                    |
| **type**       | Il Knowledge Type del Knowledge Object. Corrisponde a una delle categorie definite nella tassonomia dei Knowledge Type.                                                                |
| **created**    | La data in cui il Knowledge Object è stato creato o acquisito nell'ecosistema. Non è necessariamente la data di creazione del contenuto originale, ma la data di ingresso nel modello. |
| **version**    | La versione corrente del Knowledge Object. Un Knowledge Object mai modificato è alla versione 1. Ogni aggiornamento significativo incrementa la versione.                              |
| **author**     | Il soggetto responsabile della produzione o dell'acquisizione del Knowledge Object. Può essere una persona, un sistema automatico o un agente AI.                                      |
| **language**   | La lingua in cui il Knowledge Object è scritto o codificato.                                                                                                                           |
| **tags**       | Un insieme di etichette libere che arricchiscono la classificazione al di là dei campi strutturati. I tag non sostituiscono Domain e Type: li completano per esigenze specifiche.      |
| **importance** | Una valutazione dell'importanza del Knowledge Object all'interno del corpus. Guida le operazioni di recupero e di interrogazione, indicando quale conoscenza privilegiare in caso di ambiguità o di necessità di sintesi. |

---

## 6. Knowledge Relationships

La conoscenza non è un insieme di documenti isolati. È una rete di elementi connessi, e la comprensione delle connessioni è parte integrante del patrimonio. Un Knowledge Object senza relazioni è una voce isolata; un Knowledge Object con relazioni esplicite è un nodo in una rete navigabile.

### 6.1 Natura delle Relazioni

Ogni Knowledge Relationship connette due Knowledge Object e descrive la natura della connessione. Una relazione ha:

- **Origine**: il Knowledge Object da cui la relazione parte.
- **Destinazione**: il Knowledge Object verso cui la relazione è diretta.
- **Tipo**: la natura della connessione tra i due Knowledge Object.

Le relazioni sono direzionali: la relazione da A verso B non è equivalente alla relazione da B verso A. La navigazione del grafo di conoscenza può percorrere le relazioni in entrambe le direzioni, ma la direzione fa parte del significato della relazione.

### 6.2 Tipi di Relazione

Il modello non definisce in modo esaustivo tutti i possibili tipi di relazione: l'insieme è estendibile. I seguenti tipi rappresentano la classificazione iniziale.

| Tipo              | Significato                                                                                             |
|-------------------|---------------------------------------------------------------------------------------------------------|
| **derives-from**  | Il Knowledge Object di origine è stato derivato o generato dal Knowledge Object di destinazione.        |
| **implements**    | Il Knowledge Object di origine implementa o concretizza il Knowledge Object di destinazione.            |
| **supersedes**    | Il Knowledge Object di origine sostituisce il Knowledge Object di destinazione, che rimane nel corpus marcato come superato. |
| **references**    | Il Knowledge Object di origine cita o fa riferimento al Knowledge Object di destinazione senza dipendenza strutturale. |
| **caused**        | Il Knowledge Object di origine ha determinato la creazione del Knowledge Object di destinazione.        |
| **documents**     | Il Knowledge Object di origine documenta un aspetto del Knowledge Object di destinazione.               |
| **extends**       | Il Knowledge Object di origine estende o approfondisce il Knowledge Object di destinazione.             |

### 6.3 Catene di Conoscenza

Le Knowledge Relationship consentono di costruire catene di conoscenza: percorsi che attraversano il grafo da un elemento all'altro, ricostruendo la storia e la logica di una decisione o di un processo.

Un esempio di catena tipica nell'ecosistema Atlas:

```
Foundation Document
      ↓ [implements]
Architecture Decision Record
      ↓ [caused]
Decision
      ↓ [documents]
Commit
      ↓ [caused]
Manual
      ↓ [references]
Conversation
```

Questa catena permette di rispondere a domande del tipo: "da quale principio fondativo deriva questa procedura operativa?" oppure "quale decisione ha generato questo documento?". L'ecosistema Atlas deve essere in grado di ricostruire questi percorsi in modo affidabile. La capacità di attraversare il grafo della conoscenza in profondità è la condizione che rende possibile l'inferenza strutturata.

### 6.4 Integrità del Grafo

Un Knowledge Object non viene eliminato dal corpus. Viene marcato come archiviato, obsoleto o superato, secondo il caso. Le relazioni che lo coinvolgono rimangono valide e navigabili.

Ogni Knowledge Relationship deve riferirsi a Knowledge Object presenti nel corpus. Una relazione verso un elemento non presente non è una relazione: è un riferimento rotto. Il mantenimento dell'integrità del grafo è una responsabilità architetturale: la politica che lo governa è definita qui, indipendentemente dai meccanismi tecnici con cui verrà verificata.

---

## 7. Classificazione della Conoscenza

La classificazione di un Knowledge Object è un'operazione multidimensionale: un singolo Knowledge Object è descritto simultaneamente dal suo Domain, dal suo Type, dalla sua Source e dai suoi tag. Queste dimensioni non sono alternative, ma complementari. Ogni dimensione abilita un diverso modo di accedere al Knowledge Object e di aggregarlo con altri.

La classificazione serve tre scopi distinti:

**Recupero diretto**: trovare un Knowledge Object specifico quando se ne conosce la classificazione approssimativa.

**Aggregazione tematica**: raggruppare Knowledge Object che condividono un Domain o un Type, indipendentemente dalla loro Source o dai loro tag.

**Filtro contestuale**: isolare i Knowledge Object rilevanti per un contesto specifico, escludendo quelli non pertinenti senza perderli dal corpus.

La classificazione non è un'operazione una tantum. Evolve con il corpus: quando il modello introduce nuove categorie di Domain o Type, i Knowledge Object esistenti possono essere riclassificati senza perdita di contenuto o di relazioni.

---

## 8. Interrogazione della Conoscenza

L'interrogazione è il processo attraverso cui il corpus viene consultato per rispondere a una domanda o per produrre un output. Il modello concettuale dell'interrogazione è indipendente dalla tecnologia impiegata per realizzarla.

### 8.1 Modalità di Interrogazione

Il corpus di conoscenza supporta quattro modalità di interrogazione fondamentali, che corrispondono a quattro esigenze diverse.

**Interrogazione per identità**: recuperare un Knowledge Object specifico attraverso il suo identificatore o i suoi metadati. Il risultato è un singolo Knowledge Object o un insieme ristretto di Knowledge Object noti.

**Interrogazione per classificazione**: recuperare tutti i Knowledge Object che corrispondono a una combinazione di criteri di classificazione (Domain, Type, Source, tag, importance). Il risultato è un sottoinsieme del corpus definito dalla classificazione.

**Interrogazione per similitudine semantica**: recuperare Knowledge Object il cui contenuto è semanticamente vicino a una domanda o a un testo di riferimento. Questa modalità non dipende dalla classificazione esplicita ma dalla rappresentazione del contenuto dei Knowledge Object.

**Interrogazione per grafo**: attraversare le Knowledge Relationship a partire da un Knowledge Object noto, navigando le relazioni per raggiungere Knowledge Object connessi. Questa modalità permette di rispondere a domande che richiedono di comprendere il contesto e la storia di un elemento di conoscenza, non solo il suo contenuto immediato.

### 8.2 Composizione delle Interrogazioni

Le quattro modalità possono essere composte: un'interrogazione complessa può combinare filtri per classificazione, similitudine semantica e navigazione del grafo. La composizione delle modalità è la condizione che rende possibile l'interrogazione sofisticata del corpus.

### 8.3 Il Risultato come Knowledge Object

Il risultato di un'interrogazione — se sintetizzato e conservato — è esso stesso un Knowledge Object. Le risposte elaborate, le sintesi prodotte, le inferenze estratte dal corpus sono elementi di conoscenza di tipo Conversation o Experiment, classificabili, connettibili e includibili nel corpus. L'interrogazione del corpus produce conoscenza nuova che arricchisce il corpus stesso.

---

## 9. Evoluzione della Conoscenza

La conoscenza non è statica. Il corpus di Atlas cresce, si aggiorna e si corregge nel tempo. Il modello concettuale governa come questa evoluzione avviene in modo controllato.

### 9.1 Immutabilità dell'Identità

L'identificatore di un Knowledge Object non cambia mai. L'id è permanente: è il punto di riferimento stabile attorno a cui ruotano tutte le relazioni e tutte le versioni del Knowledge Object. Contenuto, metadati e relazioni possono evolvere; l'identità non cambia.

### 9.2 Versionamento

Ogni Knowledge Object mantiene una storia delle proprie versioni. Una nuova versione non sostituisce la precedente: la affianca, marcando la precedente come superata. L'accesso alla versione corrente è il comportamento predefinito, ma la storia delle versioni deve essere accessibile e navigabile.

La versione di un Knowledge Object è una proprietà semantica, non tecnica: è parte del metadato minimo, indipendentemente dal meccanismo con cui viene implementata.

### 9.3 Deprecazione e Archiviazione

Un Knowledge Object che non è più valido non viene eliminato. Viene marcato come deprecato o archiviato. Le relazioni che lo coinvolgono rimangono navigabili. Questo garantisce che la storia della conoscenza rimanga accessibile anche quando il corpus evolve.

### 9.4 Conflitti tra Versioni di Conoscenza

Quando due Knowledge Object contengono informazioni contraddittorie, il conflitto deve essere risolto esplicitamente attraverso una Knowledge Relationship di tipo **supersedes**, accompagnata da un nuovo Knowledge Object che documenta la risoluzione. Un conflitto non risolto è un'anomalia del corpus, non uno stato accettabile.

### 9.5 Crescita Coerente

Il corpus cresce in modo coerente quando ogni Knowledge Object aggiunto è classificato correttamente, connesso agli elementi esistenti attraverso relazioni esplicite, e provvisto del metadato minimo. La crescita incoerente — Knowledge Object non classificati, non connessi o privi di metadati — degrada la qualità del corpus e compromette la capacità di interrogazione e inferenza.

---

## 10. Technology Independence

Questo documento definisce il modello concettuale della conoscenza. Non definisce la tecnologia con cui questo modello viene implementato.

Le tecnologie impiegate nell'ecosistema Atlas per acquisire, archiviare, indicizzare e interrogare la conoscenza — qualunque esse siano al momento della lettura di questo documento — sono implementazioni di questo modello, non il modello stesso. La distinzione è fondamentale.

Open WebUI, Ollama, Qdrant, Docker, o qualsiasi altra tecnologia presente o futura rappresentano esclusivamente strumenti di implementazione. Possono essere sostituiti, aggiornati, rimossi o affiancati da alternative senza che il modello concettuale qui descritto debba cambiare. La struttura della conoscenza — le entità fondamentali, la tassonomia, i metadati, le relazioni — rimane invariata indipendentemente dal sottostrato tecnologico.

Questo principio ha tre conseguenze operative.

**Prima conseguenza**: qualsiasi migrazione tecnologica deve preservare integralmente il modello concettuale. Se una migrazione richiede di alterare le entità, la tassonomia o i metadati definiti in questo documento, il problema non è nel modello: è nella tecnologia di destinazione, che non è adatta a implementarlo.

**Seconda conseguenza**: la valutazione di una tecnologia deve includere la capacità di mappare fedelmente il modello concettuale. Una tecnologia che non è in grado di supportare le entità fondamentali, i metadati minimi o le Knowledge Relationship non è una tecnologia adatta all'ecosistema Atlas, indipendentemente dalle sue prestazioni o dalla sua popolarità nel momento della valutazione.

**Terza conseguenza**: la documentazione del corpus di conoscenza deve essere comprensibile indipendentemente dalla tecnologia con cui è stata prodotta. Un Knowledge Object descritto secondo questo modello deve poter essere compreso da qualsiasi futuro sistema che implementi il modello, senza richiedere conoscenza degli strumenti con cui è stato originariamente archiviato.

La conoscenza costituisce il patrimonio permanente dell'ecosistema Atlas. Le tecnologie utilizzate per acquisirla, organizzarla e interrogarla sono componenti sostituibili. Il valore risiede nella struttura della conoscenza, non negli strumenti impiegati per gestirla.

---

## 11. Relazione con FOUNDATION-001

FOUNDATION-002 è un documento Foundation di Livello 1, derivato da FOUNDATION-001. Eredita integralmente i principi fondativi ivi definiti e ne costituisce l'applicazione specifica all'architettura della conoscenza.

In particolare, FOUNDATION-002 applica operativamente:

- Il **principio 4.1** (il patrimonio professionale vale più della tecnologia): il modello della conoscenza definisce la struttura del patrimonio in modo indipendente dalla tecnologia che lo ospita.
- Il **principio 4.4** (nessun lock-in tecnologico): la separazione tra modello concettuale e implementazione tecnologica è il meccanismo che rende operativo questo principio nel contesto della conoscenza.
- Il **principio 4.7** (l'inferenza rappresenta il vero valore del sistema): le Knowledge Relationship e le modalità di interrogazione per grafo e per similitudine semantica sono i meccanismi che rendono possibile l'inferenza strutturata.
- Il **principio 4.8** (ogni componente deve essere sostituibile senza compromettere il patrimonio): il modello concettuale è il contratto che garantisce questa sostituibilità a livello di conoscenza.

FOUNDATION-002 non ripete né modifica i principi di FOUNDATION-001. Li applica.

---

## 12. Conclusioni

FOUNDATION-002 definisce il modello concettuale permanente della conoscenza nell'ecosistema Atlas. Il modello è composto da sei entità fondamentali — Knowledge Object, Knowledge Source, Knowledge Domain, Knowledge Type, Knowledge Relationship, Knowledge Collection — da una tassonomia estendibile, da un insieme minimo di metadati, e da principi che governano la classificazione, l'interrogazione e l'evoluzione del corpus.

Il modello è progettato per resistere al tempo: può essere implementato su tecnologie diverse in momenti diversi senza perdere coerenza. Può essere esteso con nuove categorie tassonomiche senza dover essere ridisegnato. Può crescere in modo indefinito senza perdere la capacità di essere interrogato in modo significativo.

La qualità del corpus di conoscenza dell'ecosistema Atlas è determinata dal rigore con cui questo modello viene applicato: nella classificazione di ogni Knowledge Object, nella dichiarazione di ogni Knowledge Relationship, nella conservazione di ogni versione della conoscenza. Un corpus classificato con precisione e connesso con coerenza è un corpus interrogabile con profondità. Un corpus trascurato è un archivio opaco.

Il modello qui definito è la condizione necessaria — non sufficiente — perché l'ecosistema Atlas possa esercitare la propria capacità di inferenza. La condizione sufficiente è l'applicazione disciplinata di questo modello nel tempo.

---

*FOUNDATION-002 — Versione 1.0 — 2026-07-12 — Approved*
*Andrea Russos — Contributo architetturale sviluppato attraverso un processo di progettazione collaborativa uomo–AI*
