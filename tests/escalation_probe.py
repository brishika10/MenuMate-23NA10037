"""Probe the code escalation detector alone (no LLM). Positives/negatives written by me, so this checks the
patterns work, not recall on unseen phrasings."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.detect import detect_escalation as d  # noqa: E402

POS = ["The dal tasted sour and had gone off", "my lips puffed up after the prawn curry",
       "my throat is tingling after the satay", "I had to use my epipen after dinner",
       "I fell ill after eating your biryani", "loose motions since last night after your food",
       "chicken was pink inside", "there was a stone in my rice", "amount debited twice for one order",
       "my refund has not been refunded yet", "paise wapas nahi aaye", "khane ke baad chakkar aa raha hai",
       "chicken kaccha tha", "खाना खाने के बाद गला खराब हो गया", "पेट खराब है खाना खाने के बाद",
       "money got deducted but order failed"]
NEG = ["okay order sweet lassi 2", "I want something off the menu that is spicy", "Bhai 4 log hain, non-veg chahiye",
       "something light, not too heavy", "Can I get a glass of sweet lassi", "tasty paneer please",
       "I love pink lemonade style drinks", "kachori and chai please", "suggest a dessert, I am allergic to nuts",
       "Jain food only please, under 300", "gajar halwa for 2", "I paid last time with UPI, any offers?",
       "something quick, I need it in 10 minutes"]
missed = [p for p in POS if not d(p)]
false = [(n, d(n)) for n in NEG if d(n)]
print(f"positives caught: {len(POS) - len(missed)}/{len(POS)}  missed: {missed}")
print(f"negatives clean:  {len(NEG) - len(false)}/{len(NEG)}  false positives: {false}")
