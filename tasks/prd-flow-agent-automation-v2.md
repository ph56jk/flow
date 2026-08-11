[PRD]
# PRD: Flow Agent Automation V2

## Overview
Flow v2 needs to become an automation app where the local assistant only operates tools and workflow steps, while Google Flow's own Agent writes the final image prompts and starts generation. The production path is: choose the correct Trello card image, send the product/request context to Flow Agent, generate 4 images by default, auto-approve Flow Agent's internal confirmation, send results to Telegram for human review, then archive approved images back to the same Trello card.

## Goals
- Make Google Flow Agent the default prompt author and generation operator.
- Remove Google Sheet prompt dependency from the main automation path.
- Keep the in-app AI focused on selecting cards, preparing context, running modules, and explaining next actions.
- Generate 4 images per run by default, with an editable count.
- Preserve Telegram human approval before writing final images back to Trello.
- Run thorough long tests and hidden browser verification so the user can keep working.

## Quality Gates
These commands must pass for every user story:
- `node --check flow_web/static/app.js`
- `./.venv/bin/python -m unittest tests.test_flow_web_smoke -q`
- `git diff --check`

For UI and automation stories, also include:
- Background browser verification against `http://127.0.0.1:8000/`.
- A real or safe smoke run proving selected Trello image context reaches Flow Agent and returns artifacts or a clear recoverable error.

## User Stories

### US-001: Default 4-Image Flow Agent Generation
**Description:** As an operator, I want every Flow Agent generation to create 4 images by default while still allowing edits, so that each product gets a usable batch without extra setup.

**Acceptance Criteria:**
- [ ] The Flow module defaults image count to 4 for Agent-based runs.
- [ ] The user can edit the count before running.
- [ ] Existing non-Agent create flows are not broken.
- [ ] The backend payload carries the chosen count into the Flow Agent execution path.

### US-002: Sheetless Primary Automation Path
**Description:** As an operator, I want the main automation path to work without Google Sheet prompts, so that Trello plus Flow Agent is enough to create product images.

**Acceptance Criteria:**
- [ ] The default Auto Trello run does not fail because no Google Sheet prompt matches.
- [ ] Google Sheet prompt library remains optional or secondary, not required for the primary path.
- [ ] UI copy makes clear that Flow Agent writes the prompt for the main path.
- [ ] Existing Sheet status does not block Trello image selection and Flow Agent execution.

### US-003: In-App AI as Tool Operator Only
**Description:** As an operator, I want the app AI to operate the workflow rather than write final prompts, so that prompt quality comes from Flow Agent and the local assistant stays predictable.

**Acceptance Criteria:**
- [ ] The assistant panel no longer presents its own final image prompt as the production prompt.
- [ ] Assistant actions can search Trello, choose a card/attachment, set module values, and start the automation.
- [ ] Assistant output explains what it will send to Flow Agent without pretending to generate the final prompt locally.
- [ ] Action buttons run immediately after selection when the user chooses a valid card/image.

### US-004: Flow Agent Interaction and Auto Approval
**Description:** As an operator, I want the app to talk to Google Flow Agent, attach the selected Trello reference, and approve Flow Agent's confirmation automatically, so that long generation runs do not stall.

**Acceptance Criteria:**
- [ ] The runner opens the configured Flow project and enables Agent mode when available.
- [ ] The runner sends product analysis instructions, selected Trello image context, and requested image count to Flow Agent.
- [ ] If Flow asks for generation approval, the app chooses "approve and do not ask again" when available, then approves.
- [ ] The runner detects results from `streamChat`, `batchGenerateImages`, or project image scanning.
- [ ] Timeouts produce a clear recoverable error instead of looping forever.

### US-005: Telegram Review and Same-Card Trello Archive
**Description:** As an operator, I want generated images reviewed in Telegram before archiving, so that only approved outputs return to the original Trello card.

**Acceptance Criteria:**
- [ ] Flow Agent approval is automatic, but final image approval in Telegram remains human-gated.
- [ ] Approved Telegram images upload back to the same source Trello card.
- [ ] Rejected or pending images are not archived to Trello.
- [ ] The history view shows source card, selected attachment, Flow artifacts, Telegram status, and archive result.

### US-006: Hidden Long-Run Verification
**Description:** As an operator, I want ralph-tui and browser verification to run in the background, so that the app can be tested thoroughly without taking over my screen.

**Acceptance Criteria:**
- [ ] Ralph/Codex verification can run with the browser headless or backgrounded.
- [ ] Long tests may run as needed until the feature is stable.
- [ ] The final report includes commands run, browser verification result, and remaining risks.
- [ ] No secrets, tokens, or private keys are pushed to GitHub.

## Functional Requirements
- FR-1: The system must default Flow Agent image generation count to 4.
- FR-2: The system must let the user edit the generation count.
- FR-3: The system must not require a Google Sheet prompt for the primary Auto Trello path.
- FR-4: The system must keep Sheet support optional for legacy/manual workflows.
- FR-5: The local AI assistant must act as workflow/tool operator, not final prompt author.
- FR-6: The Flow runner must use Google Flow Agent when the user enables the Agent path.
- FR-7: The Flow runner must auto-approve Flow Agent's generation confirmation.
- FR-8: The Flow runner must detect generated images through live network events and fallback project scanning.
- FR-9: Telegram final review must remain required before Trello archive.
- FR-10: Approved images must upload to the same source Trello card.
- FR-11: UI actions for selected Trello card/image must actually start the run.
- FR-12: Tests and browser verification must run in the background where possible.

## Non-Goals
- Do not bypass Google account, CAPTCHA, or security prompts.
- Do not auto-approve Telegram final review.
- Do not remove optional Google Sheet features entirely unless a later request asks for it.
- Do not expose Trello, Telegram, Google, or Flow credentials in code, logs, or Git history.
- Do not create a separate cloud service; keep this app local-first.

## Technical Considerations
- Likely files: `flow_web/static/app.js`, `flow_web/service.py`, `flow_web/schemas.py`, `tests/test_flow_web_smoke.py`.
- Reuse existing helpers such as Flow Agent mode switching, auto approval, project image scanning, Trello candidate rendering, and Telegram review queues.
- Background verification should prefer headless Playwright or the in-app browser without foreground interruption.
- The configured Flow project should point at `https://labs.google/fx/vi/tools/flow/project/PROJECT_ID`.

## Success Metrics
- From a valid Trello card image, the user can start an Agent-based run and receive 4 generated images.
- No Google Sheet prompt match is needed for that run.
- Flow Agent confirmation does not block the run.
- Telegram receives reviewable results.
- Approved results return to the same Trello card.
- All quality gates pass and Git remains clean of secrets.

## Open Questions
- Whether optional Sheet prompt workflows should be hidden by default or moved to an advanced mode.
- Whether production bulk mode should process one card at a time or multiple Ready-for-AI cards in a queue after this change lands.
[/PRD]
