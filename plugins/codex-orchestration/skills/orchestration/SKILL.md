---
name: orchestration
description: "Explain, diagnose, configure, or maintain the Codex Orchestration plugin. Normal chat activation uses the plain commands Turn Orchestration on, Use Orchestration, or Use Orchestration for this chat and is handled by the plugin's prompt hook without loading this skill. Invoke this skill explicitly only for help or maintenance."
---

# Codex Orchestration

Normal routing does not run from this skill. The bundled `UserPromptSubmit` hook owns
chat-local ON/OFF state and injects the fast dispatch contract before each active user
prompt. Use plain `Turn Orchestration on` for the lowest-latency path.

When explicitly invoked, acknowledge `Orchestration: ON for this chat`; the prompt hook
has already persisted the state. Do not load references or run maintenance unless the
user is diagnosing or changing the plugin.

For maintenance only:

- Read `references/role-contracts.md` when changing routing or agent templates.
- Read `references/usage-receipt.md` when changing receipts or telemetry.
- Resolve scripts relative to the directory containing this file.
- Accepted releases finish on `jessejaffe/codex-orchestration` main and never push to
  `DannyMac180/sol-advisor`.
