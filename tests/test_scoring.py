from moneyprinter import scoring


def test_robust_norm_flat_signal_has_no_peaks():
    assert scoring.robust_norm([5.0] * 30) == [0.0] * 30


def test_missing_signals_are_skipped_not_faked():
    combined, meta = scoring.fuse({"loudness": [0.0] * 60, "hype": None, "chat": []})
    assert meta["weights"] == {} and combined == []


def test_pick_moments_finds_spike_and_explains_it():
    n = 120
    loud = [-30.0] * n
    for s in range(70, 75):
        loud[s] = -5.0
    chat = [0.0] * n
    for s in range(71, 76):
        chat[s] = 20.0
    ms = scoring.pick_moments({"loudness": loud, "chat": chat, "replayed": None}, top=2, min_len=12, max_len=30)
    assert ms, "expected at least one moment"
    best = ms[0]
    assert best.start <= 70 < best.end
    assert set(best.breakdown) == {"loudness", "chat"}
    assert "replayed" not in best.breakdown
    assert "chat explosion" in scoring.why(best) or "loud spike" in scoring.why(best)


def test_moments_do_not_overlap():
    n = 200
    loud = [-30.0] * n
    for p in (40, 48, 120, 170):
        loud[p] = 0.0
    ms = scoring.pick_moments({"loudness": loud}, top=4, min_len=12, max_len=20)
    spans = sorted((m.start, m.end) for m in ms)
    for (a1, b1), (a2, b2) in zip(spans, spans[1:]):
        assert b1 <= a2


def test_hype_words_and_heatmap():
    words = [{"start": 3.1, "end": 3.4, "word": "NO"}, {"start": 3.5, "end": 3.8, "word": "WAY"},
             {"start": 9, "end": 9.2, "word": "okay"}]
    h = scoring.hype_per_second(words, 12)
    assert h[3] > 0 and h[9] == 0
    hm = scoring.heatmap_per_second([{"start_time": 0, "end_time": 5, "value": 0.2},
                                     {"start_time": 5, "end_time": 10, "value": 1.0}], 10)
    assert hm[7] == 1.0 and hm[1] == 0.2


def test_breakdown_table_marks_missing_as_na():
    m = scoring.Moment(10, 25, 0.5, 13, {"loudness": 0.2})
    t = scoring.breakdown_table([m], ["loudness", "hype"])
    assert "n/a" in t and "0.200" in t
