from moneyprinter import roi

PAGE_A = """# Big Streamer GTA 6 clips
$1.50 per 1,000 views
$1,200 of $5,000 paid out
Max payout per clip: $300
- Clip only Big Streamer
- Post on TikTok, Instagram or YouTube
"""
PAGE_B = """# Brand campaign
$3 per 1K views
Budget left: $0
"""
PAGE_C = """# Mystery campaign
Rules: be nice. Rate shown after joining.
"""


def test_parse_reads_only_what_is_on_the_page():
    a = roi.parse_campaign(PAGE_A)
    assert a.rate_per_1k == 1.5 and a.budget_left == 3800 and a.max_payout == 300
    assert set(a.platforms) >= {"tiktok", "youtube", "instagram"}
    c = roi.parse_campaign(PAGE_C)
    assert c.rate_per_1k is None and c.budget_left is None


def test_unknown_rate_is_na_never_invented():
    c = roi.parse_campaign(PAGE_C)
    assert c.expected_per_hour(50_000, 3) is None
    assert roi.na(c.rate_per_1k) == "n/a"


def test_rank_prefers_money_per_hour_and_drops_exhausted():
    camps = [roi.parse_campaign(PAGE_A, "a"), roi.parse_campaign(PAGE_B, "b"), roi.parse_campaign(PAGE_C, "c")]
    rows = roi.rank(camps, views=20_000, clips_per_hour=3)
    assert rows[0]["name"].startswith("Big Streamer")
    assert rows[0]["expected_per_hour"] == 90.0  # 1.5 * 20 * 3
    assert rows[-1]["exhausted"] is True


def test_no_views_means_na_per_hour():
    rows = roi.rank([roi.parse_campaign(PAGE_A)], views=None)
    assert rows[0]["expected_per_hour"] is None
