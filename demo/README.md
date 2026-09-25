# demo/ — the recording pipeline

One command regenerates a clip from scratch, headless, from a clean checkout:

```bash
./demo/record.sh              # this piece: Playwright, a rendered page
./demo/record.sh --clean      # throw the toolchain away and re-fetch it first
```

No screen capture, no window manager, no display server, no root. Everything
the recording needs is fetched into `demo/.toolchain/` and nothing is installed
system-wide. `record.sh` fails loudly if the clip is missing, empty, or longer
than 35 seconds.

It writes `demo/out/demo.gif` **and** `demo/out/demo.mp4`. The two formats are
for different places, and neither is generated from the other — they are two
encodes of the same captured frames, so they cannot drift apart. The **GIF** is
the README thumbnail: it animates inline on GitHub and needs no player. The
**MP4** is the portfolio cover, because Upwork's gallery renders an uploaded GIF
as a single static first frame.

**This piece was the last one on the old pipeline.** It shipped before
`demo/lib/` was split into recipes, so it carried a single `lib/bootstrap.sh`
that fetched vhs, ttyd and ffmpeg, and a `record.sh` that played a tape rather
than picking a recipe. Seven declared exceptions in the maintainers' drift
checker existed to say so. It now carries the same `record.sh` and the same
`lib/` as the other three, `bootstrap.sh` is gone, and those seven exceptions
are gone with it — an exception whose reason has been fixed is not a note, it
is a hole that will excuse the next real difference.

## The spreadsheet renderer, `lib/sheet.py`

All four pieces end their clip on the file the run just wrote, open in a
spreadsheet grid. That is one job, so it is one file — shared, byte-identical
everywhere, and policed like the rest of `lib/` by a drift checker that lives
in the maintainers' working tree and does not ship inside this repo.
What stays per-piece is `scene.py`: which files this piece opens, which of its
columns are worth showing, and what the narration says.

**It cannot render a table it was handed.** The only way in is
`read_table(path)` or `read_dir(path)`, both of which open something real and
raise if it is not there. `View` cannot be built without a `Table` and `Table`
cannot be built without a file on disk. That is deliberate: a terminal ASCII
table cannot be told apart from a mock-up, and a renderer that reads a fixture
reproduces exactly that flaw with better borders.

**A filtered view says it is filtered.** Showing ten of fifteen columns is fine
and is normal — nobody wants fifteen on screen. So the columns keep the letter
they have in the source file (picking columns 1, 2, 4 and 9 renders as A, B, D,
I, which is what hiding columns in Excel looks like), rows keep their real sheet
row number so a filtered set reads 2, 3, 4, 66, 67 with the join marked, and the
footer says how many of each are on screen out of how many are in the file.

**The number format is honoured.** A price cell holding 1299 with a `0.00`
format reads "1299.00" in Excel and "1299" if you only look at the value —
while a CSV beside it would say "1299.00". Rendering the value alone would put a
difference on screen that does not exist in the file.

**The command and its output come from one call.** `run_command` runs the argv,
keeps the captured stdout with it, and `terminal_html` renders that one object —
so the line on screen cannot drift from the output underneath it. The
interpreter path is the one thing rewritten, to `python`, because
`/home/somebody/repo/.venv/bin/python3.12` is machine-specific noise and not the
thing being demonstrated.

Covered by `tests/test_demo_sheet.py`, which is byte-identical in all four repos
for the same reason the module is.

## The title card, `lib/card.py`

Every clip opens on 0.8 s of dark frame: this piece's before artifact on the
left under a white label, its after artifact on the right under a green one,
one line of specifics beneath each. The same render is exported beside the
clips as `demo/out/poster.png`, for a platform that wants a cover image rather
than a video.

It exists because frame 0 is a thumbnail. Freelancer derives a video's poster
from frame 0, and this README embeds the `.gif`, whose first frame is what a
reader sees before deciding whether to press play. Frame 0 used to be a
spreadsheet on pale paper, which at that size is a blank white rectangle
(THE-285).

**The two panels are the run's own frames.** `Scene.panel` screenshots whatever
is on screen at that beat, so there is no artwork to go stale: change the
fixture and the card follows it exactly the way the clip does. It is generated
for the same reason the clip is — a hand-made card is correct once.

**The generator is shared and the captions are not.** `lib/card.py` draws it
and is byte-identical in all four repos; the two labels and the two detail
lines are in `scene.py`, built out of tables the scene has already read, so no
number on the card is missing from the clip behind it. Each string is
auto-sized to fit its half, and one that still does not fit at the smallest
size allowed stops the recording rather than being ellipsised in front of a
client.

**The face is vendored, and the machine's own fonts are put out of reach.**
Auto-sizing makes the metrics load-bearing — the same HTML against a different
face is a different card, and on a box with neither Ubuntu nor DejaVu it is a
label overhanging the divider. So `lib/fonts.sh` fetches a pinned DejaVu,
checks it against a literal sha256, and writes a fontconfig declaring that one
directory and pulling in no system config; the card gets its own Chromium with
`FONTCONFIG_FILE` pointing at it. `card.font_probe` proves that rather than
asserting it: it measures one string under three family names, one of which is
a family that exists nowhere, and under that config all three come back the
same width because there is one face left to resolve to.
`tests/test_demo_card.py` runs it both ways, because without the control arm
the same check would pass on a machine with no fonts installed at all.

**That check does not run under a plain `make test`, and a green suite is not
it passing.** It needs three variables only `lib/playwright.sh` exports, so
under a bare pytest it skips — and on the summary line a skip and a pass are
the same word-shape. `./demo/record.sh` runs it by construction, and the skip
message names the exact command otherwise. Measured on 2026-09-24: jailed, the
three probe families come back `[683, 683, 683]`; with the jail lifted on the
same box, `[678.9, 563.7, 683]`. The other checks in that file — the card in
the GIF, the card in the mp4, the poster matching frame 0 — do run under `make
test`, and the GIF one needs nothing but the standard library.

The recording's own Chromium is untouched. The scene frames are drawn with the
system stack `lib/sheet.py` names and are unchanged by this: the card is a
prepend and an export, not a re-cut.

## Which recipe

**All four pieces use Playwright today**, and the reason is the grid above: a
spreadsheet frame is a rendered page, and the terminal recipe cannot draw one.
This piece records a browser twice over: it opens on a real page of a sample PDF
and closes on `invoices.xlsx` in the grid — the workbook the run wrote, read
back through openpyxl. The VHS sibling is still live in every
repo — `make demo-terminal` — because the choice is the point of `demo/recipe`
and a recipe nobody can run is a recipe that has rotted.

| | **VHS** (`lib/vhs.sh`) | **Playwright** (`lib/playwright.sh`) |
| --- | --- | --- |
| Records | A terminal session | A real browser page |
| You write | `demo.tape` — a script of keystrokes and pauses | `scene.py` — Playwright code |
| Good at | Crisp text at small sizes; small files | Anything with a UI, a page, a document or a grid |
| Bad at | Anything that is not text in a terminal | Files are several times bigger |
| Timing | Declarative `Sleep 4s` | `page.wait_for_timeout(4000)` — same idea, in Python |
| Output | GIF **and** MP4, from one recording | GIF **and** MP4, from one recording |

## The scene

`scene.py` is four beats, in the shape all four clips share — a BEFORE, one
command, and an AFTER that is held long enough to read:

1. **BEFORE** `samples/`, listed off disk: twelve PDFs from twelve vendors.
2. **BEFORE** one of them, rendered. The listing says there are twelve
   documents; this says what a document looks like, and it is the frame that
   makes "no per-vendor templates" mean something.
3. **The command**, and the real stdout it printed.
4. **AFTER** `invoices.xlsx` in the grid, with the flagged rows on screen. One
   run writes the workbook and `invoices.csv` from the same rows; the clip
   shows the one a client double-clicks.

Beat 2 renders the page with `pypdfium2`, which `pdfplumber` already brings in,
so it adds no dependency the piece did not have. A4 is 1:1.41 and the frame is
16:9, so a whole page fits at about a third of the width and nothing on it can
be read — the margins are cropped away, and if it is still too tall the bottom
goes and **the caption says so**. A cropped page presented as a whole one is
exactly the kind of small lie this clip exists to avoid.

## Copying this into another piece

Copy the whole `demo/` folder. Then change **these files and nothing else**:

| File | What to change |
| --- | --- |
| `recipe` | One word: `playwright` or `vhs`. |
| `setup.sh` | Two lines in practice: the import names you pass `ensure_venv`, and whatever the piece needs regenerated before recording. A non-Python piece replaces the `ensure_venv` call with its own build. Anything it deletes belongs under `--fresh` unless the piece itself owns it — every `make` target runs this file, so a wipe outside that flag is a wipe of the user's work. |
| `scene.py` | The Playwright recipe's script: which files to open, which columns to show, what the narration says, and the two labels and two detail lines of the title card. The rendering is `lib/sheet.py` and `lib/card.py` and is not yours to edit. |
| `demo.tape` | The VHS recipe's tape. Delete it if you only want the browser one. |

Leave `record.sh` and everything in `lib/` alone. If you find yourself editing
one of those to make your piece work, the split is wrong — fix the split, do not
fork the file. A drift checker in the maintainers' working tree says whether
you did; it is not part of this repo, so there is nothing here for you to run.

## Toolchain

Everything lands in `demo/.toolchain/` (gitignored). Nothing system-wide, no
root, versions pinned except where noted.

| File | Fetches | Pin | Why pinned |
| --- | --- | --- | --- |
| `lib/fetch.sh` | nothing itself | — | Every download below goes through it: a few attempts, a widening gap, and a message that separates "the host is having a moment" from "the URL is wrong". It exists because GitHub's release CDN returned HTTP 500 on the ttyd asset for a couple of minutes on 2026-09-11 and took `make demo` down with it. |
| `lib/uv.sh` | uv | 0.12.13 | Checksum-verified against the published `.sha256`. |
| `lib/python-venv.sh` | nothing directly | — | The venv ladder. Calls `lib/uv.sh` when the machine has no uv. |
| `lib/ffmpeg.sh` | ffmpeg, ffprobe | 7.0.2 | Checksum-verified against a constant in the file, so a swapped tarball fails instead of quietly changing what the clip looks like — palettegen defaults move between releases. A system `ffmpeg` is used only if it reports the same version. |
| `lib/playwright.sh` | the `playwright` wheel + Chromium | 1.47.0 | The recipe this piece records with. Playwright for *Python*, not Node: the wheel ships its own driver, so a machine with no Node can still regenerate the clip. |
| `lib/vhs.sh` | vhs, ttyd | 0.10.0, 1.7.7 | The terminal sibling. **vhs deliberately**: 0.12.x starts Chromium, captures every frame, then exits 0 having written no file at all on some Linux hosts. 0.10.0 encodes reliably. |
| `lib/chromium-libs.sh` | the shared objects Chromium links against | — | See below. |

`lib/uv.sh` applies the pinning rule to the *project's* toolchain, because a
clean checkout is not a clean machine. Stock Ubuntu 24.04 has no `uv` and a
`python3` with no `ensurepip` (that lives in the separate `python3-venv`
package), so `setup.sh` would stop dead there and take `make test`, `make run`
and `make demo` with it. It fetches a pinned uv into `demo/.toolchain/bin`, and
uv then supplies the interpreter too, so the machine does not need a Python 3.12
of its own.

Both recipes end up driving a headless Chromium, and on a server image that
browser is missing the desktop libraries it links against. `playwright
install-deps` and `apt-get install` both want root, which a demo script has no
business asking for. So `lib/chromium-libs.sh` runs `ldd`, works out exactly
which `.so` files are missing, fetches those `.deb`s with `apt-get download` (no
root) and unpacks them into `demo/.toolchain/sysroot`. It loops up to three
times, because unpacking one library reveals the next one down. On a non-Debian
host it prints the library names and stops rather than guessing.

## Known limits

- **x86_64 Linux.** The pinned ttyd and ffmpeg URLs are architecture-specific.
  macOS would need `brew install vhs ttyd ffmpeg` and a small edit.
- **The first run downloads a browser.** Measured on the machine this was
  recorded on: about 23 s to re-record once the toolchain is there (22.8, 22.8,
  22.8 over three runs), and the first run adds the Chromium download on top,
  which has not been timed — the download is the variable, not the recording.
  What `make demo` leaves is 762 MB, 549 MB of it the unpacked Chromium, all
  inside the repo; `make demo-terminal` adds 24 MB more to the same directory
  and a second Chromium under `~/.cache/rod`, which is outside it. `make clean`
  removes `demo/.toolchain/`, not `~/.cache/rod`.
- **Synthetic data only.** Every invoice, vendor and customer in the clip is
  invented and comes out of `samples/generate_samples.py`. Check every frame
  before shipping.
