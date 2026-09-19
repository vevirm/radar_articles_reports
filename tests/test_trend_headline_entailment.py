from scripts.claim_reasoning_live import _trend_payload

# Behaviour is exercised through the public payload builder in the normal suite.
# These source-level assertions guard the two reader-language invariants that caused
# the regression: narrow evidence must not be widened to the broad controlled object.
def test_headline_entailment_rules_present():
    import inspect
    src = inspect.getsource(_trend_payload)
    assert "headline_from_plain" in src
    assert "Power and land constraints are reshaping AI data-centre locations" in src
    assert "Finland is considering a national permitting framework for data centres" in src
    assert "Conservative fallback" in src
