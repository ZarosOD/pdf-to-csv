# The recipe for this portfolio piece's clip. This is the file you rewrite for
# a new piece; demo/record.sh and demo/lib/bootstrap.sh stay as they are.
#
# Played by: ./demo/record.sh   (never run `vhs` against it by hand, the
# toolchain and the project setup are what record.sh puts in place first)
#
# Tape syntax: https://github.com/charmbracelet/vhs#vhs-command-reference

Output demo/out/demo.gif

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
