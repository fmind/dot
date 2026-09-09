# Google Cloud Managed MCP

Google Cloud exposes managed MCP endpoints for supported products. Follow the product's current setup guide; the [current enablement workflow](https://docs.cloud.google.com/mcp/enable-disable-mcp-servers) enables its product API rather than requiring a separate generic beta MCP enable step.

1. **Select the identity and project** per [gcloud](../../gcloud/SKILL.md), then enable the documented product API within the authorized scope:
   ```bash
   gcloud services enable <service>.googleapis.com --project=<project-id>
   ```
1. **Authenticate** with a method supported by both the product and host. Reuse the intended user, workload, or agent identity; follow [authentication guidance](https://docs.cloud.google.com/mcp/authenticate-mcp) instead of assuming every host can consume local ADC.
1. **Configure** the documented product endpoint and required quota-project headers with the host's native add command.
1. **Grant minimum IAM**: use only the MCP and product roles required by the selected endpoint and operations, then verify discovery and one authorized tool call.

Use the current [supported products](https://docs.cloud.google.com/mcp/supported-products), [MCP overview](https://docs.cloud.google.com/mcp), and [MCP registry](https://registry.modelcontextprotocol.io) instead of a local server catalog.
