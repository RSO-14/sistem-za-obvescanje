# sistem-za-obvescanje

## Pregled

**sistem-za-obvescanje** je oblačno-naravnana aplikacija za centraliziran pregled aktualnih in relevantnih dogodkov ter za obveščanje uporabnikov prek elektronske pošte. Namenjena je splošni javnosti za pregled vremenskih opozoril sistema ARSO ter organizacijam in podjetjem, ki potrebujejo sistem za obveščanje svojih zaposlenih o internih ali zunanjih dogodkih.

## Arhitekturni pregled

Sistem temelji na mikrostoritveni arhitekturi z jasno ločenimi odgovornostmi posameznih komponent.  
Komunikacija med storitvami poteka prek sinhronih (REST, GraphQL) in asinhronih (event-driven) mehanizmov.


## Mikrostoritve

- **users** – upravljanje uporabnikov, avtentikacije in uporabniških preferenc
- **arso-sync** – periodičen zajem in obdelava vremenskih opozoril iz sistema ARSO
- **arso-service** – API za dostop do shranjenih vremenskih opozoril
- **companies-sync** – upravljanje dogodkov organizacij in dežurnih oseb
- **companies-filter** – filtriranje dogodkov in odločanje o pošiljanju obvestil
- **notification-function** – pošiljanje e-poštnih obvestil (serverless, Google Cloud Functions)


## Tehnološki sklad

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


## Dokumentacija

Podrobna tehnična dokumentacija sistema je na voljo v: 

📄 [`docs/technical-documentation.md`](docs/technical-documentation.md)


## Lokalno razvojno okolje

### Zahteve
- Docker
- kubectl
- kind

### Zagon sistema
> **TODO:** Dodati navodila za zagon sistema v lokalnem Kubernetes okolju (kind).


## Namestitev v oblak

Ciljno produkcijsko okolje temelji na Google Cloud Platform:
- Google Kubernetes Engine (GKE)
- Google Cloud Functions

> **TODO:** Dodati navodila za namestitev v oblačno okolje.


## Frontend

Frontend aplikacija je implementirana kot ločen projekt in komunicira z backendom prek REST in GraphQL API-jev.

🖥️ [Frontend repozitorij](https://github.com/RSO-14/so-frontend.git)