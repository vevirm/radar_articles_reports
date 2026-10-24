from scripts.import_deep_scan_results import normalize_claim_scope_alias


def test_national_alias_requires_real_eu_country():
    claim = {"scope": {"level": "national", "countries": ["DE"]}}
    assert normalize_claim_scope_alias(claim)
    assert claim["scope"] == {"level": "member_state", "countries": ["DE"]}


def test_does_not_guess_missing_country_or_rewrite_third_country():
    for countries in ([], ["US"], ["FI", "US"], ["fi"]):
        claim = {"scope": {"level": "national", "countries": countries}}
        assert not normalize_claim_scope_alias(claim)
        assert claim["scope"]["level"] == "national"
    claim = {"scope": {"level": "member_state", "countries": []}}
    assert not normalize_claim_scope_alias(claim)
