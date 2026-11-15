# ── Create Platform Credentials Secret in Rahti ─────────────────────────────────
# Target Project: sdx-assignment-mmahdi

$PROJECT = "sdx-assignment-mmahdi"

Write-Host "Creating platform-credentials secret in project $PROJECT..." -ForegroundColor Cyan

kubectl create secret generic platform-credentials `
  -n $PROJECT `
  --from-literal=DJANGO_DEBUG=False `
  --from-literal=ALLOWED_HOSTS="*" `
  --from-literal=CSRF_TRUSTED_ORIGINS="https://django-route-$PROJECT.2.rahtiapp.fi,https://django-route-$PROJECT.apps.2.rahti.csc.fi,https://excellstudy.site,https://www.excellstudy.site" `
  --from-literal=REDIS_URL="redis://redis-service:6379/0" `
  --from-literal=SUPABASE_DB_URL="postgresql://postgres.oofpzndzqiuttssmvsty:_3Qv6.aS4_MrKWe@aws-1-ap-south-1.pooler.supabase.com:6543/postgres" `
  --from-literal=NEO4J_URL="neo4j+s://7690def6.databases.neo4j.io" `
  --from-literal=NEO4J_USER="neo4j" `
  --from-literal=NEO4J_PASSWORD="5uKEp2-PSq1MFiNtW91gHFS81XwagEjcSDkn8m1MaRA" `
  --from-literal=PIPELINE_WEBHOOK_SECRET="393d85530c926319212a4dc43046b117ae61dfa3622f3b5f567ba9a0251b7f6b" `
  --from-literal=LEARNER_CONTEXT_MCP_URL="http://learner-context-mcp-server:8001" `
  --from-literal=KNOWLEDGE_GRAPH_MCP_URL="http://knowledge-graph-mcp-server:8002" `
  --from-literal=CONTENT_MCP_URL="http://content-mcp-server:8003" `
  --from-literal=GITHUB_DISPATCH_TOKEN="$env:GITHUB_DISPATCH_TOKEN" `
  --from-literal=GITHUB_REPO_OWNER="MohammadAil67" `
  --from-literal=GITHUB_REPO_NAME="excellstudy" `
  --from-literal=GCP_PROJECT_ID="project-098924cb-e28c-4177-901" `
  --from-literal=GAR_LOCATION="asia-south1" `
  --from-literal=GAR_REPOSITORY="excellstudy" `
  --dry-run=client -o yaml | kubectl apply -f -

Write-Host "Secret created successfully!" -ForegroundColor Green
