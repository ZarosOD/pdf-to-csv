# demo/ — the recording pipeline

One command regenerates the clip from scratch, headless, from a clean checkout:

```bash
./demo/record.sh
```

It writes `demo/out/demo.gif` **and** `demo/out/demo.mp4`, and fails loudly if
either is missing or empty, or if the clip runs longer than 35 seconds. No
screen capture, no window manager, no display server.

The two formats are for different places, and neither is generated from the
other — they are two encodes of the same captured frames, so they cannot drift
apart. The **GIF** is the README thumbnail: it animates inline on GitHub and
needs no player. The **MP4** is the portfolio cover, because Upwork's gallery
renders an uploaded GIF as a single static first frame. Both come from the
`Output` lines at the top of `demo.tape`; add or remove one there and
`record.sh` checks whatever the tape now names.

Terminal tools are recorded with [VHS](https://github.com/charmbracelet/vhs).
Anything with a browser or a web UI should use Playwright video instead; the
split is deliberate, VHS gives crisp text at small sizes and Playwright gives a
real page.

## Copying this into another piece

Copy the whole `demo/` folder. Then change **three files and nothing else**:

| File | What to change |
| --- | --- |
| `demo.tape` | The whole recipe: what gets typed, the pauses, the frame size. This is the piece. |
| `setup.sh` | How to get the project runnable — the venv, `npm ci`, a build, whatever. Must be re-runnable and must leave the repo ready for the tape. |
| `preview.py` | A display helper this piece happens to need. Delete it if yours does not. |

Leave `record.sh`, `lib/bootstrap.sh`, `lib/fetch.sh` and `lib/uv.sh` alone.
They are the generic parts: fetching a pinned toolchain into `demo/.toolchain/`,
running your setup, playing the tape, and checking the result.

If your piece is also Python, `setup.sh` can keep its two lines of `lib/uv.sh`
wiring as-is and you get the clean-machine bootstrap for free. If it is Node,
apply the same rule there: fetch a pinned toolchain into `demo/.toolchain/`
rather than assuming the machine has one.

## Writing the tape

`demo.tape` is [VHS tape syntax](https://github.com/charmbracelet/vhs#vhs-command-reference).
The conventions worth keeping:

- **Aim for 25 to 30 seconds.** `record.sh` rejects anything over 35.
- **Set the height to fit the tallest screen, not the tallest total.** Use
  `Hide` / `Type "clear"` / `Enter` / `Show` between beats. A short frame is
  much more readable in a proposal thumbnail than a tall one with dead space.
- **Hide the setup.** Activating a venv or exporting variables goes in a
  `Hide` block so it never appears in the clip.
- **`Sleep` after each `Enter`**, long enough to read the output. 3 to 4.5
  seconds is about right for a table.
- **Synthetic data only.** The tape runs against `samples/`, which is generated,
  never against anything real. Check every frame before shipping.

## Toolchain

`lib/bootstrap.sh` downloads into `demo/.toolchain/` (gitignored), nothing
system-wide and no root:

| Tool | Pin | Why |
| --- | --- | --- |
| vhs | 0.10.0 | Records the terminal. **Pinned deliberately**: 0.12.x starts Chromium, captures every frame, then exits 0 having written no file at all on some Linux hosts. 0.10.0 encodes reliably. |
| ttyd | 1.7.7 | The terminal vhs drives. A system `ttyd` is used if present. |
| ffmpeg | 7.0.2 | Encodes the frames. Checksum-verified against a constant in `bootstrap.sh`, so a swapped tarball fails loudly instead of quietly changing what the clip looks like — what the clip looks like is a function of the encoder, and palettegen defaults move between releases. A system `ffmpeg` is used only if it reports this same version; the vendored build wins over it. |

Every one of those downloads goes through `lib/fetch.sh`: a few attempts, a
widening gap between them, and a message that separates "the host is having a
moment" from "the URL is wrong". It exists because GitHub's release CDN returned
HTTP 500 on the ttyd asset for a couple of minutes on 2026-09-11 and took
`make demo` down with it. Failure is fatal for vhs, ttyd and ffmpeg — there is
no recording without them — and a fallback for uv, which can still try
`python3 -m venv`.

`lib/uv.sh` applies the same rule to the *project's* toolchain, because a clean
checkout is not a clean machine. Stock Ubuntu 24.04 has no `uv` and a `python3`
with no `ensurepip` (that lives in the separate `python3-venv` package), so
`setup.sh` used to stop dead there and take `make test`, `make run` and
`make demo` with it. It now fetches a pinned uv (0.12.13, checksum-verified
against the published `.sha256`) into `demo/.toolchain/bin`. uv then supplies the
interpreter too, so the machine does not need a python3.12 of its own. A system
`uv` is used if present; the system `python3 -m venv` is the fallback if the
fetch fails; the "install uv or python3-venv" error is the last resort.

VHS renders through a headless Chromium it downloads itself into `~/.cache/rod`.
On a server image that Chromium is usually missing a few shared libraries
(`libnss3`, `libnspr4`, `libasound2`). `bootstrap.sh` detects exactly which ones
are missing, fetches those `.deb`s with `apt-get download` (no root needed) and
unpacks them into `demo/.toolchain/sysroot`. On a non-Debian host it prints the
library names and stops instead of guessing.

`./demo/record.sh --clean` throws the toolchain away and re-fetches it, which is
how to verify the from-nothing path still works.

## Known limits

- x86_64 Linux. The pinned ttyd and ffmpeg URLs are architecture-specific;
  macOS would need `brew install vhs ttyd ffmpeg` and a small edit to
  `bootstrap.sh`.
- The first run downloads a headless Chromium into `~/.cache/rod`, which is most
  of the wait. Measured from a dead clone with an empty `HOME` and
  `PATH=/usr/bin:/bin`: about 75 s from nothing, about 47 s to re-record once
  the toolchain is there. The download is the variable, not the recording.
