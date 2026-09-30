"""
IBVAP Master Model Stack Inventory PDF Generator
Converts master_stack_inventory_full.md into a high-fidelity HTML document
and renders it into a publication-grade PDF via Headless Microsoft Edge.
"""

import os
import re
import subprocess
import sys

def parse_markdown_to_html(md_path):
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pre-process LaTeX equations
    # Block math $$ ... $$
    def replace_block_math(match):
        eq = match.group(1).strip()
        return f'<div class="formula-box"><span class="formula-label">Dynamic Routing Formulation:</span><div class="math-display">{eq}</div></div>'
    content = re.sub(r'\$\$(.*?)\$\$', replace_block_math, content, flags=re.DOTALL)

    # Inline math $ ... $
    content = re.sub(r'\$(.*?)\$', r'<span class="math-inline">\1</span>', content)

    # Process tables
    lines = content.split('\n')
    html_lines = []
    in_table = False
    table_rows = []
    in_code_block = False
    code_lines = []

    for line in lines:
        stripped = line.strip()

        # Handle Code blocks
        if stripped.startswith('```'):
            if in_code_block:
                in_code_block = False
                code_text = "\n".join(code_lines)
                html_lines.append(f'<div class="ascii-diagram-card"><pre><code>{code_text}</code></pre></div>')
                code_lines = []
            else:
                in_code_block = True
                code_lines = []
            continue

        if in_code_block:
            code_lines.append(line)
            continue

        # Handle Markdown Tables
        if stripped.startswith('|') and stripped.endswith('|'):
            # Check if separator row like |:---|:---|
            if re.match(r'^\|[\s\-:]+(\|[\s\-:]+)+\|$', stripped):
                continue
            cells = [c.strip() for c in stripped.strip('|').split('|')]
            if not in_table:
                in_table = True
                table_rows = [cells]
            else:
                table_rows.append(cells)
            continue
        else:
            if in_table:
                # Flush table
                html_lines.append(render_table(table_rows))
                in_table = False
                table_rows = []

        # Handle Headers
        if stripped.startswith('# '):
            title = stripped[2:].strip()
            # Handled in custom cover / top header
            continue
        elif stripped.startswith('## '):
            h2 = stripped[3:].strip()
            html_lines.append(f'<h2 class="section-title"><span class="section-badge">Section</span> {h2}</h2>')
            continue
        elif stripped.startswith('### '):
            h3 = stripped[4:].strip()
            html_lines.append(f'<h3 class="subsection-title">{h3}</h3>')
            continue

        # Handle blockquotes
        if stripped.startswith('> '):
            quote = stripped[2:].strip()
            if quote.startswith('[!NOTE]'):
                html_lines.append('<div class="note-box"><div class="note-title">CRITICAL FIT METRIC DEFINITION</div>')
            elif quote.startswith('[!IMPORTANT]') or 'Core System Doctrine' in quote:
                html_lines.append('<div class="doctrine-box">')
            else:
                html_lines.append(f'<p class="quote-text">{quote}</p>')
            continue

        # Handle numbered lists
        num_match = re.match(r'^(\d+)\.\s+\*\*(.*?)\*\*(.*)', stripped)
        if num_match:
            idx, bold_title, rest = num_match.groups()
            html_lines.append(f'<div class="list-item"><span class="list-idx">{idx}</span><div class="list-content"><strong>{bold_title}</strong>{rest}</div></div>')
            continue

        # Handle bullet lists
        if stripped.startswith('- '):
            bullet_text = stripped[2:].strip()
            html_lines.append(f'<div class="bullet-item"><span class="bullet-dot">&#9656;</span><div class="bullet-content">{bullet_text}</div></div>')
            continue

        # Handle horizontal rule
        if stripped in ['---', '***', '___']:
            html_lines.append('<hr class="divider"/>')
            continue

        # Regular text or empty line
        if stripped == '':
            html_lines.append('<div class="spacer"></div>')
        else:
            # Bold & italic replacements
            formatted = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', stripped)
            formatted = re.sub(r'\*(.*?)\*', r'<em>\1</em>', formatted)
            formatted = re.sub(r'`(.*?)`', r'<code class="inline-code">\1</code>', formatted)
            html_lines.append(f'<p class="para">{formatted}</p>')

    if in_table:
        html_lines.append(render_table(table_rows))

    return "\n".join(html_lines)


def render_table(rows):
    if not rows:
        return ""
    header = rows[0]
    data = rows[1:]

    html = ['<div class="table-container"><table class="data-table"><thead><tr>']
    for col in header:
        col_clean = re.sub(r'\*\*(.*?)\*\*', r'\1', col)
        html.append(f'<th>{col_clean}</th>')
    html.append('</tr></thead><tbody>')

    for row_idx, row in enumerate(data):
        cls = "row-even" if row_idx % 2 == 0 else "row-odd"
        html.append(f'<tr class="{cls}">')
        for i, cell in enumerate(row):
            # Format cell content
            cell_fmt = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', cell)
            cell_fmt = re.sub(r'`(.*?)`', r'<code class="inline-code">\1</code>', cell_fmt)
            cell_fmt = re.sub(r'\*(.*?)\*', r'<em>\1</em>', cell_fmt)

            # Execution mode badges
            if "Continuous (30 FPS)" in cell:
                cell_fmt = cell_fmt.replace("Continuous (30 FPS)", '<span class="badge badge-emerald">Continuous (30 FPS)</span>')
            elif "Triggered" in cell:
                cell_fmt = cell_fmt.replace("Triggered", '<span class="badge badge-blue">Triggered</span>')
            elif "Escalation" in cell:
                cell_fmt = cell_fmt.replace("Escalation", '<span class="badge badge-amber">Escalation</span>')
            elif "Asynchronous" in cell or "Async" in cell:
                cell_fmt = cell_fmt.replace("Asynchronous", '<span class="badge badge-purple">Asynchronous</span>').replace("Async", '<span class="badge badge-purple">Async</span>')
            elif "RESTRICTED" in cell:
                cell_fmt = cell_fmt.replace("RESTRICTED", '<span class="badge badge-red">RESTRICTED</span>')

            # Fit percentage badge
            fit_match = re.search(r'<strong>(\d+%)</strong>', cell_fmt)
            if fit_match:
                pct = fit_match.group(1)
                num = int(pct.replace('%', ''))
                badge_class = "pct-high" if num >= 90 else ("pct-med" if num >= 80 else "pct-low")
                cell_fmt = cell_fmt.replace(fit_match.group(0), f'<span class="fit-badge {badge_class}">{pct}</span>')

            # Alignments
            align = "center" if "%" in cell or len(cell) < 15 and i in [3, 4] else "left"
            html.append(f'<td style="text-align: {align};">{cell_fmt}</td>')
        html.append('</tr>')

    html.append('</tbody></table></div>')
    return "\n".join(html)


def build_full_html(body_html):
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>IBVAP Master Model Stack Inventory & Architecture Blueprint</title>
<style>
  @page {{
    size: A4 portrait;
    margin: 14mm 14mm 16mm 14mm;
    @bottom-left {{
      content: "IBVAP — Intelligent Border Video Analytics Platform | SIH 26187";
      font-family: 'Segoe UI', Arial, sans-serif;
      font-size: 8pt;
      color: #64748b;
    }}
    @bottom-right {{
      content: "Page " counter(page) " of " counter(pages);
      font-family: 'Segoe UI', Arial, sans-serif;
      font-size: 8pt;
      color: #64748b;
      font-weight: 600;
    }}
  }}

  * {{
    box-sizing: border-box;
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }}

  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 9pt;
    line-height: 1.42;
    color: #1e293b;
    background: #ffffff;
    margin: 0;
    padding: 0;
  }}

  /* Executive Header */
  .cover-banner {{
    background: linear-gradient(135deg, #091e3a 0%, #1e3a8a 50%, #1e40af 100%);
    color: #ffffff;
    padding: 22px 24px;
    border-radius: 8px;
    margin-bottom: 20px;
    border-left: 6px solid #f59e0b;
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.15);
  }}

  .gov-badge {{
    display: inline-block;
    background: rgba(245, 158, 11, 0.2);
    color: #fbbf24;
    font-size: 7.5pt;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    padding: 3px 10px;
    border-radius: 4px;
    border: 1px solid rgba(245, 158, 11, 0.4);
    margin-bottom: 8px;
  }}

  .doc-title {{
    font-size: 17pt;
    font-weight: 800;
    line-height: 1.25;
    margin: 4px 0 6px 0;
    letter-spacing: -0.3px;
  }}

  .doc-subtitle {{
    font-size: 10pt;
    font-weight: 400;
    color: #cbd5e1;
    margin-bottom: 14px;
    line-height: 1.35;
  }}

  .meta-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
    background: rgba(15, 23, 42, 0.4);
    padding: 10px 14px;
    border-radius: 6px;
    font-size: 8pt;
    border: 1px solid rgba(255, 255, 255, 0.1);
  }}

  .meta-item strong {{
    display: block;
    color: #94a3b8;
    font-size: 7pt;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 2px;
  }}

  .meta-item span {{
    color: #f8fafc;
    font-weight: 600;
  }}

  /* Doctrine Box */
  .doctrine-box {{
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-left: 4px solid #2563eb;
    padding: 12px 16px;
    border-radius: 6px;
    margin-bottom: 18px;
  }}

  .doctrine-box em {{
    font-style: italic;
    color: #1e293b;
    font-size: 9.5pt;
    line-height: 1.45;
    display: block;
  }}

  .doctrine-title {{
    font-size: 8pt;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #2563eb;
    margin-bottom: 4px;
  }}

  /* Note Box */
  .note-box {{
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 6px;
    padding: 10px 14px;
    margin: 14px 0;
    font-size: 8.5pt;
    color: #1e40af;
  }}

  .note-title {{
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-size: 7.5pt;
    margin-bottom: 4px;
    color: #1d4ed8;
  }}

  /* Section Titles */
  .section-title {{
    font-size: 13pt;
    font-weight: 700;
    color: #0f172a;
    border-bottom: 2px solid #e2e8f0;
    padding-bottom: 6px;
    margin-top: 24px;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    page-break-after: avoid;
  }}

  .section-badge {{
    background: #1e293b;
    color: #ffffff;
    font-size: 7.5pt;
    font-weight: 700;
    padding: 2px 7px;
    border-radius: 3px;
    margin-right: 8px;
    text-transform: uppercase;
  }}

  .subsection-title {{
    font-size: 10.5pt;
    font-weight: 700;
    color: #1e3a8a;
    margin-top: 16px;
    margin-bottom: 8px;
    padding-left: 6px;
    border-left: 3px solid #3b82f6;
    page-break-after: avoid;
  }}

  /* Tables */
  .table-container {{
    margin: 10px 0 16px 0;
    overflow-x: auto;
    page-break-inside: avoid;
  }}

  .data-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 8pt;
    text-align: left;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  }}

  .data-table th {{
    background: #1e293b;
    color: #ffffff;
    font-weight: 600;
    padding: 6px 8px;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    font-size: 7.2pt;
    border: 1px solid #334155;
  }}

  .data-table td {{
    padding: 5px 8px;
    border: 1px solid #e2e8f0;
    vertical-align: middle;
  }}

  .row-even {{
    background: #ffffff;
  }}

  .row-odd {{
    background: #f8fafc;
  }}

  /* Badges */
  .badge {{
    display: inline-block;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 7pt;
    font-weight: 700;
    text-transform: uppercase;
    white-space: nowrap;
  }}

  .badge-emerald {{ background: #d1fae5; color: #065f46; border: 1px solid #a7f3d0; }}
  .badge-blue {{ background: #dbeafe; color: #1e40af; border: 1px solid #bfdbfe; }}
  .badge-amber {{ background: #fef3c7; color: #92400e; border: 1px solid #fde68a; }}
  .badge-purple {{ background: #ede9fe; color: #5b21b6; border: 1px solid #ddd6fe; }}
  .badge-red {{ background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }}

  .fit-badge {{
    display: inline-block;
    padding: 2px 7px;
    border-radius: 12px;
    font-size: 7.5pt;
    font-weight: 800;
    min-width: 38px;
    text-align: center;
  }}

  .pct-high {{ background: #059669; color: #ffffff; }}
  .pct-med {{ background: #2563eb; color: #ffffff; }}
  .pct-low {{ background: #d97706; color: #ffffff; }}

  /* Formula Box */
  .formula-box {{
    background: #0f172a;
    color: #38bdf8;
    padding: 14px 18px;
    border-radius: 6px;
    margin: 14px 0;
    border: 1px solid #1e293b;
    page-break-inside: avoid;
  }}

  .formula-label {{
    display: block;
    color: #94a3b8;
    font-size: 7.5pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 6px;
  }}

  .math-display {{
    font-family: "Courier New", Consolas, monospace;
    font-size: 9.5pt;
    font-weight: 600;
    color: #f1f5f9;
    word-break: break-all;
    line-height: 1.5;
  }}

  .math-inline {{
    font-family: "Courier New", Consolas, monospace;
    font-weight: 600;
    color: #0369a1;
  }}

  /* Diagram Card */
  .ascii-diagram-card {{
    background: #0f172a;
    color: #a5f3fc;
    border-radius: 6px;
    padding: 12px 14px;
    margin: 12px 0;
    font-family: Consolas, "Liberation Mono", Menlo, Courier, monospace;
    font-size: 7.5pt;
    line-height: 1.35;
    border: 1px solid #334155;
    page-break-inside: avoid;
  }}

  .ascii-diagram-card pre {{
    margin: 0;
    white-space: pre;
    overflow-x: hidden;
  }}

  .inline-code {{
    background: #f1f5f9;
    color: #0f172a;
    font-family: Consolas, Monaco, monospace;
    font-size: 8pt;
    padding: 1px 4px;
    border-radius: 3px;
    border: 1px solid #e2e8f0;
  }}

  /* Lists */
  .list-item {{
    display: flex;
    align-items: flex-start;
    margin: 8px 0;
    page-break-inside: avoid;
  }}

  .list-idx {{
    background: #2563eb;
    color: #ffffff;
    font-weight: 700;
    font-size: 7.5pt;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: 10px;
    flex-shrink: 0;
    margin-top: 1px;
  }}

  .list-content {{
    font-size: 8.5pt;
    color: #334155;
    line-height: 1.45;
  }}

  .bullet-item {{
    display: flex;
    align-items: flex-start;
    margin: 5px 0 5px 12px;
  }}

  .bullet-dot {{
    color: #3b82f6;
    margin-right: 8px;
    font-size: 9pt;
  }}

  .bullet-content {{
    font-size: 8.5pt;
    color: #334155;
  }}

  .divider {{
    border: 0;
    height: 1px;
    background: #e2e8f0;
    margin: 18px 0;
  }}

  .spacer {{
    height: 6px;
  }}

  .para {{
    margin: 6px 0;
    font-size: 8.5pt;
    color: #334155;
  }}

  /* Page break rules */
  .page-break {{
    page-break-before: always;
  }}
</style>
</head>
<body>

<!-- Header Banner -->
<div class="cover-banner">
  <div class="gov-badge">SMART INDIA HACKATHON (SIH) 2024 &bull; PROBLEM STATEMENT: 26187</div>
  <div class="doc-title">IBVAP MASTER MODEL STACK INVENTORY &amp; ORCHESTRATION BLUEPRINT</div>
  <div class="doc-subtitle">Complete 17-Layer Autonomous Multi-Tier AI Vision Architecture &bull; Border Surveillance Edge Deployment</div>
  
  <div class="meta-grid">
    <div class="meta-item">
      <strong>Organization / Team</strong>
      <span>Team Trinetra (Team ID: T96)</span>
    </div>
    <div class="meta-item">
      <strong>Development Baseline</strong>
      <span>Dell Core i3 / 12 GB RAM (No GPU)</span>
    </div>
    <div class="meta-item">
      <strong>Target Deployments</strong>
      <span>Edge RTX 3050 &bull; Jetson &bull; HQ Server</span>
    </div>
    <div class="meta-item">
      <strong>Model Portfolio</strong>
      <span>121 Cataloged / 17 Expert Pools</span>
    </div>
  </div>
</div>

<!-- Core System Doctrine -->
<div class="doctrine-box">
  <div class="doctrine-title">Autonomous Core System Doctrine</div>
  <em>&ldquo;IBVAP does not execute every model on every frame. It maintains a unified, version-controlled portfolio of specialized AI experts and autonomously selects, activates, escalates, fuses, or bypasses them based on real-time scene diagnostics, bounding box uncertainty, temporal stability, and hardware compute budgets.&rdquo;</em>
</div>

<!-- Main Content -->
{body_html}

</body>
</html>
"""
    return html


def main():
    import shutil
    base_dir = r"C:\Users\dell\Desktop\p2\IBVAP_Final_Project"
    md_path = os.path.join(base_dir, "docs", "master_stack_inventory_full.md")
    html_path = os.path.join(base_dir, "docs", "master_model_stack_inventory.html")
    pdf_path = r"C:\Users\dell\Desktop\IBVAP_MASTER_MODEL_STACK_INVENTORY.pdf"

    print(f"Reading markdown from: {md_path}")
    body_html = parse_markdown_to_html(md_path)
    full_html = build_full_html(body_html)

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(full_html)
    print(f"HTML written to: {html_path} ({len(full_html)} bytes)")

    # Execute Headless Edge
    edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    if not os.path.exists(edge_path):
        edge_path = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"

    print(f"Using Microsoft Edge binary: {edge_path}")
    cmd = [
        edge_path,
        "--headless",
        "--disable-gpu",
        "--run-all-compositor-stages-before-draw",
        f"--print-to-pdf={pdf_path}",
        html_path
    ]

    print(f"Running conversion command...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0 and os.path.exists(pdf_path):
        size_kb = os.path.getsize(pdf_path) / 1024
        print(f"SUCCESS: PDF generated at: {pdf_path}")
        print(f"PDF File Size: {size_kb:.2f} KB")

        # Copy to project docs and artifact directory
        docs_copy = os.path.join(base_dir, "docs", "IBVAP_MASTER_MODEL_STACK_INVENTORY.pdf")
        shutil.copyfile(pdf_path, docs_copy)
        print(f"Copied to: {docs_copy}")

        artifact_dir = r"C:\Users\dell\.gemini\antigravity\brain\0cdcb8c2-4db2-4e10-9b93-0183d6ae097b"
        if os.path.isdir(artifact_dir):
            art_copy = os.path.join(artifact_dir, "IBVAP_MASTER_MODEL_STACK_INVENTORY.pdf")
            shutil.copyfile(pdf_path, art_copy)
            print(f"Copied to artifact dir: {art_copy}")
    else:
        print(f"Error during PDF conversion. Return code: {res.returncode}")
        print(f"Stdout: {res.stdout}")
        print(f"Stderr: {res.stderr}")

if __name__ == "__main__":
    main()
