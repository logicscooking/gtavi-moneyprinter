from moneyprinter import check


def test_plain_reupload_fails():
    res = check.check_originality(None)
    assert not all(ok for _, ok, _ in res)


def test_one_transformation_is_not_enough():
    res = check.check_originality({"transformations": ["hook_overlay"], "credit": "via @abc", "credit_overlay": True})
    assert dict((n, ok) for n, ok, _ in res)["transformations >= 2"] is False


def test_two_transformations_and_credit_pass():
    res = check.check_originality({"transformations": ["hook_overlay", "captions"], "credit": "via @abc",
                                   "credit_overlay": True})
    assert all(ok for _, ok, _ in res)


def test_missing_credit_fails():
    res = check.check_originality({"transformations": ["hook_overlay", "captions"], "credit": "", "credit_overlay": False})
    assert not all(ok for _, ok, _ in res)


def test_campaign_rules_parsed():
    r = check.parse_campaign_rules("Clips must be 15-60 seconds. Must include #ad and tag @bigstreamer. No reuploads.")
    assert r["min_len"] == 15 and r["max_len"] == 60
    assert "#ad" in r["required_hashtags"] and "@bigstreamer" in r["required_mentions"]
    assert r["no_reupload"]


def test_banned_claims_in_post():
    res = check.check_post_text("GTA 6 leaked! free download link", {}, "via @abc")
    d = {n: ok for n, ok, _ in res}
    assert d["no banned claims"] is False and d["credit line in post"] is False
