# sistem-za-obvescanje

## 1. Pregled sistema

**sistem-za-obvescanje** je oblačno-naravnana aplikacija za centraliziran pregled aktualnih in relevantnih dogodkov ter za obveščanje uporabnikov prek elektronske pošte. Namenjena je splošni javnosti za pregled vremenskih opozoril sistema ARSO ter organizacijam in podjetjem, ki potrebujejo sistem za obveščanje svojih zaposlenih o internih ali zunanjih dogodkih.

## 2. Arhitektura sistema

### 2.1 Pregled mikrostoritev
Backend sistema je zasnovan kot mikrostoritvena arhitektura, kjer je vsaka storitev odgovorna za jasno omejen del funkcionalnosti sistema za obveščanje. Mikrostoritve so med seboj ohlapno povezane in komunicirajo prek sinhronih in asinhronih mehanizmov.

| Mikrostoritev | Namen |
|--------------|-------|
| **users** | Upravljanje uporabnikov, avtentikacije in uporabniških preferenc. |
| **arso-sync** | Periodičen zajem in obdelava vremenskih opozoril iz sistema ARSO. |
| **arso-service** | API za dostop do shranjenih vremenskih opozoril. |
| **companies-sync** | Upravljanje dogodkov organizacij in dežurnih oseb. |
| **companies-filter** | Filtriranje dogodkov in odločanje o pošiljanju obvestil. |
| **notification-function** | Pošiljanje e-poštnih obvestil uporabnikom (serverless, Google Cloud Functions). |

### 2.2 Podrobni opis mikrostoritev

### **users**
- **Odgovornost:** Registracija uporabnikov, avtentikacija, avtorizacija ter shranjevanje uporabniških nastavitev.
- **Podatki:** Uporabniški računi, vloge, pripadnost organizacijam ter preference glede pregledovanja in prejemanja obvestil.
- **API:** GraphQL API.
- **Podatkovna baza:** MongoDB.
- **Komunikacija:** Sinhrona (GraphQL). Storitev uporabljata frontend in `companies-filter`.

### **arso-sync**
- **Odgovornost:** Periodična sinhronizacija vremenskih opozoril iz sistema ARSO.
- **Podatki:** Vremenska opozorila v CAP/XML formatu, pretvorjena v interno podatkovno obliko.
- **API:** Brez javnega HTTP vmesnika.
- **Podatkovna baza:** PostgreSQL.
- **Komunikacija:** Asinhrona – objavljanje dogodkov v RabbitMQ ob novih ali posodobljenih opozorilih.

### **arso-service**
- **Odgovornost:** Ponuja REST API za dostop do trenutno veljavnih vremenskih opozoril.
- **Podatki:** Aktivna vremenska opozorila po regijah.
- **API:** REST HTTP (npr. `GET /events/active`).
- **Podatkovna baza:** PostgreSQL (samo branje).
- **Komunikacija:** Sinhrona (REST). Storitev uporablja companies-filter`.

### **companies-sync**
- **Odgovornost:** Upravljanje dogodkov organizacij, ki želijo obveščati svoje uporabnike oz. zaposlene (npr. zapore cest, požari, nevarne razmere).
- **Podatki:** Dogodki organizacij in razporedi dežurnih oseb.
- **API:** REST HTTP API.
- **Podatkovna baza:** PostgreSQL.
- **Komunikacija:** Sinhrona (REST) ter asinhrona – objavljanje dogodkov v RabbitMQ.

### **companies-filter**
- **Odgovornost:** Filtriranje dogodkov in odločanje, katerim uporabnikom je treba poslati obvestila.
- **Podatki:** Dogodki, uporabniške preference, podatki o dežurnih osebah.
- **API:** REST HTTP API za frontend.
- **Podatkovna baza:** Nima lastne baze.
- **Komunikacija:**  
  - Asinhrona: consumer v RabbitMQ (dogodki iz `arso-sync` in `companies-sync`)
  - Sinhrona: poizvedbe na `users`, `arso-service` in `companies-sync`

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

### 2.3 Komunikacija med storitvami

### Sinhrona komunikacija (REST / GraphQL)
- Frontend → users (GraphQL)
- Frontend → companies-filter (REST)
- Frontend → companies-sync (REST)
- companies-filter → users (GraphQL)
- companies-filter → arso-service, companies-sync (REST)
- companies-filter → notification-function (HTTP trigger)

### Asinhrona komunikacija (event-driven)
- **Sporočilni sistem:** RabbitMQ
- **Producenti:** `arso-sync`, `companies-sync`
- **Odjemalec:** `companies-filter`
- **Vzorec:** dogodkovno vodena arhitektura (event-driven)

### 2.4 Vloga podatkovnih baz in zunanjih storitev

| Tehnologija | Uporaba |
|------------|--------|
| **PostgreSQL** | Vremenska opozorila, dogodki organizacij, dežurstva |
| **MongoDB** | Uporabniški računi in nastavitve |
| **RabbitMQ** | Asinhrona komunikacija med mikrostoritvami |
| **Google Cloud Secrets** | Varna hramba API ključev in konfiguracije |
| **Brevo API** | Pošiljanje e-poštnih obvestil |

### 2.5 API dokumentacija

Dokumentacija API-jev (OpenAPI/Swagger) je dostopna na naslednjem naslovu: **https://rso-14.github.io/sistem-za-obvescanje/api/**

Dokumentacija zajema vse mikrostoritve (users, arso-service, companies-sync, companies-filter) z opisom končnih točk, parametrov, primeri zahtevkov/odgovorov in napak. Funkcija *Try it out* je izklopljena, saj je prikaz namenjen pregledovanju specifikacije, ne izvajanju klicev.

> Opomba: ista dokumentacija je na voljo v repozitoriju na poti `docs/api/index.html` (datoteka `docs/api/openapi.yaml`).

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

Projekt se lokalno izvaja v okolju Kubernetes z uporabo orodja kind (Kubernetes in Docker). Vse mikrostoritve in pripadajoča infrastruktura (baze, sporočilni sistem, ingress) se poganjajo znotraj lokalnega kind clustra.

Ukazi v nadaljevanju so prikazani za okolje Windows.

### 7.1 Zahteve

Za vzpostavitev lokalnega razvojnega okolja so potrebna naslednja orodja:

- Git  
- Docker  
- Kubernetes CLI (`kubectl`)  
- kind (Kubernetes in Docker)  
- Helm  
- Node.js (za zagon frontend aplikacije)

### 7.2 Pridobitev izvorne kode

Izvorna koda sistema se pridobi s kloniranjem Git repozitorija:

```bash
git clone https://github.com/RSO-14/sistem-za-obvescanje.git
cd sistem-za-obvescanje
```

### 7.3 Vzpostavitev lokalnega Kubernetes clustra (kind)

Vzpostavitev lokalnega Kubernetes clustra se izvede v okolju Windows z uporabo lupine PowerShell, ki se zažene v administratorskem načinu.  kolikor orodje `kind` še ni nameščeno, ga je mogoče namestiti z uporabo upravljalnika paketov `winget`:

```powershell
winget install Kubernetes.kind
```

Lokalni Kubernetes cluster se ustvari z orodjem kind. Konfiguracija clustra je podana neposredno prek standardnega vhoda, brez uporabe ločene konfiguracijske datoteke. V konfiguraciji so definirane preslikave vrat, ki omogočajo dostop do Kubernetes storitev iz lokalnega okolja prek NodePort mehanizma.

```powershell
@"
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  extraPortMappings:
  - containerPort: 30080
    hostPort: 30080
    protocol: TCP
  - containerPort: 30443
    hostPort: 30443
    protocol: TCP
"@ | kind create cluster --name dev-cluster --config -
```

Preverjanje stanja clustra:

```bash
kubectl cluster-info
kubectl get nodes -o wide
```

### 7.4 Namestitev Ingress controllerja (Traefik)

Za sprejem zunanjega HTTP/HTTPS prometa v Kubernetes cluster se uporablja Ingress controller Traefik, ki deluje kot vstopna točka v sistem in promet usmerja do ustreznih Kubernetes Service virov.

```bash
helm repo add traefik https://traefik.github.io/charts
helm repo update

helm install traefik traefik/traefik \
  --set service.type=NodePort \
  --set ports.web.nodePort=30080 \
  --set ports.websecure.nodePort=30443
```

Preverjanje, ali je Traefik uspešno nameščen:

```bash
kubectl -n default get pods -l app.kubernetes.io/name=traefik -o wide
kubectl -n default rollout status deployment/traefik
```

### 7.5 Namestitev infrastrukturnih komponent

Pred namestitvijo aplikacijskih mikrostoritev se v lokalni Kubernetes cluster namestijo infrastrukturne komponente, ki zagotavljajo osnovne podporne funkcionalnosti sistema. V okviru projekta se uporabljata naslednji infrastrukturni komponenti:
- Traefik – Ingress controller, ki deluje kot vstopna točka v Kubernetes cluster in omogoča sprejem ter usmerjanje zunanjega HTTP/HTTPS prometa do ustreznih Kubernetes Service virov,
- RabbitMQ – sporočilni sistem za asinhrono komunikacijo med mikrostoritvami.

Traefik se namesti z uporabo uradnega Helm charta:

```bash
helm upgrade --install traefik traefik/traefik \
  -f services/infrastructure/values.yaml
```

Po namestitvi se preveri uspešnost zagona Ingress controllerja:
```bash
kubectl rollout status deployment/traefik -n default
```

RabbitMQ se namesti z uporabo Kubernetes manifestov:

```bash
kubectl apply -f services/infrastructure/rabbitmq-pvc.yaml
kubectl apply -f services/infrastructure/rabbitmq-deployment.yaml
kubectl apply -f services/infrastructure/rabbitmq-service.yaml
```

Po namestitvi infrastrukturnih komponent se preveri stanje ustvarjenih virov:

```bash
kubectl get pods,svc -o wide
```
Delovanje RabbitMQ je možno preveriti tudi prek spletnega  vmesnika. V ta namen se uporabi `kubectl port-forward`, ki lokalno preslika vrata storitve:

```bash
kubectl port-forward svc/rabbitmq 15672:15672
```
Spletni vmesnik je nato dostopen na naslovu: http://localhost:15672

### 7.6 Namestitev mikrostoritev

Vsaka mikrostoritev ima lastne Kubernetes manifeste, organizirane v imeniku `services/<storitev>/k8s/`. Namestitev mikrostoritev poteka enotno za vse komponente sistema.

Primer namestitve vseh mikrostoritev:

```bash
kubectl apply -f services/arso-sync/k8s/
kubectl apply -f services/companies-sync/k8s/
kubectl apply -f services/users/k8s/
kubectl apply -f services/companies-filter/k8s/
kubectl apply -f services/arso-service/k8s/
```

Preverjanje, ali so vsi podi v stanju Running oziroma ali so CronJob opravila ustvarjena:

```bash
kubectl get pods,svc -o wide
kubectl get deployments,cronjobs -o wide
```

### 7.7 Upravljanje konfiguracije v lokalnem okolju

Konfiguracija aplikacije je ločena od izvorne kode in je upravljana prek Kubernetes virov `ConfigMap` in `Secret`.

`ConfigMap` vsebuje nesenzitivne konfiguracijske parametre (npr. naslove storitev, imena virov, parametre delovanja).

`Secret` vsebuje občutljive podatke (gesla, API ključe). V repozitoriju so shranjene zgolj nadomestne (placeholder) vrednosti, dejanske vrednosti pa se nastavijo v ciljnem okolju (lokalno ali oblačno).

Uveljavitev sprememb konfiguracije:

```bash
kubectl apply -f services/<storitev>/k8s/
kubectl rollout restart deployment/<ime-deploymenta>
```

Preverjanje, ali so bili podi ponovno ustvarjeni in tečejo:

```bash
kubectl get pods -o wide
kubectl rollout status deployment/<ime-deploymenta>
```

### 7.8 Lokalni razvoj in spremembe kode

Pri lokalnem razvoju je potrebno ločevati med:

- spremembami aplikacijske kode,
- spremembami Kubernetes manifestov.

#### 7.8.1 Spremembe aplikacijske kode (src/)

Če se spremeni aplikacijska logika mikrostoritve, je potrebno ustvariti novo Docker sliko in jo naložiti v lokalni kind cluster. Nato je potrebno ponovno zagnati pode, da se nova slika dejansko uporabi.

Tipični postopek za posamezno mikrostoritev:

```bash
cd services/<storitev>
docker build -t <storitev>:latest .
kind load docker-image <storitev>:latest --name dev-cluster
kubectl rollout restart deployment <ime-deploymenta>
```

V tem načinu mora `Deployment` uporabljati lokalno sliko in politiko nalaganja:

```yaml
imagePullPolicy: IfNotPresent
```

#### 7.8.2 Spremembe Kubernetes manifestov (k8s/)

Če se spreminjajo zgolj Kubernetes manifesti (`Deployment`, `Service`, `Ingress`, `ConfigMap`, `Secret`), ponovna gradnja Docker slik ni potrebna. Zadostuje ponovna uveljavitev manifestov, po potrebi pa tudi ponovni zagon podov.

```bash
kubectl apply -f services/<storitev>/k8s/
kubectl rollout restart deployment <ime-deploymenta>
```

Preverjanje stanja po uveljavitvi sprememb:

```bash
kubectl rollout status deployment <ime-deploymenta>
kubectl get pods,svc -o wide
```

### 7.9 Dostop do storitev in testiranje

Dostop do storitev je omogočen prek lokalnega Ingress controllerja. Vsaka mikrostoritev je dosegljiva preko domene, določene v njeni `IngressRoute` konfiguraciji (npr. `users.localhost`).

Za pravilno delovanje je potrebno ročno dodati naslednje vrstice v datoteko `C:\Windows\System32\drivers\etc\hosts`:

```bash
add 127.0.0.1 arso-service.localhost companies-filter.localhost users.localhost companies.localhost
```

Primeri URL-jev za testiranje (če so domene ustrezno konfigurirane):

- http://users.localhost:30080
- http://companies-filter.localhost:30080/health
- http://companies-sync.localhost:30080/organizations

Prav tako je možno uporabiti `kubectl port-forward` za neposreden dostop do storitev, na primer:

```bash
kubectl port-forward svc/users 8000:80
```
Spletni vmesnik je nato dostopen na naslovu: http://localhost:8000/graphql

### 7.10 Zagon frontenda (lokalno)

Frontend aplikacija se zaganja ločeno od Kubernetes okolja:

```bash
cd so-frontend
npm install
npm run dev
```

Privzeta pot do aplikacije:

```
http://localhost:3000
```

### 7.11 Zaključek lokalnega razvojnega cikla

Ko so spremembe uspešno preverjene v lokalnem okolju, se izvorna koda in konfiguracija shranita v Git repozitorij:

```bash
git status
git add .
git commit -m "Local changes tested"
git push
```

S tem je zaključen lokalni razvojni cikel. Nadaljnja namestitev in posodabljanje sistema v oblačnem okolju poteka avtomatizirano prek CI/CD mehanizma, opisanega v naslednjem poglavju.

## 8. Namestitev v Google Cloud

Oblačna različica sistema se izvaja v okolju Google Kubernetes Engine (GKE), pri čemer se vse mikrostoritve in infrastruktura avtomatsko nameščajo prek CI/CD mehanizma, implementiranega z GitHub Actions.

### 8.1 CI/CD z GitHub Actions

Vsaka sprememba v veji `main` sproži avtomatsko CI/CD verigo:

- zgradi se nova Docker slika za vsako storitev,
- slike se potisnejo v `Google Container Registry` (GCR),
- izvede se `kubectl apply` nad manifesti na GKE clusterju.

CI/CD poteka iz `.github/workflows/ci.yml`, ki vključuje dostop do GCP prek service account ključa in `gcloud` nastavitev.

### 8.2 Prilagoditve za deploy v GKE

Pred deployem v oblak je potrebno zagotoviti:

- da `imagePullPolicy` v vseh manifestih ni `IfNotPresent`, temveč `Always`,
- da se uporabljajo prave slike iz GCR (npr. `gcr.io/<project-id>/companies-filter:latest`),
- da so GCP Secrets in ConfigMaps pravilno nastavljeni v oblačnem okolju (prek `kubectl` ali UI),
- da `kind` specifične nastavitve niso prisotne (npr. `NodePort` porte, ki se v oblaku ne uporabljajo).

### 8.3 Google Cloud Functions

Funkcija `notification-function` je implementirana kot ločena serverless funkcija in se ne izvaja znotraj Kubernetes clustra. Funkcija bere Secrets in konfiguracijo neposredno iz GCP okolja.

## 9. Zunanje integracije

Sistem vključuje integracije z zunanjimi viri podatkov in tretjeosebnimi storitvami, ki omogočajo pridobivanje vremenskih opozoril ter pošiljanje elektronskih obvestil uporabnikom.

### 9.1 ARSO

Vremenska opozorila se pridobivajo iz javno dostopnega CAP/XML vira Agencije RS za okolje (ARSO), ki je dostopen prek statičnih HTTP končnih točk. Integracijo izvaja mikrostoritev `arso-sync`, implementirana kot periodično opravilo (CronJob), ki podatke obdela in shrani v PostgreSQL ter ob spremembah sproži dogodke v RabbitMQ. Dostop do vira ne zahteva avtentikacije.

### 9.2 Brevo

Pošiljanje elektronskih obvestil je izvedeno prek serverless funkcije v oblačnem okolju, ki uporablja storitev Brevo kot zunanjo SaaS platformo za transakcijsko e-pošto. Komunikacija poteka prek HTTPS REST vmesnika z uporabo JSON sporočil, avtentikacija pa z API ključem, pri čemer so API ključ in naslov pošiljatelja shranjeni v Kubernetes Secrets. Funkcija se sproži asinhrono ob zaznavi relevantnih dogodkov.