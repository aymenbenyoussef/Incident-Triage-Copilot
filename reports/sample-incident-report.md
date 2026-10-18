# Sample Incident Investigation Report

This sample shows the report format produced by the agent and used by the PDF
exporter.

```text
INCIDENT SUMMARY: Checkout failures began shortly after a new API deployment.
SEVERITY: High
AFFECTED SERVICES: api, web
TIMELINE: v2.3.0 was deployed to api; checkout errors and latency increased afterward.
ROOT CAUSE: The api v2.3.0 deployment introduced a checkout regression.
CONFIDENCE: High
EVIDENCE:
- NullPointerException errors were recorded in the checkout handler.
- API latency increased from the healthy baseline after the deployment.
- The recent api deployment list includes v2.3.0.
CUSTOMER IMPACT: Customers may be unable to complete checkout.
RECOMMENDED ACTION: Request human approval to roll back api to the previous version.
FOLLOW-UP INVESTIGATION: Confirm checkout success rate and latency after rollback.
```

The generated PDF contains the same sections in a formatted document with the
investigation request, generation timestamp, and tool-call count.
