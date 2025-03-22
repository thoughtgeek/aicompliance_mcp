# EU AI Act Compliance System

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Kubernetes](https://img.shields.io/badge/Kubernetes-Ready-brightgreen)
![Docker](https://img.shields.io/badge/Docker-Powered-blue)

A production-ready, Kubernetes-native system for EU AI Act compliance documentation, risk assessment, and regulatory querying. This microservices architecture provides organizations with tools to understand, implement, and maintain compliance with the European Union's Artificial Intelligence Act.

## 🔍 Overview

The EU AI Act introduces comprehensive regulations for AI systems based on risk categories, requiring organizations to implement proper governance, risk assessment, and documentation processes. This system provides:

- Semantic search across EU AI Act regulatory content
- Structured knowledge representation of compliance requirements
- AI-powered compliance assessment and guidance
- Verifiable, source-traceable responses for audit readiness
- API-first design for integration with existing compliance tools

## 🏗️ System Architecture

![Architecture Diagram](docs/architecture-diagram.txt)

The system consists of five specialized microservices designed for efficient operation in Kubernetes:

### Knowledge Graph Service (TerminusDB)
- Stores structured regulatory data with relationships
- Models complex compliance relationships and dependencies
- Enables graph-based queries and traversals

### Vector Database Service (Qdrant)
- Enables semantic search across compliance documentation
- Stores high-dimensional vector embeddings of regulatory content
- Provides similarity-based retrieval with configurable thresholds

### Embedding Service
- Converts text queries to vector representations
- Optimized for minimal resource consumption
- Supports batched processing for efficiency

### LLM Service
- Generates factually grounded responses using retrieved knowledge
- Supports multiple LLM providers (OpenAI, Anthropic, Ollama)
- Includes factual verification and source tracing

### API Gateway
- Orchestrates workflows between components
- Provides a unified RESTful API interface
- Handles request routing, validation, and response formatting

## ✨ Features

- **Enterprise-Ready**: Production-grade components with health monitoring and horizontal scaling
- **Resource-Efficient**: Optimized for minimal resource consumption with configurable limits
- **Multi-Model Support**: Choose from OpenAI, Anthropic, or deploy local models via Ollama
- **Semantic Search**: Advanced vector-based search with relevance scoring
- **Fact Grounding**: All responses traced to specific regulatory sources for audit readiness
- **Flexible Deployment**: Deploy on any Kubernetes environment (cloud, on-premise, or local)
- **Customizable**: Modular design for easy extension and customization

## 🚀 Getting Started

### Prerequisites

- Kubernetes cluster (local or cloud)
- kubectl command-line tool
- Docker for local development
- Ingress controller (for external access)

### Quick Start (Local Development)

For local development with kind (Kubernetes IN Docker):

1. Install kind and create a cluster:
```bash
[ $(uname -m) = x86_64 ] && curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.27.0/kind-linux-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/
kind create cluster --name eu-ai-act
```

2. Add local hostname:
```bash
echo "127.0.0.1 eu-ai-act.local" | sudo tee -a /etc/hosts
```

3. Deploy the system:
```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/qdrant/
kubectl apply -f k8s/terminusdb/
kubectl apply -f k8s/embedding/
kubectl apply -f k8s/llm/
kubectl apply -f k8s/api-gateway/
```

4. Verify deployment:
```bash
kubectl get pods -n eu-ai-act
```
kubectl get pods -n eu-ai-act

Access the API at http://eu-ai-act.local/

### Production Deployment

For production deployment:

1. Configure persistent storage:
```bash
kubectl apply -f k8s/storage-class.yaml
```

2. Update resource limits in deployment files for production workloads

3. Configure TLS for secure communication:
```bash
kubectl apply -f k8s/certificates.yaml
```

4. Deploy monitoring stack:
```bash
kubectl apply -f k8s/monitoring/
```

## 💻 Development Workflow

### Local Development

1. Clone the repository:
```bash
git clone https://github.com/yourusername/eu-ai-act-compliance.git
cd eu-ai-act-compliance
```

2. Install development dependencies:
```bash
pip install -r requirements.txt
```

3. Run individual components locally:
```bash
cd src/api-gateway && python app.py
```

4. Build and push Docker images:
```bash
docker build -t yourusername/eu-ai-act-api-gateway:latest src/api-gateway/
docker push yourusername/eu-ai-act-api-gateway:latest
```

5. Run tests:
```bash
pytest src/tests/
```

### CI/CD Pipeline

This repository includes GitHub Actions workflows for:
- Automated testing on pull requests
- Code quality and linting checks
- Security scanning
- Image building and publishing
- Kubernetes manifest validation

## 📊 API Endpoints

### API Gateway Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| /health | GET | Service health status |
| /search | POST | Vector similarity search |
| /knowledge_graph | POST | Knowledge graph queries |
| /compliance_query | POST | Full compliance query workflow |
| /system_info | GET | System component information |

### Example Requests

#### Vector Search
```json
{
  "query": "What are the requirements for high-risk AI systems?",
  "limit": 5,
  "threshold": 0.75
}
```

#### Compliance Query
```json
{
  "system_description": "An AI system for automated resume screening and candidate ranking",
  "application_domain": "employment",
  "capabilities": ["candidate_ranking", "automated_decision"],
  "data_sources": ["resumes", "job_descriptions"]
}
```

## 🧩 Component Details

### Knowledge Graph Service

The Knowledge Graph maintains structured relationships between:
- AI System classifications and risk categories
- Regulatory requirements and obligations
- Conformity assessment procedures
- Documentation requirements
- Organizational responsibilities

### Vector Database Service

Qdrant provides:
- High-performance vector similarity search
- Persistent storage of embeddings
- Filtering capabilities based on metadata
- Configurable search parameters

### Embedding Service

The embedding service:
- Uses SentenceTransformers for high-quality embeddings
- Implements batched processing for efficiency
- Automatically downloads and caches models
- Provides consistent vector representations

### LLM Service

Multi-provider LLM service that:
- Supports OpenAI, Anthropic, and local Ollama models
- Implements automatic fallback between providers
- Ensures factual grounding of all responses
- Optimizes for minimal token usage

### API Gateway

The orchestration layer that:
- Manages component communication
- Implements the Retrieval-Augmented Generation (RAG) workflow
- Provides unified API access
- Handles error cases and graceful degradation

## 🔧 Customization

### Adding New Document Types

1. Update the schema in `src/schema/definitions.py`
2. Add document extraction logic in `src/data_import/import.py`
3. Reinitialize the vector database

### Custom LLM Providers

To add a new LLM provider:
1. Create a new provider class in `src/llm/providers.py` extending the `LLMProvider` base class
2. Register the provider in the providers dictionary
3. Update the `select_provider` function

### Adding New API Endpoints

1. Define new route and handler in `src/api-gateway/app.py`
2. Implement required orchestration logic
3. Add validation and error handling

## 📚 Troubleshooting

### Common Issues

1. Pod Crash Looping: Check resource limits and logs
```bash
kubectl logs -n eu-ai-act -l app=api-gateway
kubectl describe pod -n eu-ai-act -l app=api-gateway
```

2. Service Connectivity: Verify service discovery
```bash
kubectl exec -it -n eu-ai-act deploy/api-gateway -- curl embedding-service:8000/health
```

3. API Errors: Check API Gateway logs
```bash
kubectl logs -n eu-ai-act -l app=api-gateway -f
```

### Health Checks

All components provide `/health` endpoints that indicate:
- Service availability
- Component dependencies
- Resource utilization

## 📈 Monitoring

The system includes Prometheus exporters for metrics and Grafana dashboards for visualization. Key metrics include:
- Request latency and throughput
- Token usage and costs
- Cache hit/miss rates
- Error rates and types

## 🔒 Security

The system implements several security best practices:
- All sensitive configurations stored in Kubernetes Secrets
- API keys managed through environment variables
- Network policies for service isolation
- Container security best practices (non-root users, read-only filesystems)

## 🤝 Contributing

Contributions are welcome! Please see our Contributing Guide for details.

1. Fork the repository
2. Create a feature branch
3. Submit a pull request with comprehensive test coverage

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- EU AI Act regulatory documentation and guidelines
- The open-source communities behind TerminusDB, Qdrant, and SentenceTransformers
- All contributors to this project

## 📞 Support

For commercial support, customization, or enterprise deployments, please contact:
support@eu-ai-act-compliance.com

*Disclaimer: This system provides tools for understanding EU AI Act compliance requirements but does not constitute legal advice. Organizations should consult with legal experts for definitive compliance guidance.*