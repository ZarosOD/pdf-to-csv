"""Tests for the two output targets the demo tape declares.

This covers the demo layer rather than the shipped tool. It is here because of
a specific failure mode: vhs has been seen to exit 0 having written no file,
and it does that per output target. A run that produced the GIF and silently
skipped the MP4 would look like a success in every way a human checks — green
exit code, a clip on disk, a README that still renders — and the missing file
would only surface when somebody went to upload a portfolio cover and found
nothing there.

In this piece the output paths live in `demo/demo.tape` (`Output` lines) and
`record.sh` checks whatever the tape names. So the thing worth pinning down is
that those two stay in agreement: the tape declares both formats, record.sh
reads the declarations rather than a hardcoded list, and the committed clip
directory holds what the tape promised.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TAPE = REPO_ROOT / "demo" / "demo.tape"
RECORD_SH = REPO_ROOT / "demo" / "record.sh"

OUTPUT_LINE = re.compile(r"^\s*Output\s+(\S+)\s*$", re.MULTILINE)


def tape_outputs() -> list[str]:
    return OUTPUT_LINE.findall(TAPE.read_text())


def test_tape_declares_both_formats() -> None:
    """One tape, two Output lines: the GIF and the MP4 are the same recording.

    Two separate vhs runs would be two captures, and two captures of a typing
    animation are never identical. Declaring both in one tape is what makes
    "same content as the GIF" a property of the setup rather than a hope.
    """
    outputs = tape_outputs()
    assert sorted(outputs) == ["demo/out/demo.gif", "demo/out/demo.mp4"], outputs


def test_record_sh_checks_whatever_the_tape_names() -> None:
    """The check must be driven by the tape, not by a second hardcoded list.

    If someone adds a third Output line, record.sh should start checking it
    without being edited. A literal "demo.mp4" in the check would mean the
    tape and the verification can drift apart silently, which is the whole
    class of bug this file exists to prevent.
    """
    script = RECORD_SH.read_text()
    assert "Output" in script, "record.sh no longer reads the tape's Output lines"
    check = script[script.index("MISSING=0") :]
    assert "demo.mp4" not in check, "the check hardcodes a filename; read the tape"
    assert "demo.gif" not in check, "the check hardcodes a filename; read the tape"


def test_the_shell_extraction_agrees_with_the_tape() -> None:
    """Run record.sh's own extraction and compare it to what the tape says.

    Asserting on the regex above alone would only prove this test can read the
    tape. This runs the grep/awk pair record.sh actually uses, so a quoting or
    whitespace change in the shell is caught here rather than in a recording.
    """
    extract = (
        f"grep -E '^[[:space:]]*Output[[:space:]]' {TAPE} | awk '{{print $2}}'"
    )
    proc = subprocess.run(
        ["bash", "-c", extract], capture_output=True, text=True, check=True
    )
    from_shell = proc.stdout.split()
    assert sorted(from_shell) == sorted(tape_outputs())


def test_committed_clip_directory_holds_everything_the_tape_declares() -> None:
    """The deliverable itself, not the machinery that builds it.

    demo/out/ is committed on purpose, so this asserts the repo a client
    clones actually contains the portfolio cover.
    """
    for rel in tape_outputs():
        clip = REPO_ROOT / rel
        assert clip.is_file(), f"the tape declares {rel} but it is not committed"
        assert clip.stat().st_size > 0, f"{rel} is empty"
