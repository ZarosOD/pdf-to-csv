# demo/ — the recording pipeline

One command regenerates the clip from scratch, headless, from a clean checkout:

```bash
./demo/record.sh
```

It writes `demo/out/demo.gif` and fails loudly if the clip is missing, empty, or
longer than 35 seconds. No screen capture, no window manager, no display server.

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

Leave `record.sh` and `lib/bootstrap.sh` alone. They are the generic parts:
fetching a pinned toolchain into `demo/.toolchain/`, running your setup, playing
the tape, and checking the result.

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
| ffmpeg | static build | Encodes the frames. A system `ffmpeg` is used if present. |

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
- First run downloads roughly 200 MB (Chromium) and takes a few minutes. Later
  runs take about 40 seconds.
