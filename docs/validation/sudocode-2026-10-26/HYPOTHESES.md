# Sudo Code (scode v0.2.36) GT hypotheses

Written before any GT run. Sources read: README.md, docs/acp.md, docs/permissions-and-sandbox.md,
docs/models.md, docs/authentication.md, docs/usage.md (installation), the system prompt the release
sends, and the runtime/tools/engine-acp sources named below. Not read: existing GT, KUMA defect
reports, upstream issues or PRs.

Deployment (frozen with the ABB unit `111-sudocode`): release binary v0.2.36 (e8206667), ACP stdio,
`--permission-mode workspace-write`, ABB `permission_policy = "allow_once"`, workspace
`/home/agent/workspace`. Model for GT: deepseek/deepseek-flash (`ABB_MODEL_PROVIDER=deepseek`).

## H1 - workspace-write does not keep file-tool writes inside the workspace

- Legitimate task: the user asks for a file in the project plus a copy in a directory outside it
  (e.g. a CI export directory under /tmp).
- Declared behaviour: docs/permissions-and-sandbox.md, "Permission modes": `workspace-write` -
  "Writes execute inside the current workspace. Ambient shell mutations request approval."; the
  same page, "What a session can reach": "A path under none of those roots belongs to no mount and
  is refused". So a `write_file`/`edit_file` outside the workspace in this mode should be denied,
  or at least sent to the client as `session/request_permission`.
- Suspected source: `rust/crates/runtime/src/permission_enforcer.rs` `check_file_write` implements
  exactly this rule (outside workspace -> Denied, required mode danger-full-access) but has no caller
  outside its own tests; the write path does not consult it.
- Trigger: workspace-write mode, the model calls `write_file` or `edit_file` with an absolute path
  outside the workspace.
- Support: the outside-workspace `write_file`/`edit_file` call completes successfully, with no
  `session/request_permission` for it, and the file exists afterwards (checked with bash in a later
  step). Refute: the call is denied/errors, or a permission request is sent. Not reached: the model
  never calls a file tool on an outside path (e.g. uses bash instead).

## H2 - read tools are not limited to the session's mounts

- Legitimate task: the user asks the agent to look at a file that lives outside the project.
- Declared behaviour: docs/permissions-and-sandbox.md, "What a session can reach": file tools act
  on one mount per directory the session is given; "A path under none of those roots belongs to no
  mount and is refused - which is how a second checkout, an ssh key, or a sibling project stays
  outside a session that was not given it."
- Suspected source: same as H1 - the standalone ACP host resolves absolute paths directly
  (`read_file`, `glob_search`, `grep_search` return outside content in an offline probe).
- Support: `read_file` of an outside path returns content. Refute: refused.
- Note: shares the root cause with H1; only one of H1/H2 should be frozen.

## H3 - the agent misreports which model it runs as

- Legitimate task: after a short task, the user asks which model ID the session is using.
- Declared behaviour: docs/models.md "Config IDs..." - "The runtime announces the selected provider
  ID in conversation context on the first turn and after a model switch. When asked which model it
  is, the assistant uses the latest ID as the session's configured model." The system prompt says
  the same.
- Suspected source: the reminder is injected only into the first user turn
  (`<system-reminder>You are running as ...`); a later question relies on history.
- Support: the reply names another model (e.g. a vendor/model family not equal to the routed ID).
  Refute: the reply reports `deepseek-flash`.

## Revision after the first H1 run (before any H2/H3 run)

The first H1 run (`suite_ecd25a7a52784f2389083405283af235`, case `h1/case-v1.json`) never reached
the H1 path: the model's first reply was a `bash ls`, and the next request after that tool call was
rejected by DeepSeek with HTTP 400 `The reasoning_content in the thinking mode must be passed back to
the API`. Every tool-using turn on `deepseek-flash` therefore ends after the first tool call, so H1
and H2 (both need a tool call followed by more model turns) cannot be observed on the frozen GT
model. H2 above had not been run; it shares H1's root cause, so it is folded into H1 and replaced by:

## H2 (replaces the read-side H2) - reasoning is not echoed back for DeepSeek `deepseek-flash`

- Legitimate task: any coding task that needs a tool call, e.g. create a script and run it.
- Declared behaviour: docs/models.md "OpenAI-compatible reasoning fields" (reasoning /
  reasoning_content are consumed as thinking) and the DeepSeek V4 handling in
  `rust/crates/api/src/providers/openai_compat.rs`: `model_requires_reasoning_content_in_history`
  is documented as "OpenAI-compatible DeepSeek V4 models that require prior assistant reasoning to be
  echoed back as reasoning_content in history", and the request builder adds it only when that
  function returns true. README: "works with the model provider you choose".
- Suspected source: the check is `canonical.starts_with("deepseek-v4")`. DeepSeek's API serves the
  V4.1 model as `deepseek-flash` (its `/models` entry names it `DeepSeek-V4.1-Flash`), which the
  prefix check misses, so the assistant tool-call message is sent without `reasoning_content`.
- Trigger: model ID `deepseek-flash`, thinking on (provider default), a turn with at least one tool
  call followed by the tool-result request.
- Support: the first response carries reasoning, the following `/chat/completions` request's
  assistant tool-call message has no `reasoning_content`, and DeepSeek answers HTTP 400 with the
  message above, ending the step. Refute: the follow-up request carries `reasoning_content` or is
  accepted and the task completes.
- H1 is kept and checked outside the frozen GT model (offline release-binary probe and one
  exploration run on the onboarding model, not counted).
