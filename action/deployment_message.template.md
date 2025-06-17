# Deployment Results {{ ":white_check_mark:" if status == "success" else ":x:" }}

{% if status == "success" %}
**{{ actor }}** successfully {{ "noop " if noop else "" }}deployed branch `{{ ref }}` to **{{ environment }}**
{% elif status == "failure" %}
**{{ actor }}**, your {{ "noop " if noop else "" }}deployment of branch `{{ ref }}` failed to deploy to **{{ environment }}**
{% else %}
**{{ actor }}**, your {{ "noop " if noop else "" }}deployment of branch `{{ ref }}` is in an unknown state for **{{ environment }}**.
{% endif %}

---

<details>
<summary>Show Results</summary>

{% if results %}
```
{{ results }}
```
{% else %}
_No results to display._
{% endif %}

{% if artifact_url %}
---
:warning: Output truncated. [Download full output here]({{ artifact_url }})
{% endif %}

</details>

---

| **Key**      | **Value**   |
|--------------|-------------|
| Status       | {{ status }} |
| Env          | {{ environment }} |
| Branch       | {{ ref }}    |
| Commit       | {{ sha }}    |
| Actor        | {{ actor }}  |
| Noop         | {{ noop }}   |
| Duration     | {{ total_seconds }} seconds |
| Logs         | [View Logs]({{ logs }}) |
