# H3 Case v2 amendment — 2026-10-26

Status: preregistered, not yet executed. This amendment adds Case v2 for the existing H3. It adds no new hypothesis. The v1 results, report and evidence archive stay unchanged, and the v1 result remains 4/10 (not qualifying). v1 and v2 trials are never pooled.

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
