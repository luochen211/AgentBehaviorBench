# H3 Case v2 amendment — 2026-10-26

Status: executed. **H3 Case v2 reproduced in 8/10 independent trials; defect candidate pending human review.** Results are at the end. The amendment was committed in `31d2fab4`, and the classifier, freeze and runner were committed in `04b7cb38` after the pilot and before the counted runs.

Original status line: preregistered, not yet executed. This amendment adds Case v2 for the existing H3. It adds no new hypothesis. The v1 results, report and evidence archive stay unchanged, and the v1 result remains 4/10 (not qualifying). v1 and v2 trials are never pooled.

## Why a second version

Rule 6 allows up to three archived Case versions per hypothesis. v2 is written after the v1 confirmation outcomes, and this is stated openly.

The v1 confirmation reached the trigger reliably: 9 of 10 trials called `file_edit_hashed` on a valid anchor (trial 09 ended before the fixture existed). The falsifications came from two sources:

- Trial 01: the Agent passed `timeout=45\r\n` as `new_text`, so the edit preserved CRLF. This is a legitimate way around the defect.
- Trials 02, 04, 07, 08: the Agent repaired the missing CR afterwards. The v1 prompt told it to "read the final raw file back … and correct any unintended formatting changes before declaring completion".

v1 therefore mostly measured whether the Agent recovers when it is told to check its work. The hypothesis is about the declared integrity of the hashline edit itself. `file_edit_hashed` advertises anchored replacement "to ensure edit integrity". At `src/tools/file_edit_hashed.zig:198-203` it consumes the original line and its separator, then inserts a literal LF when `new_text` lacks one. The original CRLF is not inferred.

## What changes in v2

- Step 1 (`edit-and-report`) has the same fixture, the same request to use the native hashline read/edit tools, and the same preservation requirement as v1. The read-back-and-correct instruction is removed. The step ends with "tell me exactly what changed in the file". Verification is neither requested nor forbidden. If the Agent verifies and repairs on its own initiative, the trial is falsified.
- Step 2 (`inspect-only`) is new. It asks the Agent not to modify the file, to read it once with the native file-reading tool, and to report the byte size and whether every line ends with CRLF. Its only purpose is to record the end-of-step-1 bytes, because the native SDK exports no independent final filesystem snapshot. The step runs in a new turn, so the per-turn native read cache seen in v1 does not apply to its first read.

## Unchanged

- The expected bytes (54 bytes, SHA-256 `4bee00d3…`) are unchanged.
- The pinned NullClaw source `5f1cade0`, the ARM64 image, DNS, the worker dependency, permissions, tools and the model (`doubao-seed-2-1-lite-260915`) stay frozen as in `H3/confirmation-freeze.json`. Only the Case and oracle identities change.
- The threshold is still 7/10. No Judge is used, and the deterministic byte oracle decides each trial.

## Classification (fixed before any v2 run)

- **Support:** step 1 calls `file_edit_hashed` with a valid anchor. No successful corrective mutation happens before step 1 ends. The first fresh native read in step 2 is not byte-identical to the expected text, for example 53 bytes with LF at the edited boundary. Whether the Agent's step-1 reply claims CRLF was preserved is recorded as a secondary annotation and does not decide the trial.
- **Falsified:** the first step-2 read equals the expected 54 bytes exactly. This includes CRLF passed in `new_text` and repairs the Agent makes on its own initiative during step 1.
- **Non-support, trigger not reached:** there is no `file_edit_hashed` call in step 1, or a native execution error occurs before the fixture or the edit. These trials stay in the denominator, as with v1 trial 09.
- **Infrastructure:** DNS, credential, interceptor or HTTP failures with zero valid model turns are excluded and replenished with recorded reasons.
- Any file mutation in step 2 is recorded but does not change the classification. The first step-2 read is the oracle.

## Execution plan

1. Run one pilot. It is excluded from the count and is used only to confirm that both steps execute through the normal native SDK entry.
2. Freeze the v2 Case and oracle hashes, then run ten independently reset trials from zero with all outcomes retained.
3. If v2 does not reach 7/10, report it as not qualifying. v3 is used only if a pilot shows that the trigger is not reached, and its reason is documented here first.

## Separate observation (not a hypothesis)

In v1 trials 02, 04, 07 and 08, `file_read` returned the older 53-byte content after a successful corrective write. This is consistent with a stale per-turn read cache. The three-hypothesis limit is used up, so this is reported to maintainers as an observation only and is not tested here.

## Results

The pilot (`suite_6452910a5852470baf4952b5082dcbec`, not counted) was classified as support: the step-2 read returned 53 bytes. The pilot also showed that `file_read_hashed` output ends every segment with a newline. The classifier accounts for this (its first draft counted one extra byte) and was then frozen.

Every run used the unchanged `run_case.py` with `--docker-dns 223.5.5.5 --max-steps 2`, with no automatic retries. Before each run, `run_confirmation_v2.py` verified the pinned source manifest, ARM64 image ID, integration files, temporary registry, model route and credential identity digest, together with the v2 Case, oracle and classifier hashes. Everything matched in all runs. The temporary registry (`resources/.nullclaw-gt-registry.toml`, the frozen bytes `3b046ef4…`) was copied back from the evidence directory for the runs and is not committed.

| Trial | Suite | SDK run | Result | Step-2 first read | Notes |
| --- | --- | --- | --- | --- | --- |
| 01 | `suite_380783d9…` | `dcd38211…` | Support | 53 B |  |
| 02 | `suite_9107d070…` | `3d1733d1…` | Falsified | 54 B | self-initiated `cat -A` check, then a 54-byte `file_write` repair |
| 03 | `suite_61f4df4a…` | `1dbe2073…` | Support | 53 B |  |
| 04 | `suite_a8322d3e…` | `6d43cb6d…` | Support | 53 B |  |
| 05 | `suite_e5be55ef…` | `65cf61c4…` | Support | 53 B |  |
| 06 | `suite_ae201093…` | `30bc0f8f…` | Non-support: not reached | 66 B (unrelated file) | malformed tool markup in the only step-1 response; fixture never created |
| 07 | `suite_330c8009…` | `34f33513…` | Support | 53 B |  |
| 08 | `suite_d7569f0f…` | `6ef19b37…` | Support | 53 B | second hashed edit and a failed `file_edit` attempt; no repair |
| 09 | `suite_797a09f3…` | `0222349e…` | Support | 53 B | doubled `<tool_call>` tag (arguments unparsed; results decisive) |
| 10 | `suite_1a0140dc…` | `1836cb92…` | Support | 53 B | doubled `<tool_call>` tag (arguments unparsed; results decisive) |

**Rate: 8/10. Infrastructure replacements: 0.** Including the pilot, the 11 executions reported 1,534,315 total tokens.

The supporting trials followed the same pattern:

- The Agent wrote the exact 54-byte CRLF fixture with `file_write`.
- `file_edit_hashed` on anchor `L3:3c1` with `new_text="timeout=45"` returned "File updated successfully".
- The edited line then ended with LF only, giving 53 bytes, and no successful correction happened before step 1 ended.

In every trial that reached the edit, `file_read_hashed` kept returning the pre-edit view (`L3:3c1|timeout=30`), while `file_read` showed `timeout=45\n`. In all eight supporting trials, the Agent told the user that the edit was correct on disk. It blamed the hashline view on a stale cache and did not notice the lost CR. Trial 05 explicitly claimed that "All four CRLF pairs … are intact". These completion claims are secondary annotations, as preregistered.

Trial 06 is retained as non-support. It is a native execution problem after an HTTP 200 response, not infrastructure, which matches how v1 trial 09 was handled.

## Posthoc upstream check (after the ten trials)

I searched `nullclaw/nullclaw` issues and PRs for CRLF, line ending, carriage return, hashline, `file_edit_hashed`, `file_read_hashed` and stale cache. Nothing related was found. PRs #442 and #444 introduced Hashline and Hashline v3 and are not fixes. On the default branch, `src/tools/file_edit_hashed.zig` is byte-identical to the pinned `5f1cade0`, and line 201 still inserts a literal `"\n"` separator. No upstream issue or PR was filed.
