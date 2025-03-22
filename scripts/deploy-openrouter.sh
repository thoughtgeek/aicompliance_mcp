#!/bin/bash
# Deploy OpenRouter configuration to the EU AI Act compliance system

set -e

# Apply the new combined configuration
echo "Applying OpenRouter API Gateway configuration..."
kubectl apply -f k8s/eu-ai-act/api-gateway-openrouter.yaml

# Clean up the now-unnecessary services
echo "Cleaning up unnecessary services..."
kubectl delete deployment/embedding-service -n eu-ai-act --ignore-not-found=true
kubectl delete deployment/llm-service -n eu-ai-act --ignore-not-found=true
kubectl delete service/embedding-service -n eu-ai-act --ignore-not-found=true
kubectl delete service/llm-service -n eu-ai-act --ignore-not-found=true

# Wait for the API gateway to be ready
echo "Waiting for API gateway to be ready..."
kubectl rollout status deployment/api-gateway -n eu-ai-act

echo "Deployment complete! API Gateway is now configured to use OpenRouter for embeddings and LLM responses."
echo ""
echo "To port-forward the API Gateway, use port 8081 instead of 8080:"
echo "kubectl port-forward -n eu-ai-act svc/api-gateway 8081:8000 --address 0.0.0.0" 