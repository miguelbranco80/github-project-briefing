# Install Project Briefing

On a Gateway with working template Add:

~~~sh
gh repo clone miguelbranco80/project-briefing-template
cd project-briefing-template
openclaw templates add .
~~~

UI Add is also supported. Keep the new agent ID. Add creates an independent
agent and one daily job; adding again is not an upgrade. If a prior Add was
partial, inspect that agent and job instead of retrying blindly.

The installed 2026.11.5-beta.1 CLI previously required offline ownership but
then contacted the stopped Gateway to create the job. This package does not
fix that runtime defect. Use a working Add flow/version and inspect any partial
result; do not stop the Gateway merely to retry the same command.

Open the agent's chat and send Get started if CLI Add did not start onboarding.
The bundled skill owns repository setup and the daily journal workflow.
Python 3.10+, Node.js/npm, authenticated gh and portal access must be available
on the requesting agent's actual execution host, not just the developer's
machine. screen is optional for panel display. Image generation is not required.
Host policy still controls tool access.

## First-run check

Ask: Refresh now, build the journal without decorative artwork, show the article
and report collection, presentation and daily-delivery readiness.

Then ask for a second refresh. Only meaningful new developments should produce
another article. Earlier posts and any saved assets should remain. Inspect the installed
09:00 UTC job and its actual delivery; a manifest declaration is not proof.
Before setup, scheduled turns must remain quiet.

## Remove

Delete the agent through the UI or:

~~~sh
openclaw agents delete ACTUAL_AGENT_ID
~~~

Export wanted data first. Agent deletion removes its dedicated workspace
(configuration, evidence, journals, generated art and installed skill) and
assigned automations. Deleting a chat is not uninstalling. Source checkouts,
archives, shared credentials and already-delivered reports remain.
