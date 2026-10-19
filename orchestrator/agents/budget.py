from datetime import datetime


def analyze_budget(state):
    """Earned value metrics. Deliberately plain code: arithmetic is not a job for a language model."""
    rows, out = state["budget_rows"], {"workstreams": {}}
    tot = {"bac": 0.0, "pv": 0.0, "ev": 0.0, "ac": 0.0}
    for r in rows:
        bac, pv, ev, ac = (float(r[k]) for k in ("bac", "pv", "ev", "ac"))
        for k, v in zip(tot, (bac, pv, ev, ac)):
            tot[k] += v
        out["workstreams"][r["workstream"]] = _metrics(bac, pv, ev, ac)
    out["program"] = _metrics(tot["bac"], tot["pv"], tot["ev"], tot["ac"])
    flagged = [n for n, m in out["workstreams"].items() if m["cpi"] < 0.90 or m["spi"] < 0.90]
    out["flagged"] = flagged
    return {"budget_metrics": out,
            "audit": [{"step": "budget", "at": datetime.now().isoformat(timespec="seconds"),
                       "detail": f"program CPI {out['program']['cpi']}, SPI {out['program']['spi']}; flagged: {', '.join(flagged) or 'none'}"}]}


def _metrics(bac, pv, ev, ac):
    cpi, spi = ev / ac, ev / pv
    return {"bac_m": round(bac, 2), "pv_m": round(pv, 2), "ev_m": round(ev, 2), "ac_m": round(ac, 2),
            "cost_variance_m": round(ev - ac, 2), "schedule_variance_m": round(ev - pv, 2),
            "cpi": round(cpi, 2), "spi": round(spi, 2), "eac_m": round(bac / cpi, 1)}
