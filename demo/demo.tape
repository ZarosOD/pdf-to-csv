# The terminal telling of the same story, for the VHS recipe.
# EDIT THIS FILE for a new piece that records a terminal.
#
#   DEMO_RECIPE=vhs DEMO_OUT_DIR=demo/out-terminal ./demo/record.sh
#
# Never run `vhs` against it by hand: the toolchain and the project setup are
# what record.sh puts in place first.
#
# Tape syntax: https://github.com/charmbracelet/vhs#vhs-command-reference

# There is no `Output` line on purpose: demo/record.sh passes `vhs -o` so the
# clip lands in whichever output directory it was asked for, and the Playwright
# clip in demo/out/ does not get overwritten. Running `vhs demo/demo.tape` by
# hand writes ./out.gif instead.

Set Shell bash
Set FontSize 16
Set Width 1180
Set Height 320
Set Padding 24
Set Framerate 24
Set TypingSpeed 28ms
Set Theme "Catppuccin Mocha"

# Setup that should not appear in the clip.
Hide
Type "export VIRTUAL_ENV_DISABLE_PROMPT=1 && source .venv/bin/activate && clear"
Enter
Sleep 1s
Show

# 1. Before: a folder of invoice PDFs from different vendors.
Type "ls samples/*.pdf"
Sleep 500ms
Enter
Sleep 3s

# 2. One command turns all of them into a CSV, and says what needs a human.
Type "python extract.py samples/ -o invoices.csv --report"
Sleep 500ms
Enter
Sleep 4s

# 3. After: the invoice-level fields.
Hide
Type "clear"
Enter
Show
Type "python demo/preview.py invoices.csv vendor invoice_number invoice_date subtotal tax total"
Sleep 500ms
Enter
Sleep 4500ms

# 4. And the line items underneath them.
Hide
Type "clear"
Enter
Show
Type "python demo/preview.py invoices.csv source_file description quantity unit_price line_total"
Sleep 500ms
Enter
Sleep 4500ms
