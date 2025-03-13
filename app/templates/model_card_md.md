# EU AI Act Model Card

**Generated:** {{ generated_at.strftime('%Y-%m-%d %H:%M') }}  
**Document Version:** {{ version }}

## 1. Model Details

{% if data.model_details %}
- **Name:** {{ data.model_details.name }}
- **Version:** {{ data.model_details.version }}
- **Description:** {{ data.model_details.description }}
{% if data.model_details.framework %}
- **Framework:** {{ data.model_details.framework }}
{% endif %}
{% if data.model_details.license %}
- **License:** {{ data.model_details.license }}
{% endif %}
{% else %}
*No model details provided.*
{% endif %}

## 2. Intended Use

{% if data.intended_use %}
- **Primary Purpose:** {{ data.intended_use.primary_purpose }}

{% if data.intended_use.intended_users %}
**Intended Users:**
{% for user in data.intended_use.intended_users %}
- {{ user }}
{% endfor %}
{% endif %}

{% if data.intended_use.use_cases %}
**Use Cases:**
{% for case in data.intended_use.use_cases %}
- {{ case }}
{% endfor %}
{% endif %}

{% if data.intended_use.out_of_scope_uses %}
**Out-of-Scope Uses:**
{% for out_of_scope in data.intended_use.out_of_scope_uses %}
- {{ out_of_scope }}
{% endfor %}
{% endif %}
{% else %}
*No intended use information provided.*
{% endif %}

## 3. Risk Assessment

{% if data.risk_assessment %}
| Risk Category | Description | Mitigation Strategy |
|---------------|-------------|---------------------|
{% for risk in data.risk_assessment.risks %}
| {{ risk.category }} | {{ risk.description }} | {{ risk.mitigation }} |
{% endfor %}

{% if data.risk_assessment.residual_risks %}
**Residual Risks:**

{{ data.risk_assessment.residual_risks }}
{% endif %}
{% else %}
*No risk assessment information provided.*
{% endif %}

## 4. Performance Metrics

{% if data.performance_metrics %}
| Metric Name | Value | Dataset/Context |
|-------------|-------|----------------|
{% for metric in data.performance_metrics.metrics %}
| {{ metric.name }} | {{ metric.value }} | {{ metric.context }} |
{% endfor %}

{% if data.performance_metrics.evaluation_datasets %}
**Evaluation Datasets:**

{% for dataset in data.performance_metrics.evaluation_datasets %}
- **{{ dataset.name }}**: {{ dataset.description }}
{% if dataset.link %}
  Link: {{ dataset.link }}
{% endif %}
{% endfor %}
{% endif %}
{% else %}
*No performance metrics provided.*
{% endif %}

## 5. Training Data

{% if data.training_data %}
- **Dataset Name:** {{ data.training_data.dataset_name }}
- **Description:** {{ data.training_data.description }}
{% if data.training_data.source %}
- **Source:** {{ data.training_data.source }}
{% endif %}
{% if data.training_data.preprocessing %}
- **Preprocessing:** {{ data.training_data.preprocessing }}
{% endif %}

{% if data.training_data.data_splits %}
**Data Splits:**

| Split | Size | Purpose |
|-------|------|---------|
{% for split in data.training_data.data_splits %}
| {{ split.name }} | {{ split.size }} | {{ split.purpose }} |
{% endfor %}
{% endif %}
{% else %}
*No training data information provided.*
{% endif %}

## 6. Technical Specifications

{% if data.technical_specifications %}
{% if data.technical_specifications.model_architecture %}
- **Model Architecture:** {{ data.technical_specifications.model_architecture }}
{% endif %}
{% if data.technical_specifications.parameters %}
- **Parameters:** {{ data.technical_specifications.parameters }}
{% endif %}
{% if data.technical_specifications.input_format %}
- **Input Format:** {{ data.technical_specifications.input_format }}
{% endif %}
{% if data.technical_specifications.output_format %}
- **Output Format:** {{ data.technical_specifications.output_format }}
{% endif %}

{% if data.technical_specifications.dependencies %}
**Dependencies:**
{% for dependency in data.technical_specifications.dependencies %}
- {{ dependency }}
{% endfor %}
{% endif %}
{% else %}
*No technical specifications provided.*
{% endif %}

## 7. Human Oversight

{% if data.human_oversight %}
{% if data.human_oversight.measures %}
**Oversight Measures:**
{% for measure in data.human_oversight.measures %}
- {{ measure }}
{% endfor %}
{% endif %}

{% if data.human_oversight.human_in_loop_points %}
**Human-in-the-Loop Points:** {{ data.human_oversight.human_in_loop_points }}
{% endif %}

{% if data.human_oversight.monitoring %}
**Monitoring Procedures:** {{ data.human_oversight.monitoring }}
{% endif %}
{% else %}
*No human oversight information provided.*
{% endif %}

## 8. Compliance Information

{% if data.compliance_information %}
{% if data.compliance_information.eu_ai_act_classification %}
**EU AI Act Classification:** {{ data.compliance_information.eu_ai_act_classification }}
{% endif %}

{% if data.compliance_information.standards %}
**Applicable Standards:**
{% for standard in data.compliance_information.standards %}
- **{{ standard.name }}**: {{ standard.description }}
{% endfor %}
{% endif %}

{% if data.compliance_information.impact_assessments %}
**Impact Assessments:**

| Type | Date | Summary |
|------|------|---------|
{% for assessment in data.compliance_information.impact_assessments %}
| {{ assessment.type }} | {{ assessment.date }} | {{ assessment.summary }} |
{% endfor %}
{% endif %}
{% else %}
*No compliance information provided.*
{% endif %}

## 9. Contact Information

{% if data.contact_information %}
{% if data.contact_information.developer %}
- **Developer:** {{ data.contact_information.developer }}
{% endif %}
{% if data.contact_information.contact_email %}
- **Contact Email:** {{ data.contact_information.contact_email }}
{% endif %}
{% if data.contact_information.website %}
- **Website:** {{ data.contact_information.website }}
{% endif %}
{% else %}
*No contact information provided.*
{% endif %}

---

*Generated using AI Compliance Documentation Generator*  
*Generated on {{ generated_at.strftime('%Y-%m-%d %H:%M') }}* 