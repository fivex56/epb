# fill_prices.py
# Fills N/A prices with estimates based on known data.
# Rules:
#   130k = 65k × 2 (universal)
#   1h ↔ 1d via market median ratio (from platforms that have both)
#   3d = 1d × 3 (unless real data exists)
#   10d = 1d × 10 (unless real data exists)
#   15m: only fill if platform has real 15m data (currently only TR Energy)
# Never overwrites real scraped prices.
# Python 3.9+

import os, sys, json, math

TERMS = ['15m', '1h', '1d', '3d', '10d']
VOLUMES = ['65k', '130k']
PRICE_KEY = '{vol}_{term}_price'


def isnum(v):
    return isinstance(v, (int, float)) and math.isfinite(float(v))


def fmt(v):
    return round(v, 2)


def load(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save(obj, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False)
        f.write('\n')


def get_known(p):
    """{(vol, term): float} for all real numeric prices."""
    k = {}
    for vol in VOLUMES:
        for term in TERMS:
            key = PRICE_KEY.format(vol=vol, term=term)
            v = p.get(key)
            if isnum(v):
                k[(vol, term)] = float(v)
    return k


def median(lst):
    if not lst:
        return None
    s = sorted(lst)
    n = len(s)
    if n % 2:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2


def compute_ratios(platforms):
    """Compute market median ratios from platforms that have both prices."""
    vol_ratios = []    # 130k / 65k for same term
    h_to_d_ratios = []  # 1d / 1h for same volume

    for p in platforms:
        known = get_known(p)
        for term in TERMS:
            v65 = known.get(('65k', term))
            v130 = known.get(('130k', term))
            if v65 and v130 and v65 > 0:
                vol_ratios.append(v130 / v65)
        for vol in VOLUMES:
            v1h = known.get((vol, '1h'))
            v1d = known.get((vol, '1d'))
            if v1h and v1d and v1h > 0:
                h_to_d_ratios.append(v1d / v1h)

    vr = median(vol_ratios) or 2.0
    hd = median(h_to_d_ratios) or 1.57

    return {'vol_ratio': vr, 'h_to_d': hd}


def fill_platform(p, ratios):
    """Fill N/A slots for one platform. Returns dict of filled values (vol,term)->price."""
    known = get_known(p)
    if not known:
        return {}

    vr = ratios['vol_ratio']
    hd = ratios['h_to_d']
    est = dict(known)  # start with real data

    # ---- Pass 1: volume cross-fill (65k ↔ 130k for same term) ----
    for term in TERMS:
        v65 = est.get(('65k', term))
        v130 = est.get(('130k', term))
        if v65 and not v130:
            est[('130k', term)] = v65 * vr
        if v130 and not v65:
            est[('65k', term)] = v130 / vr

    # ---- Pass 2: 15m → 1h for platforms with 15m but no 1h ----
    # (do this BEFORE 1h↔1d so the chain propagates)
    if ('65k', '15m') in known and ('65k', '1h') not in known:
        v65_15 = known[('65k', '15m')]
        est[('65k', '1h')] = v65_15 * 1.06
        est[('130k', '1h')] = v65_15 * 1.06 * vr

    # ---- Pass 3: 1h out-of-place check (do this after 15m→1h) ----
    for vol in VOLUMES:
        v1h = est.get((vol, '1h'))
        v1d = est.get((vol, '1d'))
        if v1h and not v1d:
            est[(vol, '1d')] = v1h * hd

    # ---- Pass 4: fill 3d and 10d from 1d ----
    for vol in VOLUMES:
        v1d = est.get((vol, '1d'))
        if v1d:
            if (vol, '3d') not in known:
                est[(vol, '3d')] = v1d * 3
            if (vol, '10d') not in known:
                est[(vol, '10d')] = v1d * 10

    # ---- Pass 5: 130k from 65k for 15m if not already filled ----
    if ('65k', '15m') in known:
        v65_15 = known[('65k', '15m')]
        if ('130k', '15m') not in known:
            est[('130k', '15m')] = v65_15 * vr

    return est


def main():
    in_path = sys.argv[1] if len(sys.argv) > 1 else 'result.json'
    out_path = sys.argv[2] if len(sys.argv) > 2 else 'result.json'

    data = load(in_path)
    platforms = data.get('platforms', [])

    ratios = compute_ratios(platforms)
    print(f"Market ratios: vol_ratio={ratios['vol_ratio']:.4f}, h_to_d={ratios['h_to_d']:.4f}")

    total_filled = 0

    for p in platforms:
        est = fill_platform(p, ratios)

        for vol in VOLUMES:
            for term in TERMS:
                key = PRICE_KEY.format(vol=vol, term=term)
                current = p.get(key)
                new = est.get((vol, term))

                if isnum(current):
                    continue  # keep real data

                if new is not None:
                    total_filled += 1
                    p[key] = fmt(new)

    data['platforms'] = platforms
    data['filled'] = {'estimated': total_filled}
    data['meta']['fill_ratios'] = {k: round(v, 4) for k, v in ratios.items()}

    save(data, out_path)
    print(f"Done: filled {total_filled} N/A slots\n")

    for p in platforms:
        name = p.get('platform_name', p.get('platform_id', '?'))[:35]
        count = sum(1 for vol in VOLUMES for term in TERMS
                    if isnum(p.get(PRICE_KEY.format(vol=vol, term=term))))
        p65h = p.get('65k_1h_price', '?')
        p130h = p.get('130k_1h_price', '?')
        p65d = p.get('65k_1d_price', '?')
        p130d = p.get('130k_1d_price', '?')
        p653d = p.get('65k_3d_price', '?')
        p6510d = p.get('65k_10d_price', '?')
        print(f"  {name:35s} {count}/10  65k: {str(p65h):>8s} / {str(p65d):>8s} / {str(p653d):>8s} / {str(p6510d):>8s}  |  130k: {str(p130h):>8s} / {str(p130d):>8s}")


if __name__ == '__main__':
    main()
