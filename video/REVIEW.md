# REVIEW: One road, three drives (draft-v2)

v2 (`renders/draft-v2.mp4`) is the layout pass after the coordinator review: see "v2 layout pass" below. The measurements and v1 notes further down still hold unless v2 says otherwise; the QA frames to use are in `review/qa-v2/`.

Storyline A. B (evidence wall) and C (into the numbers) were not built.

## Structure
Seven scene files plus an end card. Scene length = voice clips + 0.35 s each; the voice is the clock (audio placed at each scene's start).

| scene | clips | start | length |
| --- | --- | --- | --- |
| scene-a home stage, push/pan, pull-back | 1-3 | 0.00 | 23.02 |
| scene-b pile of 738, bars, Jaccard | 4-5 | 23.02 | 17.16 |
| scene-c 896 bars, dictionary, timeline strips | 6-8 | 40.18 | 20.98 |
| scene-d P4 group of 31, 0.57 | 9-10 | 61.16 | 15.40 |
| scene-e frozen frame, identical numbers | 11-12 | 76.56 | 15.42 |
| scene-f P7 group of 48, delay | 13-14 | 91.98 | 15.81 |
| scene-g fresh piles, H3 scores, "two of three faults found" | 15-16 | 107.79 | 18.22 |
| scene-end project line + Cua link | none | 126.01 | 4.00 |

Every number on screen is filled from `data.js` (`data-bind` or script). Seams: 7, all LEFT (cut-the-curve, exit `power3.in` / entry `power3.out`, 0.4 s, 260 px). `ledger.json` + `seam-gate.mjs verify`: PASSED, 0 fail, 0 warn (run with CHROME_PATH set to system Chrome; the cached headless-shell would not start).

## Measured
- `npx hyperframes check --json`: 0 errors; 1 warning (`first_frame_empty`, a false positive: `review/qa/at-0s.png` shows three real frames at t=0).
- Render: 1920x1080, 30 fps, 125.97 s, 3779 frames, h264 + aac. Audio: -17.1 LUFS integrated, true peak -1.6 dB, no clipping, voice detected; silences fall on the 0.35 s scene gaps.
- Rendered frames at 8.4, 12.5, 28, 66.5, 72.4, 97, 124.5 s were pulled from the mp4 and match the snapshots.

## Looked at (snapshots)
Per-scene contact sheets: `review/a` ... `review/g`. Hero moves sampled at 8 frames: tile fly-in `review/motion/fly`, group slide `review/motion/slide`, push-in `review/motion/push`. Review sheets: `review/full/review-beats.jpg`, `review-seam-01..07.jpg`, `review-phone.jpg`. SPEC QA frames: `review/qa/` (hook at-0s, frozen hold at-12s, 278 ink tiles at-29.2s, 31 orange tiles at-64.6s, 0.57 at-72.5s, 48 group at-96.8s, end card at-125s).

## Fixed during review
- Cross-cut clean to black patch jumped to a different road position; the demo drive now rewinds to step 0 so the same frame gains the rectangle.
- Frozen hold was too short to read; it is held about 1.6 s with a clock showing the real freeze length.
- Counter labels appeared before their numbers (bad selectors); fixed.
- Pile overlapped row labels in scene E; rows scaled to 0.66 so type stays above the 28 px floor.
- Whole home row moved down 60 px (top-heavy first frame).
- Dead stretches (scene D, scene F) broken with real motion; scene D score hold marked `data-hold`.
- Parked-car schematic overlapped the road line; moved to the shoulder, panes framed.

## Deviations from SPEC.md
1. Frames are 560 px wide, not 600, to keep three frames inside the 90% action-safe box.
2. Shot 1 steps sprite reels (640x320 JPEG sheets built by `tools/build_assets.py` from the PNGs); shots 2, 4, 11, 12, 16 and the end card use the original PNGs. The middle frame shows the clean twin (route-2640648) until the cross-cut.
3. Shot 2 holds the repeated pair 000040/000060 about 1.6 s (real pace would be 0.5 s at 4x).
4. Shot 7: the 896 slots are wrapped as 112 x 8, not one row (a single row is under 2 px per slot). Labelled "illustrative". The 32 lit slots are a seeded random pick.
5. Shot 8 raster of lit patterns is illustrative (labelled); the thumbnails are real frames of route-2640632 and route-2640642.
6. Shot 6 bars are from step 295; the nearest PNG (000300) is shown. Shot 12 bars are steps 190/195; the frames shown are the identical pair 000100/000120 (the 190/195 PNGs were not exported). The pairing is visual only.
7. Shot 9: "ten suspects" is drawn as a row of ten squares (my device); the group tiles are scattered in the pile, so no bracket could wrap them.
8. Shot 14: no P8 route or controls in the inputs, so no speed readout. The parked-car panes are a drawn schematic, labelled "illustrative". "1 s late" reads `delaySeconds` in data.js.
9. Shot 16: SPEC says "left and middle crashed drives"; the narration says two of the three drives crashed (middle and right), so orange "found" marks sit on those two.
10. Added from DATA, not listed in SPEC shots: "0.91 overlap" (P7) in orange; "4 other crashes" and "0 clean twins" under the 27 of 31; "tuned on all 738 drives" in shot 15.
11. Word timing is estimated (character-proportional with pauses anchored on ffmpeg silence detection), not a transcript. A whisper model download was not authorised. Cues land within about 0.3 s.
12. Pile tile marks for planted sets (hollow centre on the 53 P7 tiles) are my own ink marks, not orange.
13. In shot 15 the fresh-pile tiles fill grey (muted ink), standing for drives completed, not for crashes; the fill count is decorative.
14. No music, as instructed. Font: Archivo (latin woff2) from Google Fonts, downloaded into `assets/fonts/`.

## Not checked / weak
- Sound was measured, not heard. The draft voice is as supplied.
- Phone width (360 px): the 44 px labels and the tile grids are too small to read; only the display numbers, "27 of 31" and the end card survive. Kept because SPEC fixes 44 px body type.
- Weakest shots: pile-only openings of scenes D, F and G (a small pile in a large empty frame). With more time: scale the pile to about 1.6 in the side pose and move the Jaccard diagram below it.
- Several tweens use per-element GSAP stagger on 738 DOM tiles; rendering took 43 s, no issue.
- Seam gate speed-match ratio is 1.3 to 1.6 (sampled; inside its pass threshold).

## v2 layout pass
- Piles: full pile at scale 2.6 (about 1490 x 655 px, 31 px tiles) in scenes B (shot 4), E (scan) and G (tuned results). Where a pile shares a frame (B shots 4b/5, D, F) it is scale 1.5 (860 px wide) beside a hero that fills the rest of the width.
- Scene D: the 31-tile group is the hero (96 px tiles, 6 columns, about 590 px tall, thumbnails legible); "27 of 31" at 96 px; "0.57" orange at 220 px and "0.22" muted at 120 px on one baseline.
- Scene F: the 48-tile group uses the same 96 px tile. The slide now starts at "a second method" (about 96.0 s) and the group is fully formed by about 97.3 s (rings, slide and 8 x 6 grid; QA frame is at 98.0 s).
- Hook: frames stay 560 px (three at 600 do not fit the 90% box); the home row sits at top 370 so the row plus its labels is vertically centred.
- Scene G: two fresh piles of 20 x 10 tiles (38 px) side by side fill the 1728 px safe width; the rule card and verdict sit under them.
- P8 panes are 560 x 280 (same size as a real frame), 2 px ink lines, labelled "illustrative".
- End card: centred; frame 840 x 420, project line 44 px, link 56 px bold.
- Scene B: Jaccard circles enlarged (big circle 520 px across); catch-all number moved to x 1660.
- Scene E: the final scan now runs on a full-size pile after the rows exit (v1 shrank the rows above a small pile).
- Not changed: the three frames in the hook and scene G stay 560 px wide (26% of frame height); this is the one place the 40% hero rule is not met.
- v2 re-check: `check` 0 errors (same false-positive first_frame_empty), seam gate PASSED 7/7, render 1920x1080 30 fps 125.97 s.
