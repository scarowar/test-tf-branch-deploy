Terrachops Deployment Results {{ ":white_check_mark:" if status == "success" else ":x:" }}
{% if status == "success" %}
{{ actor }} successfully {{ "noop " if noop else "" }}deployed branch {{ ref }} to {{ environment }}
{% endif %}

{% if status == "failure" %}
{{ actor }}, your {{ "noop " if noop else "" }}deployment of branch {{ ref }} failed to deploy to {{ environment }}
{% endif %}

{% if status == "unknown" %}
{{ actor }}, your {{ "noop " if noop else "" }}deployment of branch {{ ref }} is in an unknown state when trying to deploy to {{ environment }}.
{% endif %}

<details> <summary>Show Results</summary>

{{ results }}

{% if artifact_url %}
---
:warning: Output truncated. [Download full output here]({{ artifact_url }})
{% endif %}

</details>
Deployment Details

Status: {{ status }}
Environment: {{ environment }}
Branch: {{ ref }}
Commit: {{ sha }}
Actor: {{ actor }}
Noop: {{ noop }}
Duration: {{ total_seconds }} seconds
Logs: [View Logs]({{ logs }})
