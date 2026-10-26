"""Classify one NullClaw H3 Case v2 run with the preregistered byte oracle (H3-v2-amendment.md).

support      = step 1 has an ok file_edit_hashed call, and the first ok native read in step 2
               (file_read or file_read_hashed) is not byte-identical to the expected text.
falsified    = that first step-2 read equals the expected 54 bytes exactly.
not_reached  = no ok file_edit_hashed call in step 1, or a native execution error before it.
no_evidence  = step 1 edited, but step 2 has no ok native read (kept in the denominator).
infra        = zero model calls, or any non-200 model response.
Step-2 mutations and the step-1 completion claim are recorded but do not change the result.
"""
import json, re, sys
from pathlib import Path

ORACLE = json.loads((Path(__file__).parent / "oracle-v2.json").read_text())
CASE = json.loads((Path(__file__).parent / "case-v2.json").read_text())["cases"][0]["inputs"]
CALL = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.S)
RESULT = re.compile(r'<tool_result name="([^"]+)" status="([^"]+)">\n(.*?)\n</tool_result>', re.S)
HASHLINE = re.compile(r"^L\d+:[0-9a-f]+\|", re.M)
MUTATING = {"file_write", "file_edit", "file_edit_hashed", "file_append"}

root = Path(sys.argv[1])
d = next(p.parent for p in root.rglob("run.json") if "trajectory" in str(p))
rows = [json.loads(l) for l in (d / "logs/network.jsonl").read_text().splitlines()]
requests = [r["data"] for r in rows if r["event"] == "llm_request"]
responses = [r["data"] for r in rows if r["event"] == "llm_response"]


def step_of(request):
    for m in request["payload"].get("messages", []):
        if m.get("role") == "user" and isinstance(m.get("content"), str):
            for i, step in enumerate(CASE):
                if m["content"].startswith(step["payload"][:60]):
                    return i + 1
    return None


def transcript(step):
    """Tool calls and results in order, from the last request of a step (it carries the full history)."""
    mine = [r for r in requests if step_of(r) == step]
    events = []
    if not mine:
        return events
    for m in mine[-1]["payload"].get("messages", []):
        c = m.get("content")
        if not isinstance(c, str):
            continue
        if m["role"] == "assistant":
            for raw in CALL.findall(c):
                try:
                    events.append(("call", json.loads(raw)))
                except json.JSONDecodeError:
                    events.append(("call", {"raw_unparsed": raw[:200]}))
        elif m["role"] == "user":
            for name, status, body in RESULT.findall(c):
                events.append(("result", {"name": name, "status": status, "content": body}))
    return events


def read_bytes(result):
    body = result["content"]
    if result["name"] == "file_read_hashed":
        # One "L<n>:<hash>|<segment>\n" per LF-separated segment; CR stays inside the segment.
        if body.endswith("\n"):
            body = body[:-1]
        body = "\n".join(HASHLINE.sub("", line, count=1) for line in body.split("\n"))
    return body


statuses = [r.get("status") for r in responses]
s1, s2 = transcript(1), transcript(2)
edits = [e for k, e in s1 if k == "result" and e["name"] == "file_edit_hashed" and e["status"] == "ok"]
reads2 = [e for k, e in s2 if k == "result" and e["name"] in ("file_read", "file_read_hashed") and e["status"] == "ok"]
mutations2 = [e.get("name") for k, e in s2 if k == "call" and e.get("name") in MUTATING]
end_text = read_bytes(reads2[0]) if reads2 else None
expected = ORACLE["expected_final_text"]

if not requests or any(s != 200 for s in statuses):
    verdict = "infra"
elif not edits:
    verdict = "not_reached"
elif end_text is None:
    verdict = "no_evidence"
elif end_text == expected:
    verdict = "falsified"
else:
    verdict = "support"

results = sorted(root.rglob("steps/*/result.json"))
outputs = [json.loads(p.read_text()).get("output") or "" for p in results]
print(json.dumps({
    "verdict": verdict,
    "model_calls": len(requests),
    "model_statuses": sorted(set(statuses)),
    "step1_calls": [e.get("name", "unparsed") for k, e in s1 if k == "call"],
    "step1_hashed_edit_new_text": [e.get("arguments", {}).get("new_text") for k, e in s1
                                   if k == "call" and e.get("name") == "file_edit_hashed"],
    "step2_first_read_tool": reads2[0]["name"] if reads2 else None,
    "step2_first_read_bytes": len(end_text.encode()) if end_text is not None else None,
    "step2_first_read_repr": repr(end_text) if end_text is not None else None,
    "end_state_exact": end_text == expected if end_text is not None else None,
    "step2_mutating_calls": mutations2,
    "step_statuses": [json.loads(p.read_text()).get("status") for p in results],
    "step1_claim_excerpt": outputs[0][-400:] if outputs else None,
}, ensure_ascii=False, indent=2))
