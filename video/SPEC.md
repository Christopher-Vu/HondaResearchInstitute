# SPEC: One road, three drives

GOAL:    the viewer can say, in their own words, how a tool that never sees the answer found two planted camera
         faults by reading a driving model's insides, and why the third still hides.
OUTPUT:  HyperFrames, 1920 x 1080, 30 fps.
TIME:    narrated; the voice is the clock. 16 narration clips (below) plus a 4 s end card. Expected 105 to 125 s.
         Each scene's duration = its clip's length + 0.35 s of air; shot frame ranges follow from the clips.

## LOOK

- Ground: concrete grey #D8D8D4 with 3% monochrome grain (static noise texture, opacity 0.03). No gradients.
- Ink: #1B1C1E for every word and every structural line (2 px at 1080).
- Accent: safety orange #FF5A1F. It may appear ONLY on what the tool finds: the found group's outline, the
  found tiles, the overlap region in the Jaccard diagram, and the one number that is the payoff in a scene. It
  never fills a button or a background.
- Secondary ink: #6B6E72 for numbers that are context (the baseline 0.22, the catch-all 0.2).
- Type: Archivo (Google Fonts, variable, wdth 62 to 125, wght 100 to 900), downloaded as woff2 into
  `assets/fonts/` with @font-face. Display: wght 800, wdth 112, 96 px, tracking 0 (never touch tracking).
  Body lines on screen: wght 500, wdth 100, 44 px. Numbers that align in a table: Archivo with
  `font-variant-numeric: tabular-nums`, not a monospace. Sentence case everywhere; no all-caps.
- Medium: the real CARLA camera frames (`assets/frames/route-*/NNNNNN.png`, 1024 x 512, what the model saw,
  after the fault). They are the only photographs. They sit in a frame with a 1 px #1B1C1E edge and square
  corners (no radius), with a soft contact shadow 0 12 px 32 px rgba(0,0,0,0.18).
- Diagrams are drawn in ink on the grey ground: tiles, circles, lines. No icons on coloured squares.

## OBJECTS

- **The road**: base route 26406, Town04 highway. Three drives of it:
  clean `route-2640642` (succeeded), black patch `route-2640632` (crashed into a vehicle), frozen
  `route-2640638` (crashed). Frames every 20 policy steps (1 s). In the frozen drive, frames 000040 and 000060
  are byte-identical, as are 000100 and 000120, 000160 and 000180, 000220 and 000240: show the repeat by holding.
- **The pile**: 738 small square tiles (12 px, 2 px gap) in a grid; 278 crashed tiles in ink, 460 fine tiles
  as outlines. Planted crashes: P4 43, P7 53, P8 58. The found P4 group: 31 tiles, of which 27 are P4 crashes and
  4 are other pilots' crashes. The found P7 group: 48 tiles, all P7 crashes.
- **The model's insides**: a column of 896 thin bars (the layer-10 numbers for one frame), drawn from the real
  frame mean of one shard if available, else drawn as illustrative and labelled "illustrative".
- **The dictionary**: the 896 numbers re-expressed as a few lit patterns out of a row of 896 slots (the SAE
  has expansion 1, so 896 patterns, k of them on per frame: show k = 32 lit).
- **The Jaccard diagram**: two circles, "the tool's answer" and "the truth"; overlap in orange; the fraction
  overlap / everything shown as a number.

## Narration (exact text; voice reads it; the screen never repeats it word for word)

1. This is one stretch of highway, driven three times by the same self-driving model, and it crashed twice.
2. Before the second drive we blacked out the middle of its camera. Before the third, we made the picture freeze
   for two seconds out of every three.
3. We planted those failures on purpose, so we already know the answer. The question is whether a tool can work
   it out without being told.
4. So we hid those drives in a pile of 738. It holds 278 crashes, and each planted fault is only about a fifth
   of them.
5. We score a tool by how much its answer overlaps the truth. A tool that simply answers "every crash" scores
   about one in five.
6. Our tool never looks at the answer. It reads the model's insides: the 896 numbers it computes for each frame
   it sees.
7. First it learns a dictionary of the patterns those numbers tend to form, the way a language has words.
8. Then it asks which patterns switch on in the three seconds before a crash and stay off when a drive goes fine.
9. Among its ten suspects was a group of 31 crashed drives. 27 of them had the blacked-out camera, and none were
   the clean twins.
10. That is an overlap of 0.57. The best tool that ignores the model's insides managed 0.22.
11. The frozen camera got past it. A frozen frame is still a normal picture of the road, only an old one.
12. There was one clue. When the car is stopped and the picture is frozen, the model's numbers repeat exactly,
    and that happens nowhere else in the pile.
13. We added that one signal, "nothing changed since the last frame", and a second method pulled out 48 frozen
    drives with no mistakes.
14. A one-second delay is still hidden. The cars it breaks end up parked, and a parked car cannot show that it
    sees late.
15. We tuned these methods after seeing the data, and that is not proof. Both faults were then driven again on
    fresh roads, with the rules written down first. The overlaps came back at 0.56 and 0.89.
16. Reading the model's insides told us why two of these three drives crashed.

## MOTION

- Enter: power2.out over 18 frames. Move: power3.inOut over 24 frames. Exit: power2.in over 12 frames.
  Camera (the whole stage scaling or panning): power2.inOut over 36 frames. No springs on text.
- One hero move per shot; secondary moves travel 60% as far and start 4 to 6 frames later.
- Text lands on the word that names it and then holds still until it leaves. Nothing breathes or floats.
- Frames "drive" by stepping through the real PNG sequence at 1 frame per second of drive time sped up 4x
  (one PNG every 7.5 video frames); the frozen drive holds where its PNGs repeat.

## SHOTS (durations follow the narration clips)

1. Home stage: three frames side by side, each 600 px wide, all three driving (PNG steps). On "crashed twice"
   the middle and right frames get a 2 px ink rule under them and the word "crashed" in body type (ink, not
   orange: the tool has not found anything yet).
2. Push in on the middle frame: a black rectangle appears exactly as in the real frame (the PNG already has it;
   reveal it by cross-cutting from the clean frame). Pan to the right frame: it steps, then holds through a
   repeated pair (000040/000060), with a small ink clock showing "2 s frozen".
3. Pull back to all three. The two crashed drives get the words "we did this" in body type beside them.
4. The three frames shrink into three tiles and fly into the pile of 738; the grid fills. 278 tiles turn ink.
5. The Jaccard diagram grows next to the pile: answer circle, truth circle, overlap; then the "every crash"
   answer is drawn as a huge circle swallowing the truth: number 0.2 in secondary ink.
6. Back to one clean frame; from it, a column of 896 thin bars unrolls to the right (the model's numbers).
7. The column re-folds into a row of 896 slots with 32 lit (the dictionary). Lit slots in ink.
8. A timeline strip of one crashed drive with its last 3 s shaded; slots light in that window. A clean drive's
   strip below stays dark.
9. Payoff: in the pile, 31 tiles get orange outlines and slide out into their own group; 27 of them carry the
   tiny black-patch thumbnail. Their clean twins in the pile stay unmarked.
10. Number lands: 0.57 in orange, 96 px; 0.22 beside it in secondary ink.
11. The frozen frame again: it holds; beside it, the clean frame from the same moment. They look alike.
12. Two consecutive frozen frames side by side and their 896-bar columns: identical; an "=" lands between them.
13. In the pile, 48 tiles get orange outlines and group; every one is a P7 crash.
14. A P8 tile: the car parked; a small speed readout at 0 m/s (from `controls.jsonl` of a P8 slice route, else
    omit). The tile stays unmarked.
15. Two new empty piles appear labelled "fresh P4 drives" and "fresh P7 drives", filling slowly; the rule card
    "written before the data" in body type. The fresh scores land in orange: 0.56 (best of 18 dictionaries, median
    0.41) and 0.89 (48 drives, none wrong).
16. Home stage returns: three frames; the left and middle crashed drives now carry orange "found" marks; the
    right one (if P8 ever shown) none. Line on screen: "two of three faults found".
End card (4 s): project line "SimLingo failure discovery, Honda Research Institute" and the link
https://github.com/trycua/cua set in body type, held 3 s.

## DATA (one module, `data.js`; every number on screen reads from it)

pool 738, failures 278, keys {P4: 43, P7: 53, P8: 58}, catch_all ~0.2 (0.155 to 0.209), P4 found group 31 with
27 in key, P4 jaccard 0.574, best baseline 0.219, P7 found group 48 with 48 in key, P7 jaccard 0.906,
dictionary size 896, k shown 32, window 3 s, fresh P4 0.557 (median 0.405 of 18), fresh P7 0.889 (48 drives).

## BANNED

The spec.md defaults (dark void, glow, gradients, glass, cream paper with serif, centred everything, fade-and-
slide-up on everything, text moving while read, corner labels, HUD readouts, three cards in a row, docked logo),
plus: all-caps text, letter-spacing changes, monospace as decoration, icons on coloured rounded squares, rounded
corners with a visible border, orange on anything the tool did not find, any number not in `data.js`.

## QA

Check frames at: the hook's first frame (three real frames visible, not black); the frozen hold (two identical
frames held); the pile with 278 ink tiles; the payoff (31 orange-outlined tiles separated); the 0.57 landing; the
48 P7 group; the end card with the full Cua URL readable.
