"""MenuMate pipeline. Order of checks follows policy.md:
P-01 escalation (code, then LLM flag) -> P-02 clarify -> hard rules P-03..P-08 -> soft ranking -> grounded reply.
The recommender is only reachable when route == "recommend"; escalate/clarify return before it."""
from schema import Output, Profile, RuleTrace, Tokens

from . import detect
from .extract import extract_profile
from .filters import apply_hard_rules
from .llm import Usage, model_name
from .menu import MENU
from .policy import ESCALATION_TEXT
from .rank import rank, requested_dishes
from .reply import clarify_reply, honesty_note, write_reply


def _escalate(cid, profile, usage, detail) -> Output:
    text = ESCALATION_TEXT["hi"] if profile.language == "hi" else ESCALATION_TEXT["en"]
    profile.escalation = True
    return Output(conversation_id=cid, route="escalate", profile=profile, reply=text, recommendations=[],
                  rule_trace=[RuleTrace(rule_id="P-01", outcome="exclude", detail=detail)],
                  tokens=Tokens(prompt=usage.prompt, completion=usage.completion), model=model_name())


def respond(conversation_id: str, history: list[dict], message: str) -> Output:
    usage = Usage()
    language = detect.detect_language(message)

    # Gate 1 (P-01, code only, before any LLM call): if this fires, nothing below runs.
    hit = detect.detect_escalation(message)
    if hit:
        return _escalate(conversation_id, Profile(language=language), usage, f"code detector matched '{hit}'")

    profile, ambiguous, info = extract_profile(history, message, usage)

    # Gate 2 (P-01, LLM flag): second chance for phrasings the regex misses.
    if profile.escalation:
        return _escalate(conversation_id, Profile(language=language), usage, "LLM extractor flagged escalation")

    trace = [RuleTrace(rule_id="P-01", outcome="pass")]
    # P-02: ambiguous allergy -> one question, no recommendations
    if ambiguous:
        trace.append(RuleTrace(rule_id="P-02", outcome="exclude", detail="ambiguous allergy"))
        return Output(conversation_id=conversation_id, route="clarify", profile=profile,
                      reply=clarify_reply(profile, message), rule_trace=trace,
                      tokens=Tokens(prompt=usage.prompt, completion=usage.completion), model=model_name())
    trace.append(RuleTrace(rule_id="P-02", outcome="pass"))

    eligible, hard_trace = apply_hard_rules(MENU, profile)
    requested = requested_dishes(MENU, message)
    picked, soft_trace, meta = rank(MENU, eligible, profile, requested)
    picked_items = [MENU[s["id"]] for s in picked]
    reply, recs, rinfo = write_reply(message, profile, picked_items, MENU, usage, history, meta["requested_eligible"])

    # Belt and braces: drop anything not in the hard-filtered set, whatever the LLM returned.
    eligible_set = set(eligible)
    recs = [r for r in recs if r.item_id in eligible_set][:3]
    # "Fewer than 3" is only claimed when fewer were eligible/selectable, not when the LLM chose to show fewer.
    note = honesty_note(len(recs) if not recs else len(picked), meta["over_budget"], meta["total_price"], profile)
    reply = (reply + " " + note).strip() if note else reply

    # Observability: how the extraction and reply validator went (read by eval.py for groundedness).
    vtrace = RuleTrace(rule_id="VALIDATOR", outcome="pass" if rinfo["first_attempt_valid"] else "penalize",
                       detail=f"source={rinfo['reply_source']} attempts={rinfo['reply_attempts']} "
                              f"extract={info['extract_source']} errors={str(rinfo['validation_errors'])[:300]}")
    return Output(conversation_id=conversation_id, route="recommend", profile=profile, reply=reply,
                  recommendations=recs, rule_trace=trace + hard_trace + soft_trace + [vtrace],
                  tokens=Tokens(prompt=usage.prompt, completion=usage.completion), model=model_name())
