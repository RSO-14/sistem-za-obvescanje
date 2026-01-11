# sistem-za-obvescanje

## Pregled

**sistem-za-obvescanje** je oblačno-naravnana aplikacija za centraliziran pregled aktualnih in relevantnih dogodkov ter za obveščanje uporabnikov prek elektronske pošte. Namenjena je splošni javnosti za pregled vremenskih opozoril sistema ARSO ter organizacijam in podjetjem, ki potrebujejo sistem za obveščanje svojih zaposlenih o internih ali zunanjih dogodkih.

## Arhitekturni pregled

Sistem temelji na mikrostoritveni arhitekturi z jasno ločenimi odgovornostmi posameznih komponent. Komunikacija med storitvami poteka prek sinhronih (REST, GraphQL) in asinhronih (event-driven) mehanizmov.

### Mikrostoritve

- **users** – upravljanje uporabnikov, avtentikacije in uporabniških preferenc
- **arso-sync** – periodičen zajem in obdelava vremenskih opozoril iz sistema ARSO
- **arso-service** – API za dostop do shranjenih vremenskih opozoril
- **companies-sync** – upravljanje dogodkov organizacij in dežurnih oseb
- **companies-filter** – filtriranje dogodkov in odločanje o pošiljanju obvestil
- **serverless komponenta** - pošiljanje e-poštnih obvestil uporabnikom (serverless, Google Cloud Functions)


### Tehnološki sklad

- **Backend:** Python, FastAPI, Strawberry GraphQL, Uvicorn  
- **Podatkovna hramba:** PostgreSQL, MongoDB  
- **Sporočilni sistem:** RabbitMQ (dogodkovno vodena komunikacija)  
- **Kontejnerizacija:** Docker, Docker Buildx  
- **Orkestracija:** Kubernetes (lokalno: kind, oblak: GKE)
- **Upravljanje konfiguracije:** Okoljske spremenljivke, Kubernetes ConfigMaps in Secrets  
- **Frontend:** Next.js (React), Tailwind CSS  
- **CI/CD:** GitHub Actions (CI – build & push v Docker Hub), Flux CD (CD – GitOps deploy na Kubernetes)
- **Zunanje integracije:** Javni CAP/XML vir ARSO, Brevo API  
- **Oblačna platforma:** Google Cloud (GKE, serverless storitve)


## Dokumentacija

Podrobna tehnična dokumentacija sistema je na voljo v: 

📄 [`docs/technical-documentation.md`](docs/technical-documentation.md)


## Lokalno razvojno okolje
Projekt se lokalno izvaja v okolju Kubernetes z uporabo orodja kind. Mikrostoritve, podatkovne baze in Ingress controller se poganjajo znotraj lokalnega kind clustra.

### 1. Zahteve
- Git 
- Docker  
- kind  
- kubectl  
- Helm  
- Node.js (za frontend)

### 2. Kloniranje repozitorija
```bash
git clone https://github.com/RSO-14/sistem-za-obvescanje.git
cd sistem-za-obvescanje
```

### 3. Vzpostavitev lokalnega kind clustra (Windows PowerShell)
```powershell
winget install Kubernetes.kind

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

### 4. Namestitev Traefik in infrastrukture
```bash
helm repo add traefik https://traefik.github.io/charts
helm repo update

helm install traefik traefik/traefik \
  --set service.type=NodePort \
  --set ports.web.nodePort=30080 \
  --set ports.websecure.nodePort=30443

helm upgrade --install traefik traefik/traefik -f services/infrastructure/values.yaml

kubectl apply -f services/infrastructure/rabbitmq-pvc.yaml
kubectl apply -f services/infrastructure/rabbitmq-deployment.yaml
kubectl apply -f services/infrastructure/rabbitmq-service.yaml
```

### 5. Namestitev mikrostoritev
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

### 6. Dostop do storitev in testiranje
Za pravilno delovanje je potrebno ročno dodati naslednje vrstice v datoteko `C:\Windows\System32\drivers\etc\hosts`:

```
127.0.0.1 users.localhost companies-filter.localhost companies-sync.localhost arso-service.localhost
```
Primer URL-ja za testiranje (če so domene ustrezno konfigurirane): http://companies-filter.localhost:30080/health

Prav tako je možno uporabiti `kubectl port-forward` za neposreden dostop do storitev:
```bash
# RabbitMQ dashboard: http://localhost:15672
kubectl port-forward svc/rabbitmq 15672:15672
# GraphQL UI: http://localhost:8000/graphql
kubectl port-forward svc/users 8000:80
```

## Frontend

Frontend aplikacija je implementirana kot ločen projekt in komunicira z backendom prek REST in GraphQL API-jev:

🖥️ [Frontend repozitorij](https://github.com/RSO-14/so-frontend.git)