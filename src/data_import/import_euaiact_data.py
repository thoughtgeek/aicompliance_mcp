#!/usr/bin/env python3
"""
EU AI Act Knowledge Graph Data Import Script
This script imports structured EU AI Act data into TerminusDB.
"""

import json
import os
import sys
import terminusdb_client
from terminusdb_client import WOQLClient

# Configuration
TERMINUSDB_URL = os.environ.get("TERMINUSDB_URL", "http://localhost:6363")
TERMINUSDB_USER = os.environ.get("TERMINUSDB_USER", "admin")
TERMINUSDB_PASSWORD = os.environ.get("TERMINUSDB_PASSWORD", "root")
DB_NAME = "eu_ai_act"
SCHEMA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "schema", "terminusdb_schema.json")

# Sample EU AI Act data
SAMPLE_DATA = {
    "risk_categories": [
        {
            "id": "unacceptable",
            "name": "unacceptable",
            "description": "AI systems that pose unacceptable risks to the safety, livelihoods, and rights of people",
            "legalBasis": "Article 5 of EU AI Act",
            "citations": ["citation_article5"]
        },
        {
            "id": "high",
            "name": "high",
            "description": "AI systems with high risk of harm to health, safety or fundamental rights",
            "legalBasis": "Article 6 of EU AI Act",
            "citations": ["citation_article6"]
        },
        {
            "id": "limited",
            "name": "limited",
            "description": "AI systems with limited risk that require specific transparency obligations",
            "legalBasis": "Article 52 of EU AI Act",
            "citations": ["citation_article52"]
        },
        {
            "id": "minimal",
            "name": "minimal",
            "description": "AI systems with minimal risk that can be developed and used without additional obligations",
            "legalBasis": "Not explicitly covered in EU AI Act",
            "citations": []
        }
    ],
    "legal_citations": [
        {
            "id": "citation_article5",
            "article": "5",
            "paragraph": "1",
            "text": "The following artificial intelligence practices shall be prohibited: (a) the placing on the market, putting into service or use of an AI system that deploys subliminal techniques...",
            "sourceUrl": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A52021PC0206"
        },
        {
            "id": "citation_article6",
            "article": "6",
            "paragraph": "1",
            "text": "An AI system that is itself a safety component of a product or is itself a product covered by the Union harmonisation legislation listed in Annex II shall be considered as high-risk.",
            "sourceUrl": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A52021PC0206"
        },
        {
            "id": "citation_article52",
            "article": "52",
            "paragraph": "1",
            "text": "Providers shall ensure that AI systems intended to interact with natural persons are designed and developed in such a way that natural persons are informed that they are interacting with an AI system...",
            "sourceUrl": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A52021PC0206"
        }
    ],
    "requirements": [
        {
            "id": "req_risk_management",
            "title": "Risk Management System",
            "description": "AI systems classified as high-risk must implement a risk management system to identify and analyze known and foreseeable risks.",
            "category": "Risk Management",
            "appliesTo": ["high"],
            "citations": ["citation_article9"],
            "documentation": ["doc_risk_assessment"]
        },
        {
            "id": "req_data_governance",
            "title": "Data Governance",
            "description": "High-risk AI systems must be developed with training, validation and testing data that meets quality criteria.",
            "category": "Data Management",
            "appliesTo": ["high"],
            "citations": ["citation_article10"],
            "documentation": ["doc_data_governance"]
        }
    ],
    "obligations": [
        {
            "id": "obl_transparency",
            "title": "Transparency Obligation",
            "description": "Providers must ensure users are aware when they are interacting with an AI system.",
            "obligatedParty": ["provider"],
            "appliesTo": ["limited"],
            "citations": ["citation_article52"],
            "evidenceRequired": ["evidence_disclosure"]
        },
        {
            "id": "obl_conformity",
            "title": "Conformity Assessment",
            "description": "Providers of high-risk AI systems must conduct conformity assessments before placing on market.",
            "obligatedParty": ["provider"],
            "appliesTo": ["high"],
            "citations": ["citation_article43"],
            "evidenceRequired": ["evidence_assessment_report"]
        }
    ],
    "organizations": [
        {
            "id": "org_provider",
            "name": "AI System Provider",
            "role": "provider",
            "description": "Any natural or legal person, public authority, agency or other body that develops an AI system or has an AI system developed with a view to placing it on the market or putting it into service under its own name or trademark, whether for payment or free of charge.",
            "obligations": ["obl_transparency", "obl_conformity"]
        },
        {
            "id": "org_deployer",
            "name": "AI System Deployer",
            "role": "deployer",
            "description": "Any natural or legal person, public authority, agency or other body using an AI system under its authority, except where used in personal, non-professional activity.",
            "obligations": []
        }
    ],
    "evidence": [
        {
            "id": "evidence_disclosure",
            "title": "Disclosure Notice",
            "description": "Documentation showing how users are notified they are interacting with an AI system.",
            "evidenceType": "Documentation",
            "verificationMethod": "Manual review",
            "citations": ["citation_article52"]
        },
        {
            "id": "evidence_assessment_report",
            "title": "Conformity Assessment Report",
            "description": "Report documenting the conformity assessment process and results.",
            "evidenceType": "Report",
            "verificationMethod": "Review by notified body",
            "citations": ["citation_article43"]
        }
    ],
    "documentation": [
        {
            "id": "doc_risk_assessment",
            "title": "Risk Assessment Documentation",
            "description": "Documentation of the risk management process including risk identification, analysis, and mitigation.",
            "documentType": "Technical Documentation",
            "requiredContent": "Risk evaluation methodology, identified risks, mitigation measures, validation results",
            "citations": ["citation_article9"]
        },
        {
            "id": "doc_data_governance",
            "title": "Data Governance Documentation",
            "description": "Documentation of data governance practices for training, validation, and testing datasets.",
            "documentType": "Technical Documentation",
            "requiredContent": "Data sources, processing methods, data validation procedures, bias detection and correction methodologies",
            "citations": ["citation_article10"]
        }
    ],
    "faqs": [
        {
            "id": "faq_highrisk",
            "question": "How do I determine if my AI system is high-risk under the EU AI Act?",
            "answer": "High-risk AI systems are either: 1) AI systems used as safety components of products subject to third-party assessment or 2) AI systems in areas listed in Annex III, such as biometric identification, critical infrastructure, education, employment, essential services, law enforcement, migration, and justice.",
            "category": "Classification",
            "citations": ["citation_article6"],
            "relatedRequirements": []
        },
        {
            "id": "faq_prohibited",
            "question": "What AI practices are prohibited under the EU AI Act?",
            "answer": "Prohibited practices include: subliminal manipulation causing harm, exploitation of vulnerabilities of specific groups, social scoring by public authorities, and certain uses of real-time remote biometric identification in publicly accessible spaces for law enforcement.",
            "category": "Prohibitions",
            "citations": ["citation_article5"],
            "relatedRequirements": []
        }
    ],
    "conformity_assessments": [
        {
            "id": "assessment_self",
            "title": "Self-assessment Procedure",
            "description": "Internal control procedure where the provider verifies compliance with requirements.",
            "assessmentType": "Internal Control",
            "appliesTo": ["high"],
            "citations": ["citation_article43"],
            "requiredDocumentation": ["doc_risk_assessment", "doc_data_governance"]
        },
        {
            "id": "assessment_thirdparty",
            "title": "Third-party Assessment",
            "description": "Assessment conducted by a notified body to verify compliance.",
            "assessmentType": "External Assessment",
            "appliesTo": ["high"],
            "citations": ["citation_article43"],
            "requiredDocumentation": ["doc_risk_assessment", "doc_data_governance"]
        }
    ],
    "ai_systems": [
        {
            "id": "ai_biometric",
            "name": "Remote Biometric Identification System",
            "description": "AI system for identifying natural persons at a distance through biometric data.",
            "riskCategory": "high",
            "requirements": ["req_risk_management", "req_data_governance"],
            "obligations": ["obl_conformity"],
            "assessments": ["assessment_thirdparty"]
        },
        {
            "id": "ai_chatbot",
            "name": "Customer Service Chatbot",
            "description": "AI system designed to interact with customers and provide assistance.",
            "riskCategory": "limited",
            "requirements": [],
            "obligations": ["obl_transparency"],
            "assessments": []
        }
    ]
}

def main():
    """Main function to import EU AI Act data into TerminusDB."""
    print("Starting EU AI Act data import...")
    
    # Connect to TerminusDB
    try:
        client = WOQLClient(TERMINUSDB_URL)
        client.connect(user=TERMINUSDB_USER, key=TERMINUSDB_PASSWORD)
        print(f"Connected to TerminusDB at {TERMINUSDB_URL}")
    except Exception as e:
        print(f"Failed to connect to TerminusDB: {e}")
        sys.exit(1)
    
    # Create database if it doesn't exist
    try:
        if not client.db_exists(DB_NAME):
            client.create_database(DB_NAME, "EU AI Act Regulatory Knowledge Graph")
            print(f"Created database '{DB_NAME}'")
        
        client.db(DB_NAME)
        print(f"Connected to database '{DB_NAME}'")
    except Exception as e:
        print(f"Failed to create/connect to database: {e}")
        sys.exit(1)
    
    # Import schema
    try:
        with open(SCHEMA_FILE, 'r') as f:
            schema = json.load(f)
        
        client.insert_document(schema, graph_type="schema")
        print("Imported schema successfully")
    except Exception as e:
        print(f"Failed to import schema: {e}")
        sys.exit(1)
    
    # Import data
    try:
        # Import legal citations first as they are referenced by other entities
        for citation in SAMPLE_DATA["legal_citations"]:
            client.insert_document({
                "@type": "LegalCitation",
                "@id": citation["id"],
                "id": citation["id"],
                "article": citation["article"],
                "paragraph": citation["paragraph"],
                "text": citation["text"],
                "sourceUrl": citation["sourceUrl"]
            })
        print(f"Imported {len(SAMPLE_DATA['legal_citations'])} legal citations")
        
        # Import risk categories
        for category in SAMPLE_DATA["risk_categories"]:
            citation_refs = [{"@id": cid, "@type": "LegalCitation"} for cid in category["citations"]]
            client.insert_document({
                "@type": "RiskCategory",
                "@id": category["id"],
                "id": category["id"],
                "name": category["name"],
                "description": category["description"],
                "legalBasis": category["legalBasis"],
                "citations": citation_refs
            })
        print(f"Imported {len(SAMPLE_DATA['risk_categories'])} risk categories")
        
        # Import documentation types
        for doc in SAMPLE_DATA["documentation"]:
            citation_refs = [{"@id": cid, "@type": "LegalCitation"} for cid in doc["citations"]]
            client.insert_document({
                "@type": "Documentation",
                "@id": doc["id"],
                "id": doc["id"],
                "title": doc["title"],
                "description": doc["description"],
                "documentType": doc["documentType"],
                "requiredContent": doc["requiredContent"],
                "citations": citation_refs
            })
        print(f"Imported {len(SAMPLE_DATA['documentation'])} documentation types")
        
        # Import evidence types
        for evidence in SAMPLE_DATA["evidence"]:
            citation_refs = [{"@id": cid, "@type": "LegalCitation"} for cid in evidence["citations"]]
            client.insert_document({
                "@type": "Evidence",
                "@id": evidence["id"],
                "id": evidence["id"],
                "title": evidence["title"],
                "description": evidence["description"],
                "evidenceType": evidence["evidenceType"],
                "verificationMethod": evidence["verificationMethod"],
                "citations": citation_refs
            })
        print(f"Imported {len(SAMPLE_DATA['evidence'])} evidence types")
        
        # Import requirements
        for req in SAMPLE_DATA["requirements"]:
            applies_to_refs = [{"@id": cat, "@type": "RiskCategory"} for cat in req["appliesTo"]]
            citation_refs = [{"@id": cid, "@type": "LegalCitation"} for cid in req["citations"]]
            doc_refs = [{"@id": doc, "@type": "Documentation"} for doc in req["documentation"]]
            
            client.insert_document({
                "@type": "Requirement",
                "@id": req["id"],
                "id": req["id"],
                "title": req["title"],
                "description": req["description"],
                "category": req["category"],
                "appliesTo": applies_to_refs,
                "citations": citation_refs,
                "documentation": doc_refs
            })
        print(f"Imported {len(SAMPLE_DATA['requirements'])} requirements")
        
        # Import organizations (without obligations for now)
        for org in SAMPLE_DATA["organizations"]:
            client.insert_document({
                "@type": "Organization",
                "@id": org["id"],
                "id": org["id"],
                "name": org["name"],
                "role": org["role"],
                "description": org["description"],
                "obligations": []
            })
        print(f"Imported {len(SAMPLE_DATA['organizations'])} organizations (without obligations)")
        
        # Import obligations
        for obl in SAMPLE_DATA["obligations"]:
            applies_to_refs = [{"@id": cat, "@type": "RiskCategory"} for cat in obl["appliesTo"]]
            citation_refs = [{"@id": cid, "@type": "LegalCitation"} for cid in obl["citations"]]
            evidence_refs = [{"@id": ev, "@type": "Evidence"} for ev in obl["evidenceRequired"]]
            obligated_party_refs = [{"@id": party, "@type": "Organization"} for party in obl["obligatedParty"]]
            
            client.insert_document({
                "@type": "Obligation",
                "@id": obl["id"],
                "id": obl["id"],
                "title": obl["title"],
                "description": obl["description"],
                "obligatedParty": obligated_party_refs,
                "appliesTo": applies_to_refs,
                "citations": citation_refs,
                "evidenceRequired": evidence_refs
            })
        print(f"Imported {len(SAMPLE_DATA['obligations'])} obligations")
        
        # Update organizations with obligations
        for org in SAMPLE_DATA["organizations"]:
            obligation_refs = [{"@id": obl, "@type": "Obligation"} for obl in org["obligations"]]
            client.update_document({
                "@type": "Organization",
                "@id": org["id"],
                "obligations": obligation_refs
            })
        print(f"Updated {len(SAMPLE_DATA['organizations'])} organizations with obligations")
        
        # Import conformity assessments
        for assessment in SAMPLE_DATA["conformity_assessments"]:
            applies_to_refs = [{"@id": cat, "@type": "RiskCategory"} for cat in assessment["appliesTo"]]
            citation_refs = [{"@id": cid, "@type": "LegalCitation"} for cid in assessment["citations"]]
            doc_refs = [{"@id": doc, "@type": "Documentation"} for doc in assessment["requiredDocumentation"]]
            
            client.insert_document({
                "@type": "ConformityAssessment",
                "@id": assessment["id"],
                "id": assessment["id"],
                "title": assessment["title"],
                "description": assessment["description"],
                "assessmentType": assessment["assessmentType"],
                "appliesTo": applies_to_refs,
                "citations": citation_refs,
                "requiredDocumentation": doc_refs
            })
        print(f"Imported {len(SAMPLE_DATA['conformity_assessments'])} conformity assessments")
        
        # Import FAQs
        for faq in SAMPLE_DATA["faqs"]:
            citation_refs = [{"@id": cid, "@type": "LegalCitation"} for cid in faq["citations"]]
            req_refs = [{"@id": req, "@type": "Requirement"} for req in faq["relatedRequirements"]]
            
            client.insert_document({
                "@type": "FAQ",
                "@id": faq["id"],
                "id": faq["id"],
                "question": faq["question"],
                "answer": faq["answer"],
                "category": faq["category"],
                "citations": citation_refs,
                "relatedRequirements": req_refs
            })
        print(f"Imported {len(SAMPLE_DATA['faqs'])} FAQs")
        
        # Import AI systems
        for system in SAMPLE_DATA["ai_systems"]:
            req_refs = [{"@id": req, "@type": "Requirement"} for req in system["requirements"]]
            obl_refs = [{"@id": obl, "@type": "Obligation"} for obl in system["obligations"]]
            assessment_refs = [{"@id": ass, "@type": "ConformityAssessment"} for ass in system["assessments"]]
            
            client.insert_document({
                "@type": "AISystem",
                "@id": system["id"],
                "id": system["id"],
                "name": system["name"],
                "description": system["description"],
                "riskCategory": {"@id": system["riskCategory"], "@type": "RiskCategory"} if system["riskCategory"] else None,
                "requirements": req_refs,
                "obligations": obl_refs,
                "assessments": assessment_refs
            })
        print(f"Imported {len(SAMPLE_DATA['ai_systems'])} AI systems")
        
        print("\nData import completed successfully!")
        
    except Exception as e:
        print(f"Failed to import data: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 