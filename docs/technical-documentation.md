# sistem-za-obvescanje

## 1. Pregled sistema

**sistem-za-obvescanje** je oblačno-naravnana aplikacija za centraliziran pregled aktualnih in relevantnih dogodkov ter za obveščanje uporabnikov prek elektronske pošte. Namenjena je splošni javnosti za pregled vremenskih opozoril sistema ARSO ter organizacijam in podjetjem, ki potrebujejo sistem za obveščanje svojih zaposlenih o internih ali zunanjih dogodkih.

## 2. Arhitektura sistema

## 2.1 Pregled mikrostoritev
Backend sistema je zasnovan kot mikrostoritvena arhitektura, kjer je vsaka storitev odgovorna za jasno omejen del funkcionalnosti sistema za obveščanje. Mikrostoritve so med seboj ohlapno povezane in komunicirajo prek sinhronih in asinhronih mehanizmov.

| Mikrostoritev | Namen |
|--------------|-------|
| **users** | Upravljanje uporabnikov, avtentikacije in uporabniških preferenc. |
| **arso-sync** | Periodičen zajem in obdelava vremenskih opozoril iz sistema ARSO. |
| **arso-service** | API za dostop do shranjenih vremenskih opozoril. |
| **companies-sync** | Upravljanje dogodkov organizacij in dežurnih oseb. |
| **companies-filter** | Filtriranje dogodkov in odločanje o pošiljanju obvestil. |
| **notification-function** | Pošiljanje e-poštnih obvestil uporabnikom (serverless, Google Cloud Functions). |

---

## 2.2 Podrobni opis mikrostoritev

### **users**
- **Odgovornost:** Registracija uporabnikov, avtentikacija, avtorizacija ter shranjevanje uporabniških nastavitev.
- **Podatki:** Uporabniški računi, vloge, pripadnost organizacijam ter preference glede pregledovanja in prejemanja obvestil.
- **API:** GraphQL API.
- **Podatkovna baza:** MongoDB.
- **Komunikacija:** Sinhrona (GraphQL). Storitev uporabljata frontend in `companies-filter`.

---

### **arso-sync**
- **Odgovornost:** Periodična sinhronizacija vremenskih opozoril iz sistema ARSO.
- **Podatki:** Vremenska opozorila v CAP/XML formatu, pretvorjena v interno podatkovno obliko.
- **API:** Brez javnega HTTP vmesnika.
- **Podatkovna baza:** PostgreSQL.
- **Komunikacija:** Asinhrona – objavljanje dogodkov v RabbitMQ ob novih ali posodobljenih opozorilih.

---

### **arso-service**
- **Odgovornost:** Ponuja REST API za dostop do trenutno veljavnih vremenskih opozoril.
- **Podatki:** Aktivna vremenska opozorila po regijah.
- **API:** REST HTTP (npr. `GET /events/active`).
- **Podatkovna baza:** PostgreSQL (samo branje).
- **Komunikacija:** Sinhrona (REST). Storitev uporablja companies-filter`.

---

### **companies-sync**
- **Odgovornost:** Upravljanje dogodkov organizacij, ki želijo obveščati svoje uporabnike oz. zaposlene (npr. zapore cest, požari, nevarne razmere).
- **Podatki:** Dogodki organizacij in razporedi dežurnih oseb.
- **API:** REST HTTP API.
- **Podatkovna baza:** PostgreSQL.
- **Komunikacija:** Sinhrona (REST) ter asinhrona – objavljanje dogodkov v RabbitMQ.

---

### **companies-filter**
- **Odgovornost:** Filtriranje dogodkov in odločanje, katerim uporabnikom je treba poslati obvestila.
- **Podatki:** Dogodki, uporabniške preference, podatki o dežurnih osebah.
- **API:** REST HTTP API za frontend.
- **Podatkovna baza:** Nima lastne baze.
- **Komunikacija:**  
  - Asinhrona: consumer v RabbitMQ (dogodki iz `arso-sync` in `companies-sync`)
  - Sinhrona: poizvedbe na `users`, `arso-service` in `companies-sync`

---

### **notification-function**
- **Odgovornost:** Pošiljanje e-poštnih obvestil končnim uporabnikom na podlagi dogodkov, ki jih posreduje storitev `companies-filter`.
- **Izvajalno okolje:** Google Cloud Functions (serverless).
- **API:** HTTP-trigger funkcija, namenjena internemu klicu iz backend sistema.
- **Zunanja integracija:** Brevo (SMTP / transactional email API).
- **Konfiguracija in skrivnosti:**  
  - `BREVO_API_KEY`  
  - `SENDER_EMAIL`
  - `NOTIFICATION_FUNCTION_TOKEN`
  
  Vrednosti so shranjene v Google Cloud Secrets in niso del izvorne kode.
- **Podatkovna baza:** Ne uporablja lastne baze.
- **Komunikacija:** Asinhrona – sprožena iz `companies-filter` ob zaznavi relevantnega dogodka.

---

## 2.3 Komunikacija med storitvami

### Sinhrona komunikacija (REST / GraphQL)
- Frontend → **users** (GraphQL)
- Frontend → **companies-filter** (REST)
- **companies-filter** → **users** (GraphQL)
- **companies-filter** → **arso-service**, **companies-sync** (REST)
- **companies-filter** → **notification-function** (HTTP trigger)

---

### Asinhrona komunikacija (event-driven)
- **Sporočilni sistem:** RabbitMQ
- **Producenti:** `arso-sync`, `companies-sync`
- **Odjemalec:** `companies-filter`
- **Vzorec:** dogodkovno vodena arhitektura (event-driven)

---

## 2.4 Vloga podatkovnih baz in zunanjih storitev

| Tehnologija | Uporaba |
|------------|--------|
| **PostgreSQL** | Vremenska opozorila, dogodki organizacij, dežurstva |
| **MongoDB** | Uporabniški računi in nastavitve |
| **RabbitMQ** | Asinhrona komunikacija med mikrostoritvami |
| **Google Cloud Secrets** | Varna hramba API ključev in konfiguracije |
| **Brevo API** | Pošiljanje e-poštnih obvestil |

## 3. Uporabljene tehnologije

Sistem je zasnovan v skladu z načeli cloud-native arhitekture. Spodaj so navedene ključne uporabljene tehnologije.

- **Backend:** Python, FastAPI, Strawberry GraphQL, Uvicorn  
- **Podatkovna hramba:** PostgreSQL, MongoDB  
- **Sporočilni sistem:** RabbitMQ (dogodkovno vodena komunikacija)  
- **Kontejnerizacija:** Docker, Docker Buildx  
- **Orkestracija:** Kubernetes, kind (lokalno okolje)  
- **Upravljanje konfiguracije:** Okoljske spremenljivke, Kubernetes ConfigMaps in Secrets  
- **Frontend:** Next.js (React), Tailwind CSS  
- **CI/CD:** GitHub Actions, Docker Hub  
- **Zunanje integracije:** Javni CAP/XML vir ARSO, Brevo API  
- **Oblačna platforma:** Google Cloud (GKE, Cloud Functions)

## 4. Struktura repozitorija

Repozitorij projekta *sistem-za-obvescanje* je organiziran po mikrostoritvenem principu, kjer ima vsaka storitev lastno izvorno kodo, odvisnosti in Kubernetes konfiguracijo.

### 4.1 Korenska struktura

- `.github/workflows/`  
  Vsebuje definicije CI/CD procesov, implementiranih z GitHub Actions.
- `services/`  
  Osrednji imenik, ki vsebuje vse mikrostoritve sistema.
- `README.md`  
  Osnovna tehnična dokumentacija projekta.

### 4.2 Struktura mikrostoritve

Vsaka mikrostoritev znotraj imenika `services/` sledi enotni strukturi. Primer je storitev `companies-filter`:

- `src/`  
  Izvorna koda mikrostoritve (aplikacijska logika).
- `k8s/`  
  Kubernetes manifesti, specifični za posamezno storitev:
  - `deployment.yaml`
  - `service.yaml`
  - `ingress.yaml`
  - `*-configmap.yaml` in `*-secret.yaml`
- `Dockerfile`  
  Definicija Docker vsebnika za mikrostoritev.
- `requirements.txt`  
  Seznam Python odvisnosti storitve.

## 5. Konfiguracija aplikacije in upravljanje konfiguracije

Sistem uporablja zunanje upravljanje konfiguracije, kar omogoča spreminjanje nastavitev brez sprememb izvorne kode ali ponovnega prevajanja aplikacij.

### 5.1 Okoljske spremenljivke

Vse mikrostoritve uporabljajo okoljske spremenljivke za konfiguracijo naslednjih kategorij:

1. povezave do podatkovnih baz,
2. nastavitve sporočilnega sistema,
3. naslove in končne točke drugih storitev,
4. avtentikacijske in avtorizacijske parametre,
5. poverilnice za zunanje storitve.

### 5.2 ConfigMaps in Secrets

Nesenzitivna konfiguracija, kot so imena storitev ali parametri delovanja, je shranjena v Kubernetes ConfigMap-ih.  
Občutljivi podatki, kot so gesla, API ključi in varnostni žetoni, so shranjeni v Kubernetes Secrets ali v oblačnem okolju v Google Cloud Secrets Managerju.

## 6. Kubernetes arhitektura

Sistem je nameščen v Kubernetes okolju, kjer je vsaka mikrostoritev definirana kot samostojna enota z lastnimi manifesti za izvajanje in konfiguracijo. Manifesti posameznih mikrostoritev so organizirani v imenikih `services/<storitev>/k8s/`, skupni infrastrukturni vir sistema (RabbitMQ) pa je definiran ločeno v imeniku `services/infrastructure/`.

### 6.1 Kubernetes manifesti

Sistem uporablja standardne Kubernetes objekte:
- **Deployment** in **CronJob** za izvajanje aplikacijskih storitev in periodičnih opravil,
- **Service (ClusterIP)** za interno omrežno povezovanje,
- **IngressRoute (Traefik)** za izpostavitev storitev v lokalnem okolju,
- **ConfigMap** in **Secret** za upravljanje konfiguracije.

Konfiguracija je v celoti ločena od implementacije in se v aplikacije posreduje prek okoljskih spremenljivk, definiranih v ConfigMap-ih in Secret-ih. Podatkovne baze in sporočilni sistem RabbitMQ so nameščeni kot ločeni Kubernetes Deployment-i s trajno hrambo podatkov.

### 6.2 Health checks

Za aplikacijske mikrostoritve so definirani **readiness** in **liveness** mehanizmi za nadzor nad stanjem podov in pravilno usmerjanje prometa. Aplikacije uporabljajo HTTP mehanizme zaznavanja stanja, podatkovne baze pa ukazne mehanizme za preverjanje razpoložljivosti. Periodična opravila (CronJob) health mehanizmov ne uporabljajo.

## 7. Lokalno razvojno okolje
> **TODO:** Dodati navodila za zagon sistema v lokalnem Kubernetes okolju (kind).

### 7.1 Zahteve
(Docker, kubectl, kind)

### 7.2 Zagon sistema v lokalnem okolju
(Postopek zagona z uporabo kind)

## 8. Namestitev v oblak (Google Cloud)
> **TODO:** Dodati navodila za namestitev v oblačno okolje.

### 8.1 Ciljno okolje
(Google Kubernetes Engine – GKE)

### 8.2 Razlike med lokalnim in cloud okoljem
(Kaj se spremeni in kaj ostane enako)

## 9. Zunanje integracije

Sistem vključuje integracije z zunanjimi viri podatkov in tretjeosebnimi storitvami, ki omogočajo pridobivanje vremenskih opozoril ter pošiljanje elektronskih obvestil uporabnikom.

### 9.1 ARSO

Vremenska opozorila se pridobivajo iz javno dostopnega CAP/XML vira Agencije RS za okolje (ARSO), ki je dostopen prek statičnih HTTP končnih točk. Integracijo izvaja mikrostoritev `arso-sync`, implementirana kot periodično opravilo (CronJob), ki podatke obdela in shrani v PostgreSQL ter ob spremembah sproži dogodke v RabbitMQ. Dostop do vira ne zahteva avtentikacije.

### 9.2 Brevo

Pošiljanje elektronskih obvestil je izvedeno prek serverless funkcije v oblačnem okolju, ki uporablja storitev Brevo kot zunanjo SaaS platformo za transakcijsko e-pošto. Komunikacija poteka prek HTTPS REST vmesnika z uporabo JSON sporočil, avtentikacija pa z API ključem, pri čemer so API ključ in naslov pošiljatelja shranjeni v Kubernetes Secrets. Funkcija se sproži asinhrono ob zaznavi relevantnih dogodkov.