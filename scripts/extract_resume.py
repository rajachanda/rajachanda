from pypdf import PdfReader
import re
import sys

pdf_path = sys.argv[1]
reader = PdfReader(pdf_path)
text = []
for p in reader.pages:
    try:
        text.append(p.extract_text() or "")
    except Exception:
        text.append("")
full = "\n".join(text)

# Simple section extraction by headings
headings = ['Contact', 'Objective', 'Summary', 'Education', 'Experience', 'Internship', 'Projects', 'Skills', 'Certifications', 'Achievements', 'Honors', 'Awards']

lines = full.splitlines()

sections = {}
current = 'Summary'
sections[current] = []
for ln in lines:
    s = ln.strip()
    if not s:
        continue
    # detect heading lines
    if any(re.match(rf'^{h}\b', s, re.IGNORECASE) for h in headings):
        current = s
        sections[current] = []
    else:
        sections.setdefault(current, []).append(s)

# Build markdown summary
out_lines = ["# Resume Summary\n"]
for k, v in sections.items():
    out_lines.append(f"## {k}\n")
    snippet = '\n'.join(v[:10])
    out_lines.append(snippet + "\n")

summary_md = "\n".join(out_lines)
with open('resume_summary.md', 'w', encoding='utf-8') as f:
    f.write(summary_md)

print('Wrote resume_summary.md')
