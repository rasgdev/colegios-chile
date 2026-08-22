#!/bin/bash
# setup-gcp-actions.sh — Setup único de GCP para GitHub Actions.
# Crea: bucket de estado (GCS), service account, pool/provider WIF y el binding.
# Idempotente: se puede re-ejecutar sin romper nada.
# Al final imprime los valores a pegar en GitHub Secrets.
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
log()  { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
die()  { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ── Configuración (editable / por env) ────────────────────
PROJECT="${PROJECT_ID:-my-project-colegios-chile}"
REGION="${GCP_REGION:-us-central1}"
BUCKET="${TF_STATE_BUCKET:-colegios-chile-tfstate}"
SA_NAME="${DEPLOY_SA_NAME:-deploy-gha}"
TF_SA_NAME="${TERRAFORM_SA_NAME:-terraform-gha}"
POOL="github-pool"
PROVIDER="github"
REPO="${GITHUB_REPO:-rasgdev/colegios-chile}"

echo "=== Setup GitHub Actions → GCP ==="
echo "  Proyecto : ${PROJECT}"
echo "  Repo     : ${REPO}"
echo "  Bucket   : ${BUCKET}"
echo ""

# ── Pre-checks ─────────────────────────────────────────────
command -v gcloud >/dev/null || die "gcloud no instalado. Instala el CLI de Google Cloud."

ACC=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | head -1)
[ -n "${ACC}" ] || die "No hay sesión activa de gcloud. Ejecuta: gcloud auth login"
log "Sesión activa: ${ACC}"
echo ""

# ── 0. Habilitar APIs necesarias (idempotente) ─────────────
echo "=== Habilitando APIs ==="
gcloud services enable \
  compute.googleapis.com \
  serviceusage.googleapis.com \
  cloudresourcemanager.googleapis.com \
  iam.googleapis.com \
  storage.googleapis.com \
  oslogin.googleapis.com \
  iap.googleapis.com \
  --project="${PROJECT}"
log "APIs habilitadas"
echo ""

# ── 1. Bucket de estado (bootstrap, fuera del config principal) ──
if gcloud storage buckets describe "gs://${BUCKET}" >/dev/null 2>&1; then
  warn "Bucket ${BUCKET} ya existe; omito."
else
  gcloud storage buckets create "gs://${BUCKET}" \
    --project="${PROJECT}" --location="${REGION}"
  gcloud storage buckets update "gs://${BUCKET}" --versioning
  log "Bucket creado con versioning: gs://${BUCKET}"
fi

# ── 2. Service Accounts ────────────────────────────────────
# deploy-gha:   mínimo. Solo roles de deploy (los crea Terraform via main.tf).
# terraform-gha: amplio. Necesita los roles de terraform (bootstrap via script).
DEPLOY_SA_EMAIL="${SA_NAME}@${PROJECT}.iam.gserviceaccount.com"
TF_SA_EMAIL="${TF_SA_NAME}@${PROJECT}.iam.gserviceaccount.com"

for sa in "${SA_NAME}" "${TF_SA_NAME}"; do
  email="${sa}@${PROJECT}.iam.gserviceaccount.com"
  if gcloud iam service-accounts describe "${email}" --project="${PROJECT}" >/dev/null 2>&1; then
    warn "SA ${email} ya existe; omito creación."
  else
    gcloud iam service-accounts create "${sa}" \
      --project="${PROJECT}" --display-name="GitHub Actions (${sa})"
    log "SA creado: ${email}"
  fi
done

# Roles amplios SOLO para el SA de terraform (bootstrap, idempotente).
for role in \
  roles/compute.admin \
  roles/serviceusage.serviceUsageAdmin \
  roles/resourcemanager.projectIamAdmin \
  roles/storage.objectAdmin; do
  gcloud projects add-iam-policy-binding "${PROJECT}" \
    --member="serviceAccount:${TF_SA_EMAIL}" --role="${role}" >/dev/null
  log "Rol ${role} → terraform-gha"
done

# Limpieza: quitar roles amplios de deploy-gha si se asignaron en runs anteriores.
for role in \
  roles/compute.admin \
  roles/serviceusage.serviceUsageAdmin \
  roles/resourcemanager.projectIamAdmin \
  roles/storage.objectAdmin; do
  if gcloud projects remove-iam-policy-binding "${PROJECT}" \
    --member="serviceAccount:${DEPLOY_SA_EMAIL}" --role="${role}" >/dev/null 2>&1; then
    log "Rol ${role} revocado de deploy-gha"
  else
    warn "Sin ${role} en deploy-gha; omito."
  fi
done

# ── 3. WIF: pool + provider + binding al repo ──────────────
if gcloud iam workload-identity-pools describe "${POOL}" \
  --location=global --project="${PROJECT}" >/dev/null 2>&1; then
  warn "Pool ${POOL} ya existe; omito."
else
  gcloud iam workload-identity-pools create "${POOL}" \
    --location=global --project="${PROJECT}" --display-name="GitHub Actions"
  log "Pool creado: ${POOL}"
fi

if gcloud iam workload-identity-pools providers describe "${PROVIDER}" \
  --location=global --workload-identity-pool="${POOL}" --project="${PROJECT}" >/dev/null 2>&1; then
  warn "Provider ${PROVIDER} ya existe; omito."
else
  gcloud iam workload-identity-pools providers create-oidc "${PROVIDER}" \
    --location=global --workload-identity-pool="${POOL}" --project="${PROJECT}" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --display-name="GitHub OIDC" \
    --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
    --attribute-condition="assertion.repository=='${REPO}' && assertion.ref.startsWith('refs/heads/main')"
  log "Provider OIDC creado (solo repo ${REPO} + rama main)."
fi

PROJECT_NUMBER=$(gcloud projects describe "${PROJECT}" --format="value(projectNumber)")
PRINCIPAL="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL}/attribute.repository/${REPO}"
for email in "${DEPLOY_SA_EMAIL}" "${TF_SA_EMAIL}"; do
  gcloud iam service-accounts add-iam-policy-binding "${email}" \
    --project="${PROJECT}" --role=roles/iam.workloadIdentityUser \
    --member="${PRINCIPAL}" >/dev/null
  log "Binding WIF → ${email}"
done

# ── 4. Salida ──────────────────────────────────────────────
WIP=$(gcloud iam workload-identity-pools providers describe "${PROVIDER}" \
  --location=global --workload-identity-pool="${POOL}" --project="${PROJECT}" --format="value(name)")

echo ""
echo "=========================================================="
echo " Setup completo. Copia estos valores a GitHub Secrets:"
echo "=========================================================="
echo "WORKLOAD_IDENTITY_PROVIDER  = ${WIP}"
echo "SERVICE_ACCOUNT             = ${DEPLOY_SA_EMAIL}    (deploy.yml)"
echo "TERRAFORM_SERVICE_ACCOUNT   = ${TF_SA_EMAIL}    (infra.yml)"
echo ""
echo "Además (Settings → Secrets and variables → Actions):"
echo "  TF_VAR_project_id      = ${PROJECT}"
echo "  TF_VAR_region          = ${REGION}"
echo "  TF_VAR_zone            = us-central1-a"
echo "  TF_VAR_db_password     = <password de PostgreSQL de producción>"
echo "  TF_VAR_repo_url        = https://github.com/${REPO}.git"
echo "  TF_VAR_repo_branch     = main"
echo "  TF_VAR_deploy_sa_email = ${DEPLOY_SA_EMAIL}"
echo ""
echo "Después: Actions → Infra GCP (manual) → Run workflow → Apply"
echo "para crear la VM (única vez)."