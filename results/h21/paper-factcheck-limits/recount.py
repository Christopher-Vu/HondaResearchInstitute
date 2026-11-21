"""Recount of the counted tries, read by hand from VARIANTS.md, compared with appendix-tries.tex.

    /opt/miniconda3/bin/python results/h21/paper-factcheck-limits/recount.py

RECOUNT: (VARIANTS.md line of the row, id, configurations counted, running count the log records or None,
where the position comes from). Positions are assigned in this order, one per configuration.
"""
import re
from pathlib import Path

RECOUNT = [
    (61, "v1 rescored", 3, "3", "row"),
    (62, "m03", 1, "6", "row; 4 rows share 4-6"), (63, "m04", 1, "6", "row; shared"),
    (64, "m07", 1, "6", "row; shared"), (65, "m06", 0, "6", "row; shared, uncounted in log"),
    (72, "m05", 49, "55", "row"), (73, "m01", 2, "59", "row"), (74, "m02", 2, "59", "row"),
    (83, "m08", 2, "71", "row"), (84, "m09", 1, "71", "row"), (85, "m10", 1, "71", "row"),
    (86, "m12", 6, "71", "row"), (87, "m13", 2, "71", "row"), (88, "m11", 6, "77", "row"),
    (89, "m14", 2, "79", "row"),
    (103, "m21", 1, "80", "row"), (104, "m15", 6, "86", "row"), (105, "m16", 4, "90", "row"),
    (106, "m17", 4, "94", "row"), (107, "m18", 7, "101", "row"), (108, "m19", 2, "103", "row"),
    (109, "m20", 1, "104", "row; 2 pools, count +1"),
    (131, "j01", 1, "75", ":168 reconciles"), (132, "j02", 1, "75", ":168"), (133, "j03", 1, "75", ":168"),
    (134, "j04", 1, "75", ":168"), (142, "j05", 1, "76", ":168"), (143, "j06", 1, "77", ":168"),
    (144, "j07", 1, "78", ":168"),
    (161, "j04", 1, "112", "row"), (162, "j02", 1, "113", "row"), (163, "j03", 1, "114", "row"),
    (164, "j05", 1, "115", "row"), (165, "j06", 1, "116", "row"), (166, "j07", 1, "117", "row"),
    (183, "j11", 1, "118", "row"), (184, "j11", 1, "119", "row"), (202, "j12", 1, "120", "row"),
    (203, "j12", 1, "121", "row"), (224, "j13", 1, "122", "row"), (225, "j13", 1, "123", "row"),
    (249, "j14", 1, "124", "row"), (281, "j15", 1, "125", "row"), (282, "j15", 1, "126", "row"),
    (319, "j09", 1, "127", "row"), (320, "j10", 1, "128", "row"),
    (365, "m08", 1, "129", "row"), (366, "m15", 1, "130", "row"), (367, "m11", 1, "131", "row"),
    (368, "m12", 1, "132", "row"), (369, "m16", 1, "133", "row"), (370, "j05", 1, "134", "row"),
    (587, "j09", 1, "135", "row"), (588, "m22", 1, "136", "row"), (589, "m23", 1, "137", "row"),
    (590, "m24", 2, "139", "row"), (591, "m25", 5, "144", "row"), (592, "m26", 2, "146", "row"),
    (593, "m27", 1, "147", "row"), (594, "m28", 1, "148", "row"), (595, "m29", 1, "149", "row"),
    (596, "m30", 1, "150", "row"), (597, "m31", 1, "151", "row"), (598, "m32", 1, "152", "row"),
    (599, "m33", 1, "153", "row"), (600, "m34", 1, "154", "row"), (601, "m35", 1, "155", "row"),
    (602, "m36", 1, "156", "row"), (603, "m38", 1, "157", "row"), (604, "m39", 2, "159", "row"),
    (661, "m40", 1, "160", "row"), (662, "m41", 1, "161", "row"), (663, "m42", 1, "162", "row"),
    (664, "m43", 1, "163", "row"), (665, "m44", 1, "164", "row"),
    (703, "m41", 1, "165", "row"), (704, "m40", 1, "166", "row"), (705, "m44", 1, "167", "row"),
    (706, "m23", 1, "168", "row"), (707, "m39", 1, "169", "row"),
    (797, "m45", 1, "170", "row"), (798, "m46", 1, "171", "row"), (799, "m47", 1, "172", "row"),
    (800, "m48", 1, "173", "row"), (801, "m49", 1, "174", "row"),
    (824, "m41", 2, None, "range 175-182 at :822, order inferred"), (825, "m41", 2, None, ":822"),
    (826, "m40", 2, None, ":822"), (827, "m23", 2, None, ":822"),
    (883, "m49", 4, "183-186", "prose"), (890, "m50", 1, "187", "row"), (891, "m51", 1, "188", "row"),
    (927, "m23", 1, None, "'2 tried' at :923; implied by :959"), (928, "m40", 1, None, ":923, :959"),
    (959, "r01", 1, "191", "row"), (960, "r02", 1, "192", "row"), (961, "r03", 1, "193", "row"),
    (962, "r04", 1, "194", "row"), (963, "r05", 1, "195", "row"), (964, "r06", 1, "196", "row"),
    (965, "r07", 1, "197", "row"),
    (1007, "r08", 1, "198", "row"), (1008, "r09", 1, "199", "row"), (1009, "r10", 1, "200", "row"),
    (1010, "r11", 1, "201", "row"), (1011, "r12", 1, "202", "row"),
    (1085, "u01-u03", 3, "205", "row"), (1086, "u04-u06", 3, "208", "row"), (1087, "u07-u09", 3, "211", "row"),
    (1088, "u10, u11", 2, "213", "row"), (1089, "u12-u14", 3, "216", "row"),
    (1062, "img-mean", 1, None, "total 219 at :1062; rows only in prereg-views.md:72-75"),
    (1062, "query-mean", 1, None, ":1062"), (1062, "caption", 1, None, ":1062"),
    (1200, "j16", 1, "220", "row"), (1201, "j16+route", 1, "221", "row"), (1202, "j17+route", 1, "222", "row"),
    (1164, "j18", 1, "219 + 1", "total 224 at :1298-1299, no order"), (1165, "j19", 1, "219 + 2", ":1298-1299"),
    (1328, "j24", 1, "224 + 1", ":1384 assigns 225"), (1329, "j25", 1, "224 + 2", ":1384 assigns 226"),
    (1376, "j22", 1, "224 + 1", ":1384 assigns 227"), (1377, "j23", 1, "224 + 2", ":1384 assigns 228"),
    (1409, "j20", 1, "224 + 1", ":1415 assigns 229"), (1410, "j21", 1, "224 + 2", ":1415 assigns 230"),
    (1479, "j26", 1, "230 + 1", ":1495"), (1480, "j27", 1, "230 + 2", ":1495"),
]


def positions():
    out, nxt = [], 1
    for line, rid, n, recorded, how in RECOUNT:
        if rid == "m03":
            start = nxt
        span = (start, start + 2) if rid in ("m03", "m04", "m07", "m06") else (nxt, nxt + n - 1)
        out.append((line, rid, span, recorded, how))
        nxt += n
    return out, nxt - 1


def appendix_rows(tex):
    rows, source = [], None
    for text in tex.read_text().splitlines():
        if text.strip().startswith("% source: VARIANTS.md:"):
            source = [int(n) for n in re.findall(r":(\d+)", text.split("(")[0])]
            continue
        cells = [c.strip() for c in text.rstrip("\\ ").split(" & ")]
        if source and len(cells) == 5 and re.match(r"\d", cells[4]):
            pos = re.sub(r"\$\^\\dagger\$", "", cells[4]).split("--")
            rows.append((source, cells[0], (int(pos[0]), int(pos[-1])), "dagger" in cells[4]))
            source = None
    return rows


def fmt(span):
    return str(span[0]) if span[0] == span[1] else f"{span[0]}-{span[1]}"


def main():
    mine, total = positions()
    theirs = appendix_rows(Path("docs/paper/appendix-tries.tex"))
    print(f"recount total {total}; my rows {len(mine)}; appendix rows {len(theirs)}\n")
    print("| # | VARIANTS.md line | id | my position | recorded in log | position source | appendix | agrees |")
    print("|---|---|---|---|---|---|---|---|")
    for k, ((line, rid, span, rec, how), app) in enumerate(zip(mine, theirs), 1):
        aline, aid, aspan, dag = app
        same = line in aline and aspan == span
        print(f"| {k} | {line} | {rid} | {fmt(span)} | {rec or '-'} | {how} | :{', :'.join(map(str, aline))} {fmt(aspan)}{' (dagger)' if dag else ''} | {'yes' if same else 'NO'} |")
    extra = len(theirs) - len(mine)
    if extra:
        print(f"\nrow count differs by {extra}")


if __name__ == "__main__":
    main()
