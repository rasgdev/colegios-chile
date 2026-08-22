# Deploy a GCP — Setup único y operación

Proyecto: `my-project-colegios-chile`. Stack: VM Compute Engine (e2-micro, free tier) +
PostgreSQL + FastAPI + Astro SSR. Deploy desde GitHub Actions vía **IAP tunnel + OS Login**
(Workload Identity Federation, sin claves estáticas).

## Costo (aprox. $0/mes)

| Recurso | Costo |
|---|---|
| VM e2-micro + disco 20 GB estándar (us-central1) | Free tier |
| Bucket GCS de estado (regional `us-central1`, < 5 GB) | Free tier |
| IP estática adjunta a la VM en ejecución | Gratis |
| Firewalls, IAP API, IAM, WIF, Service Account, OS Login | Gratis |
| GitHub Actions (repo público) | Gratis / ilimitado |

**Únicos costos posibles (evitables):**
1. **IP estática**: gratis solo mientras la VM está **en ejecución**. Si detienes la VM, esa IP pasa a facturarse (~$3.6/mes). No la detengas (o libérala con `terraform destroy`).
2. **Egress de red**: el free tier incluye ~1 GB/mes de salida (Norteamérica). Tráfico público del sitio más allá de eso se cobra. Para un demo es imperceptible.
3. **Bucket**: si se creara sin `--location` queda multi-región (más caro por GB). El script usa `us-central1` regional.

## Orden de ejecución (hacerlo una vez)

1. Crear el repo en GitHub y pushear.
2. Crear el bucket GCS para el estado de Terraform.
3. Crear el Service Account y darle roles.
4. Crear el pool/provider de WIF y enlazarlo al repo.
5. Setear los secrets de GitHub.
6. `terraform apply` manual (crea la VM por única vez).
7. A partir de ahí, cada push a `main` despliega solo (sin recrear la VM).

> **Automatiza los pasos 2–4** con `scripts/setup-gcp-actions.sh`
> (idempotente, valida y al final imprime los secrets). Alternativa manual abajo.

---

## 1. Repo + push

```bash
git init && git add -A && git commit -m "init"
gh repo create rasgdev/colegios-chile --public --source=. --push
```

## 2. Bucket de estado (privado por defecto)

```bash
PROJECT=my-project-colegios-chile
gcloud storage buckets create gs://colegios-chile-tfstate --project="$PROJECT" --location=us-central1
gcloud storage buckets update gs://colegios-chile-tfstate --versioning
```

## 3. Service Account (identidad de GitHub Actions)

```bash
gcloud iam service-accounts create deploy-gha \
  --project="$PROJECT" \
  --display-name="GitHub Actions deploy"

SA=deploy-gha@$PROJECT.iam.gserviceaccount.com

# Roles para correr terraform (apply del primer commit de infra):
gcloud projects add-iam-policy-binding "$PROJECT" \
  --member="serviceAccount:$SA" \
  --role=roles/compute.admin
gcloud projects add-iam-policy-binding "$PROJECT" \
  --member="serviceAccount:$SA" \
  --role=roles/serviceusage.serviceUsageAdmin
gcloud projects add-iam-policy-binding "$PROJECT" \
  --member="serviceAccount:$SA" \
  --role=roles/resourcemanager.projectIamAdmin
gcloud projects add-iam-policy-binding "$PROJECT" \
  --member="serviceAccount:$SA" \
  --role=roles/storage.objectAdmin

# Roles de deploy (IAP + OS Login + lectura) los crea Terraform (main.tf),
# así que se aplican en el paso 6 automáticamente.
```

## 4. Workload Identity Federation

```bash
gcloud iam workload-identity-pools create github-pool \
  --location=global --project="$PROJECT" \
  --display-name="GitHub Actions"

gcloud iam workload-identity-pools providers create-oidc github \
  --location=global \
  --workload-identity-pool=github-pool \
  --project="$PROJECT" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --display-name="GitHub OIDC" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
  --attribute-condition="assertion.repository=='rasgdev/colegios-chile' && assertion.ref.startsWith('refs/heads/main')"

PROJECT_NUMBER=$(gcloud projects describe "$PROJECT" --format="value(projectNumber)")
gcloud iam service-accounts add-iam-policy-binding "$SA" \
  --project="$PROJECT" \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/attribute.repository/rasgdev/colegios-chile"

# Obten el WORKLOAD_IDENTITY_PROVIDER:
gcloud iam workload-identity-pools providers describe github \
  --location=global --workload-identity-pool=github-pool \
  --project="$PROJECT" --format="value(name)"
```

> El attribute-condition restringe el acceso **solo** al repo `rasgdev/colegios-chile`
> y **solo** a la rama `main`. Forks y PRs no pueden obtener tokens.

## 5. Secrets de GitHub

Crear en GitHub → Settings → Secrets and variables → Actions:

| Secret | Valor |
|---|---|
| `WORKLOAD_IDENTITY_PROVIDER` | output del comando anterior |
| `SERVICE_ACCOUNT` | `deploy-gha@my-project-colegios-chile.iam.gserviceaccount.com` |
| `TF_VAR_project_id` | `my-project-colegios-chile` |
| `TF_VAR_region` | `us-central1` |
| `TF_VAR_zone` | `us-central1-a` |
| `TF_VAR_db_password` | password de PostgreSQL de producción (tuya, nunca en git) |
| `TF_VAR_repo_url` | `https://github.com/rasgdev/colegios-chile.git` |
| `TF_VAR_repo_branch` | `main` |
| `TF_VAR_deploy_sa_email` | `deploy-gha@my-project-colegios-chile.iam.gserviceaccount.com` |

## 6. Primer `terraform apply` (crea la VM una sola vez)

Desde GitHub Actions: **Actions → Infra GCP (manual) → Run workflow → Apply**.

O localmente (si prefieres):

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
# edita terraform.tfvars: db_password (real), ssh_source_ranges (opcional, [] si solo IAP)
export TF_VAR_deploy_sa_email="$SA"
gcloud auth application-default login
terraform init -backend-config=bucket=colegios-chile-tfstate -backend-config=prefix=infra
terraform plan
terraform apply
```

Esto crea la VM con `startup.sh` (bootstrap) + habilita IAP + OS Login + IAM de deploy.
El `startup.sh` termina llamando a `scripts/deploy.sh` (deploy inicial).

## 7. Deploys siguientes (automáticos)

- `push` a `main` con cambios de código → workflow **Deploy a GCP**: SSH por IAP → `deploy.sh`.
- Rollback → **Deploy a GCP → Run workflow → ref**: commit/tag anterior.
- Cambios de `infra/**` → solo con **Infra GCP (manual)** (nunca automático: no se recrea la VM).

## Notas de seguridad

- SSH público cerrado: `ssh_source_ranges` por defecto `[]`; admin entra con
  `gcloud compute ssh --tunnel-through-iap colegios-server --zone us-central1-a`.
- PostgreSQL escucha solo en `localhost` de la VM.
- El estado de Terraform (contiene `db_password`) vive en el bucket GCS **privado**, nunca en git.
- Ningún workflow usa `pull_request_target`; los secrets solo se usan en `push` a main.
- El repo es público: no se suben `.env`, `terraform.tfvars` ni `*.tfstate*` (verificado en `.gitignore`).