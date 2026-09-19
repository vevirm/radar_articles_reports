from scripts.claim_reasoning_live import _trend_title_pair

BANNED = ("doubles down", "second thoughts", "handbrake", "throttle", "fine print", "gets fenced in", "bets bigger")

def test_generated_trend_titles_use_plain_language():
    for i in range(12):
        left, right = _trend_title_pair("energy supply", f"key-{i}", i)
        joined = f"{left} {right}".lower()
        assert not any(term in joined for term in BANNED)
