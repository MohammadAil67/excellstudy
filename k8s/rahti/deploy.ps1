# ── ExcellStudy CSC Rahti Deployment Script ─────────────────────────────────────
# Target Project: sdx-assignment-mmahdi
# Target Registry: Docker Hub (public repository: mahdides1234)

$PROJECT = "sdx-assignment-mmahdi"
$DOCKERHUB_USER = "mahdides1234"

Write-Host "=== 1. Building Docker Images ===" -ForegroundColor Cyan
Write-Host "Building Django Web..."
docker build -t ${DOCKERHUB_USER}/excellstudy-django:latest -f Dockerfile .
if ($LASTEXITCODE -ne 0) { Write-Error "Django image build failed"; exit 1 }

Write-Host "Building MCP Base..."
docker build -t ${DOCKERHUB_USER}/mcp-base:latest -f Dockerfile.mcp .
if ($LASTEXITCODE -ne 0) { Write-Error "MCP image build failed"; exit 1 }

Write-Host "`n=== 2. Pushing Images to Docker Hub ===" -ForegroundColor Cyan
Write-Host "Pushing Django Web..."
docker push ${DOCKERHUB_USER}/excellstudy-django:latest

Write-Host "Pushing MCP Base..."
docker push ${DOCKERHUB_USER}/mcp-base:latest

Write-Host "`n=== 3. Applying Kubernetes Manifests to Rahti ($PROJECT) ===" -ForegroundColor Cyan
kubectl apply -f k8s/rahti/redis.yaml
kubectl apply -f k8s/rahti/mcp-servers.yaml
kubectl apply -f k8s/rahti/django-deployment.yaml
kubectl apply -f k8s/rahti/django-route.yaml

Write-Host "`n=== 4. Deployment Complete! Checking Pod Status ===" -ForegroundColor Green
kubectl get pods -n $PROJECT
kubectl get route django-route -n $PROJECT
