import importlib.util, html, json, os, re

SRC = os.path.dirname(os.path.abspath(__file__))
DOMAIN_DIR = os.path.join(SRC, "domains")
STUDY_AID_PATH = os.path.join(SRC, "study-aids", "identity-governance-monitoring.md")
REPO_ROOT = os.path.dirname(SRC)
OUT_PATH = os.path.join(REPO_ROOT, "index.html")

def load(mod):
    spec = importlib.util.spec_from_file_location(mod, os.path.join(DOMAIN_DIR, mod + ".py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

# head module, [extra modules whose LABS are appended]
GROUPS = [("d1", []), ("d2", []), ("d3", []), ("d4", [])]

DOMAINS = []
for head, extra in GROUPS:
    m = load(head)
    labs = list(m.LABS)
    for e in extra:
        labs += list(load(e).LABS)
    d = dict(m.DOMAIN); d["labs"] = labs
    DOMAINS.append(d)

E = html.escape

def code(s):
    return E(s.strip("\n").rstrip())

def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")

def inline_md(text):
    placeholders = []

    def stash_code(match):
        placeholders.append(f"<code>{E(match.group(1))}</code>")
        return f"\x00{len(placeholders) - 1}\x00"

    rendered = re.sub(r"`([^`]+)`", stash_code, text)
    rendered = E(rendered)
    rendered = re.sub(
        r"\[([^\]]+)\]\((https?://[^)]+)\)",
        r'<a href="\2" target="_blank" rel="noreferrer">\1</a>',
        rendered,
    )
    rendered = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", rendered)
    rendered = re.sub(r"\x00(\d+)\x00", lambda m: placeholders[int(m.group(1))], rendered)
    return rendered

def markdown_blocks(markdown):
    lines = markdown.strip().splitlines()
    output, i = [], 0

    while i < len(lines):
        line = lines[i].rstrip()
        if not line:
            i += 1
            continue

        if line.startswith("```"):
            language = line[3:].strip()
            block = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1
            lang_attr = f' data-language="{E(language)}"' if language else ""
            output.append(f'<pre class="study-code"{lang_attr}><code>{E(chr(10).join(block))}</code></pre>')
            continue

        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-+", lines[i + 1]):
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append([cell.strip() for cell in lines[i].strip().strip("|").split("|")])
                i += 1
            headers = rows[0]
            body_rows = rows[2:]
            table = ["<div class=\"study-table-wrap\"><table><thead><tr>"]
            table.extend(f"<th>{inline_md(cell)}</th>" for cell in headers)
            table.append("</tr></thead><tbody>")
            for row in body_rows:
                table.append("<tr>")
                table.extend(f"<td>{inline_md(cell)}</td>" for cell in row)
                table.append("</tr>")
            table.append("</tbody></table></div>")
            output.append("".join(table))
            continue

        if line.startswith(">"):
            quote = []
            while i < len(lines) and lines[i].startswith(">"):
                quote.append(lines[i][1:].strip())
                i += 1
            output.append(f'<blockquote class="study-anchor">{inline_md(" ".join(quote))}</blockquote>')
            continue

        list_match = re.match(r"^(\s*)([-*]|\d+\.)\s+(.+)", line)
        if list_match:
            ordered = list_match.group(2).endswith(".")
            tag = "ol" if ordered else "ul"
            items = []
            while i < len(lines):
                item = re.match(r"^\s*([-*]|\d+\.)\s+(.+)", lines[i])
                if not item or item.group(1).endswith(".") != ordered:
                    break
                items.append(f"<li>{inline_md(item.group(2))}</li>")
                i += 1
            output.append(f'<{tag} class="study-list">{"".join(items)}</{tag}>')
            continue

        heading = re.match(r"^(#{2,4})\s+(.+)", line)
        if heading:
            level = len(heading.group(1)) + 1
            output.append(f"<h{level}>{inline_md(heading.group(2))}</h{level}>")
            i += 1
            continue

        paragraph = [line]
        i += 1
        while i < len(lines) and lines[i].strip():
            next_line = lines[i]
            if (
                next_line.startswith(("```", ">", "|", "##"))
                or re.match(r"^\s*([-*]|\d+\.)\s+", next_line)
            ):
                break
            paragraph.append(next_line.strip())
            i += 1
        output.append(f"<p>{inline_md(' '.join(paragraph))}</p>")

    return "".join(output)

def load_study_aid():
    with open(STUDY_AID_PATH, encoding="utf-8") as source:
        markdown = source.read().replace("\r\n", "\n")

    title_match = re.match(r"#\s+(.+)\n", markdown)
    matches = list(re.finditer(r"(?m)^##\s+(.+)$", markdown))
    intro_end = matches[0].start() if matches else len(markdown)
    intro = markdown[title_match.end():intro_end] if title_match else markdown[:intro_end]
    sections = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        sections.append((match.group(1).strip(), markdown[match.end():end].strip()))

    section_map = dict(sections)
    questions = []
    for line in section_map["100 true/false questions"].splitlines():
        match = re.match(r"^(\d+)\.\s+(.+)$", line)
        if match:
            questions.append((int(match.group(1)), match.group(2)))

    answers = {}
    for line in section_map["Answer key"].splitlines():
        match = re.match(r"^(\d+)\.\s+\*\*([TF])\*\*\s+-\s+(.+)$", line)
        if match:
            answers[int(match.group(1))] = (match.group(2), match.group(3))

    if len(questions) != 100 or len(answers) != 100:
        raise ValueError("The identity study aid must contain exactly 100 questions and answers")

    notes = [
        (name, body)
        for name, body in sections
        if name not in {"100 true/false questions", "Answer key", "Official Microsoft Learn links"}
    ]
    return {
        "title": title_match.group(1) if title_match else "Identity, governance, and monitoring study aid",
        "intro": intro,
        "notes": notes,
        "questions": questions,
        "answers": answers,
        "sources": section_map["Official Microsoft Learn links"],
    }

def steps_html(steps):
    out, open_ol, n = [], False, 0
    for s in steps:
        if s.startswith("##"):
            if open_ol: out.append("</ol>"); open_ol = False
            out.append(f'<h5 class="sub">{E(s[2:].strip())}</h5>')
        else:
            if not open_ol:
                out.append(f'<ol class="steps" start="{n+1}">'); open_ol = True
            n += 1
            out.append(f"<li>{s}</li>")
    if open_ol: out.append("</ol>")
    return "".join(out)

def codepane(pane, body):
    return (
        f'<div class="pane" data-pane="{pane}">'
        f'<div class="codewrap"><button class="copy" type="button">Copy</button>'
        f'<pre class="code"><code>{code(body)}</code></pre></div></div>'
    )

def lab_html(lab, dkey):
    exam = "".join(f"<li>{x}</li>" for x in lab["exam"])
    traps = "".join(f"<li>{x}</li>" for x in lab["traps"])
    lvl = lab["level"].lower()
    code_label = lab.get("code_label", "Python / SDK")

    # Build tabs + panes dynamically. Portal is always present and active.
    tabs = ['<button class="tab active" data-tab="portal" type="button">Azure Portal</button>']
    panes = [f'<div class="pane active" data-pane="portal">{steps_html(lab["portal"])}</div>']
    if lab.get("cli"):
        tabs.append('<button class="tab" data-tab="cli" type="button">Azure CLI (Bash)</button>')
        panes.append(codepane("cli", lab["cli"]))
    if lab.get("code"):
        tabs.append(f'<button class="tab" data-tab="code" type="button">{E(code_label)}</button>')
        panes.append(codepane("code", lab["code"]))

    cleanup = ""
    if lab.get("cleanup"):
        cleanup = (
            '<details class="cleanup"><summary>Cleanup / teardown</summary>'
            f'<div class="codewrap"><button class="copy" type="button">Copy</button>'
            f'<pre class="code"><code>{code(lab["cleanup"])}</code></pre></div></details>'
        )

    search = " ".join([lab["id"], lab["title"], lab["objective"],
                       re.sub("<[^>]+>", " ", " ".join(lab["exam"] + lab["traps"]))]).lower()

    return f'''
<article class="lab" id="lab-{lab["id"]}" data-domain="{dkey}" data-level="{lvl}" data-search="{E(search)}">
  <header class="lab-head" role="button" tabindex="0">
    <span class="lab-id">{E(lab["id"])}</span>
    <div class="lab-title-wrap">
      <h3 class="lab-title">{E(lab["title"])}</h3>
      <p class="lab-obj">{E(lab["objective"])}</p>
    </div>
    <span class="meta">
      <span class="pill pill-{lvl}">{E(lab["level"])}</span>
      <span class="pill pill-time">{E(lab["time"])}</span>
    </span>
    <span class="chev" aria-hidden="true">&#9662;</span>
  </header>
  <div class="lab-body">
    <div class="callout callout-exam">
      <div class="callout-h"><span class="ico">&#9678;</span> What the exam is testing</div>
      <ul>{exam}</ul>
    </div>
    <p class="prereq"><b>Prerequisites:</b> {lab["prereq"]}</p>
    <div class="tabs" role="tablist">{"".join(tabs)}</div>
    <div class="panes">{"".join(panes)}</div>
    <div class="callout callout-trap">
      <div class="callout-h"><span class="ico">&#9888;</span> Exam traps &amp; gotchas</div>
      <ul>{traps}</ul>
    </div>
    {cleanup}
  </div>
</article>'''

STUDY = load_study_aid()
study_topics = []
study_topic_links = []
for name, body in STUDY["notes"]:
    topic_id = f"study-{slug(name)}"
    study_topic_links.append(f'<a href="#{topic_id}">{E(name)}</a>')
    study_topics.append(
        f'<section class="study-topic" id="{topic_id}" data-search="{E((name + " " + body).lower())}">'
        f'<h3>{E(name)}</h3>{markdown_blocks(body)}</section>'
    )

quiz_items = []
for number, question in STUDY["questions"]:
    answer, explanation = STUDY["answers"][number]
    answer_word = "True" if answer == "T" else "False"
    search_text = f"{number} {question} {answer_word} {explanation}".lower()
    quiz_items.append(f'''
<article class="quiz-item" data-answer="{answer}" data-search="{E(search_text)}">
  <h4><span class="quiz-number">{number}</span><span class="quiz-question">{inline_md(question)}</span></h4>
  <div class="quiz-choices" role="group" aria-label="Question {number}: choose true or false">
    <button class="quiz-choice" data-choice="T" type="button">True</button>
    <button class="quiz-choice" data-choice="F" type="button">False</button>
  </div>
  <div class="quiz-feedback" role="status" hidden>
    <strong class="quiz-result">Answer: {answer_word}</strong>
    <span class="quiz-explanation">{inline_md(explanation)}</span>
  </div>
</article>''')

STUDY_HTML = f'''
<section class="study-aid" id="study-aid">
  <div class="study-hero">
    <p class="eyebrow">Domain 4 companion study aid</p>
    <h2>{E(STUDY["title"])}</h2>
    {markdown_blocks(STUDY["intro"])}
    <div class="study-jump">{"".join(study_topic_links)}<a href="#study-quiz">100-question quiz</a><a href="#study-sources">Official sources</a></div>
  </div>
  <div class="study-tools">
    <input id="study-q" type="search" placeholder="Search the study aid and quiz" autocomplete="off">
    <button id="show-answers" class="btn" type="button">Show all answers</button>
    <button id="reset-quiz" class="btn" type="button">Reset quiz</button>
  </div>
  <div class="study-notes">{"".join(study_topics)}</div>
  <section class="study-quiz" id="study-quiz">
    <div class="dom-head"><span class="dom-num">100</span><div><h2>100 true/false questions</h2><p class="dom-w">Choose an answer to reveal the explanation</p></div></div>
    <div class="quiz-progress" id="quiz-progress" aria-live="polite">0 of 100 answered</div>
    <div class="quiz-list">{"".join(quiz_items)}</div>
    <div class="empty" id="study-empty"><h3>No study content matches that search</h3><p>Try a broader identity, governance, monitoring, or KQL term.</p></div>
  </section>
  <section class="study-sources study-topic" id="study-sources">
    <h3>Official Microsoft Learn links</h3>
    {markdown_blocks(STUDY["sources"])}
  </section>
</section>'''

nav, sections, total = [], [], 0
for i, d in enumerate(DOMAINS, 1):
    total += len(d["labs"])
    nav.append(
        f'<button class="navbtn" data-domain="{d["key"]}" type="button">'
        f'<span class="navnum">{i}</span>'
        f'<span class="navtxt"><b>{E(d["name"])}</b><i>{E(d["weight"])} &middot; {len(d["labs"])} labs</i></span></button>'
    )
    sections.append(
        f'<section class="domain" id="dom-{d["key"]}" data-domain="{d["key"]}">'
        f'<div class="dom-head"><span class="dom-num">{i}</span>'
        f'<div><h2>{E(d["name"])}</h2><p class="dom-w">Exam weighting <b>{E(d["weight"])}</b> &middot; {len(d["labs"])} labs</p></div></div>'
        f'<p class="dom-blurb">{E(d["blurb"])}</p>'
        + "".join(lab_html(l, d["key"]) for l in d["labs"]) + "</section>"
    )

nav.append(
    '<a class="navbtn study-nav" href="#study-aid">'
    '<span class="navnum">+</span>'
    '<span class="navtxt"><b>Identity, governance &amp; monitoring</b>'
    '<i>Cheat sheet &middot; 100 explained questions</i></span></a>'
)

CSS = """
:root {
  color-scheme: light;
  --cp-bg: #f7f4ef;
  --cp-bg-elevated: #fcfbf8;
  --cp-surface: #ffffff;
  --cp-surface-soft: #f5f5f5;
  --cp-border: #dedede;
  --cp-border-strong: #919191;
  --cp-text: #242424;
  --cp-text-muted: #5c5c5c;
  --cp-text-soft: #6f6f6f;
  --cp-accent: #b11f4b;
  --cp-accent-hover: #9a1a41;
  --cp-accent-soft: rgba(177, 31, 75, 0.08);
  --cp-accent-fg: #ffffff;
  --cp-success: #16a34a;
  --cp-danger: #dc2626;
  --cp-warning: #f59e0b;
  --cp-link: #0078d4;
  --cp-shadow: 0 18px 48px rgba(0, 0, 0, 0.12);
  --cp-overlay: rgba(255, 255, 255, 0.8);
  --cp-panel: rgba(255, 255, 255, 0.86);
  --cp-panel-strong: rgba(255, 255, 255, 0.96);
  --cp-sheen: rgba(255, 255, 255, 0.55);
  --cp-highlight: rgba(177, 31, 75, 0.12);
}
html[data-theme="dark"] {
  color-scheme: dark;
  --cp-bg: #3d3b3a;
  --cp-bg-elevated: #343231;
  --cp-surface: #292929;
  --cp-surface-soft: #2e2e2e;
  --cp-border: #474747;
  --cp-border-strong: #5f5f5f;
  --cp-text: #dedede;
  --cp-text-muted: #919191;
  --cp-text-soft: #b0b0b0;
  --cp-accent: #fd8ea1;
  --cp-accent-hover: #fb7b91;
  --cp-accent-soft: rgba(253, 142, 161, 0.14);
  --cp-accent-fg: #1a1a1a;
  --cp-success: #4ade80;
  --cp-danger: #f87171;
  --cp-warning: #fbbf24;
  --cp-link: #4da6ff;
  --cp-shadow: 0 18px 48px rgba(0, 0, 0, 0.32);
  --cp-overlay: rgba(41, 41, 41, 0.88);
  --cp-panel: rgba(41, 41, 41, 0.72);
  --cp-panel-strong: rgba(41, 41, 41, 0.96);
  --cp-sheen: rgba(255, 255, 255, 0.04);
  --cp-highlight: rgba(253, 142, 161, 0.12);
}
*{box-sizing:border-box}
body{margin:0;background:var(--cp-bg);color:var(--cp-text);font-family:"Segoe UI",Aptos,Calibri,-apple-system,BlinkMacSystemFont,sans-serif;font-size:15px;line-height:1.6}
code,pre,kbd{font-family:Consolas,"Courier New",Courier,monospace}
a{color:var(--cp-link)}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px 80px}
header.top{background:var(--cp-bg-elevated);border-bottom:1px solid var(--cp-border);padding:34px 0 26px;margin-bottom:26px}
header.top .wrap{padding-bottom:0}
.eyebrow{color:var(--cp-accent);font-weight:600;font-size:12.5px;letter-spacing:.10em;text-transform:uppercase;margin:0 0 8px}
h1{margin:0 0 10px;font-size:31px;line-height:1.2;font-weight:650;letter-spacing:-.01em}
.sub-lede{color:var(--cp-text-muted);margin:0 0 20px;max-width:74ch}
.stats{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:20px}
.stat{background:var(--cp-surface);border:1px solid var(--cp-border);border-radius:.625rem;padding:9px 15px;box-shadow:0 0 2px rgba(0,0,0,.12),0 1px 2px rgba(0,0,0,.14)}
.stat b{display:block;font-size:20px;line-height:1.2;color:var(--cp-accent)}
.stat span{font-size:11.5px;color:var(--cp-text-muted);text-transform:uppercase;letter-spacing:.05em}
.controls{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
#q{flex:1 1 300px;min-width:240px;background:var(--cp-surface);border:1px solid var(--cp-border);color:var(--cp-text);border-radius:.625rem;padding:10px 14px;font-family:inherit;font-size:14.5px;outline:none}
#q:focus{border-color:var(--cp-accent)}
.seg{display:flex;background:var(--cp-surface);border:1px solid var(--cp-border);border-radius:.625rem;overflow:hidden}
.seg button{background:transparent;border:0;border-right:1px solid var(--cp-border);color:var(--cp-text-muted);padding:10px 14px;font-family:inherit;font-size:13.5px;cursor:pointer;white-space:nowrap}
.seg button:last-child{border-right:0}
.seg button.on{background:var(--cp-accent);color:var(--cp-accent-fg);font-weight:600}
.btn{background:var(--cp-surface);border:1px solid var(--cp-border);color:var(--cp-text-muted);border-radius:.625rem;padding:10px 14px;font-family:inherit;font-size:13.5px;cursor:pointer;white-space:nowrap}
.btn:hover{border-color:var(--cp-accent);color:var(--cp-accent)}
.btn.primary{background:var(--cp-accent);border-color:var(--cp-accent);color:var(--cp-accent-fg);text-decoration:none}
.btn.primary:hover{background:var(--cp-accent-hover);color:var(--cp-accent-fg)}
nav.doms{display:grid;grid-template-columns:repeat(auto-fit,minmax(215px,1fr));gap:10px;margin:0 0 30px}
.navbtn{display:flex;gap:11px;align-items:center;text-align:left;background:var(--cp-surface);border:1px solid var(--cp-border);border-radius:16px;padding:13px 15px;cursor:pointer;color:var(--cp-text);font-family:inherit;box-shadow:0 0 2px rgba(0,0,0,.12),0 1px 2px rgba(0,0,0,.14)}
.navbtn.study-nav{text-decoration:none}
.navbtn:hover{border-color:var(--cp-accent)}
.navbtn.on{border-color:var(--cp-accent);background:var(--cp-accent-soft)}
.navnum{flex:0 0 30px;height:30px;border-radius:50%;background:var(--cp-accent);color:var(--cp-accent-fg);display:grid;place-items:center;font-weight:700;font-size:14px}
.navtxt b{display:block;font-size:13.5px;font-weight:600;line-height:1.35}
.navtxt i{font-style:normal;font-size:11.5px;color:var(--cp-text-muted)}
.domain{margin-bottom:44px;scroll-margin-top:16px}
.dom-head{display:flex;gap:14px;align-items:center;padding-bottom:12px;border-bottom:2px solid var(--cp-accent);margin-bottom:12px}
.dom-num{flex:0 0 38px;height:38px;border-radius:50%;background:var(--cp-accent);color:var(--cp-accent-fg);display:grid;place-items:center;font-weight:700;font-size:17px}
.dom-head h2{margin:0;font-size:22px;font-weight:640;letter-spacing:-.01em}
.dom-w{margin:1px 0 0;font-size:12.5px;color:var(--cp-text-muted)}
.dom-blurb{color:var(--cp-text-muted);margin:0 0 18px;max-width:88ch;font-size:14.5px}
.lab{background:var(--cp-surface);border:1px solid var(--cp-border);border-radius:16px;margin-bottom:12px;overflow:hidden;box-shadow:0 0 2px rgba(0,0,0,.12),0 1px 2px rgba(0,0,0,.14);scroll-margin-top:14px}
.lab.open{border-color:var(--cp-accent)}
.lab-head{display:flex;gap:14px;align-items:center;padding:15px 18px;cursor:pointer;user-select:none}
.lab-head:hover{background:var(--cp-surface-soft)}
.lab-head:focus-visible{outline:2px solid var(--cp-accent);outline-offset:-2px}
.lab-id{flex:0 0 auto;font-weight:700;color:var(--cp-accent);font-size:14px;min-width:30px}
.lab-title-wrap{flex:1 1 auto;min-width:0}
.lab-title{margin:0;font-size:16px;font-weight:600;line-height:1.35}
.lab-obj{margin:3px 0 0;font-size:13px;color:var(--cp-text-muted);line-height:1.5}
.meta{display:flex;gap:6px;flex:0 0 auto;flex-wrap:wrap;justify-content:flex-end}
.pill{font-size:11px;padding:3px 9px;border-radius:999px;border:1px solid var(--cp-border);color:var(--cp-text-muted);white-space:nowrap}
.pill-foundational{border-color:var(--cp-success);color:var(--cp-success)}
.pill-core{border-color:var(--cp-link);color:var(--cp-link)}
.pill-advanced{border-color:var(--cp-warning);color:var(--cp-warning)}
.chev{flex:0 0 auto;color:var(--cp-text-muted);transition:transform .15s;font-size:13px}
.lab.open .chev{transform:rotate(180deg)}
.lab-body{display:none;padding:0 18px 18px;border-top:1px solid var(--cp-border)}
.lab.open .lab-body{display:block}
.callout{border-radius:.625rem;padding:13px 16px;margin:16px 0}
.callout ul{margin:8px 0 0;padding-left:19px}
.callout li{margin-bottom:6px;font-size:14px}
.callout li:last-child{margin-bottom:0}
.callout-h{font-weight:650;font-size:13px;letter-spacing:.03em;text-transform:uppercase;display:flex;gap:8px;align-items:center}
.ico{font-size:14px}
.callout-exam{background:var(--cp-accent-soft);border-left:3px solid var(--cp-accent)}
.callout-exam .callout-h{color:var(--cp-accent)}
.callout-trap{background:var(--cp-surface-soft);border-left:3px solid var(--cp-warning)}
.callout-trap .callout-h{color:var(--cp-warning)}
.prereq{font-size:13.5px;color:var(--cp-text-muted);margin:0 0 14px;padding-left:2px}
.tabs{display:flex;gap:0;border-bottom:1px solid var(--cp-border);margin-bottom:0;flex-wrap:wrap}
.tab{background:transparent;border:0;border-bottom:2px solid transparent;color:var(--cp-text-muted);padding:9px 15px;font-family:inherit;font-size:13.5px;cursor:pointer;margin-bottom:-1px}
.tab:hover{color:var(--cp-text)}
.tab.active{color:var(--cp-accent);border-bottom-color:var(--cp-accent);font-weight:600}
.pane{display:none;padding-top:15px}
.pane.active{display:block}
h5.sub{margin:18px 0 8px;font-size:12.5px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--cp-accent)}
h5.sub:first-child{margin-top:4px}
ol.steps{margin:0;padding-left:22px}
ol.steps li{margin-bottom:8px;font-size:14.5px;line-height:1.65}
ol.steps li code,.callout code,.prereq code,p code{background:var(--cp-surface-soft);border:1px solid var(--cp-border);border-radius:4px;padding:1px 5px;font-size:12.5px}
.codewrap{position:relative;margin:0 0 12px}
.copy{position:absolute;top:9px;right:9px;background:var(--cp-surface-soft);border:1px solid var(--cp-border);color:var(--cp-text-muted);border-radius:6px;padding:4px 10px;font-family:inherit;font-size:11.5px;cursor:pointer;z-index:2;opacity:.85}
.copy:hover{opacity:1;border-color:var(--cp-accent);color:var(--cp-accent)}
.copy.done{color:var(--cp-success);border-color:var(--cp-success)}
pre.code{background:var(--cp-bg-elevated);border:1px solid var(--cp-border);border-radius:.625rem;padding:15px 16px;overflow-x:auto;margin:0;font-size:12.9px;line-height:1.62}
pre.code code{white-space:pre;color:var(--cp-text)}
details.cleanup{margin-top:14px;border:1px solid var(--cp-border);border-radius:.625rem;background:var(--cp-surface-soft)}
details.cleanup summary{cursor:pointer;padding:10px 15px;font-size:13.5px;font-weight:600;color:var(--cp-text-muted);list-style:none}
details.cleanup summary::-webkit-details-marker{display:none}
details.cleanup summary::before{content:"\\25B8 ";color:var(--cp-accent)}
details.cleanup[open] summary::before{content:"\\25BE "}
details.cleanup .codewrap{margin:0 12px 12px}
.study-aid{margin:56px 0 44px;scroll-margin-top:16px}
.study-hero{background:var(--cp-surface);border:1px solid var(--cp-border);border-top:4px solid var(--cp-accent);border-radius:16px;padding:24px;box-shadow:0 0 2px rgba(0,0,0,.12),0 1px 2px rgba(0,0,0,.14)}
.study-hero h2{margin:0 0 12px;font-size:26px;line-height:1.25}
.study-hero p{color:var(--cp-text-muted);max-width:92ch}
.study-anchor{margin:16px 0;padding:13px 16px;background:var(--cp-accent-soft);border-left:3px solid var(--cp-accent);border-radius:.625rem;color:var(--cp-text)}
.study-jump{display:flex;gap:8px;flex-wrap:wrap;margin-top:18px}
.study-jump a{border:1px solid var(--cp-border);border-radius:.625rem;background:var(--cp-surface-soft);color:var(--cp-text);padding:6px 10px;text-decoration:none;font-size:12.5px}
.study-jump a:hover{border-color:var(--cp-accent);color:var(--cp-accent)}
.study-tools{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:16px 0 22px}
#study-q{flex:1 1 360px;min-width:240px;background:var(--cp-surface);border:1px solid var(--cp-border);color:var(--cp-text);border-radius:.625rem;padding:10px 14px;font-family:inherit;font-size:14.5px;outline:none}
#study-q:focus{border-color:var(--cp-accent)}
.study-notes{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;align-items:start}
.study-topic{min-width:0;background:var(--cp-surface);border:1px solid var(--cp-border);border-radius:16px;padding:20px;scroll-margin-top:16px;box-shadow:0 0 2px rgba(0,0,0,.12),0 1px 2px rgba(0,0,0,.14)}
.study-topic h3{margin:0 0 12px;font-size:19px;line-height:1.3;color:var(--cp-accent)}
.study-topic h4,.study-topic h5{margin:18px 0 8px}
.study-topic p{margin:8px 0;color:var(--cp-text-muted)}
.study-list{margin:8px 0;padding-left:22px}
.study-list li{margin-bottom:6px}
.study-table-wrap{overflow-x:auto;margin:14px 0}
.study-table-wrap table{width:100%;border-collapse:collapse;font-size:13px}
.study-table-wrap th,.study-table-wrap td{padding:9px 10px;border:1px solid var(--cp-border);text-align:left;vertical-align:top}
.study-table-wrap th{background:var(--cp-surface-soft);color:var(--cp-text);font-weight:650}
.study-code{background:var(--cp-bg-elevated);border:1px solid var(--cp-border);border-radius:.625rem;padding:14px 16px;overflow-x:auto;font-size:12.9px;line-height:1.62}
.study-quiz{margin-top:44px;scroll-margin-top:16px}
.study-quiz .dom-num{flex-basis:48px;border-radius:.625rem}
.quiz-progress{margin:-2px 0 14px;color:var(--cp-text-muted);font-size:13px}
.quiz-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.quiz-item{min-width:0;background:var(--cp-surface);border:1px solid var(--cp-border);border-radius:16px;padding:16px;display:flex;flex-direction:column;gap:12px;box-shadow:0 0 2px rgba(0,0,0,.12),0 1px 2px rgba(0,0,0,.14)}
.quiz-item h4{display:flex;gap:10px;align-items:flex-start;margin:0;font-size:14px;line-height:1.5;font-weight:600}
.quiz-item h4 .quiz-number{flex:0 0 28px;height:28px;border-radius:50%;background:var(--cp-accent-soft);color:var(--cp-accent);display:grid;place-items:center;font-size:12px}
.quiz-question{min-width:0}
.quiz-choices{display:flex;gap:8px}
.quiz-choice{flex:1;background:var(--cp-surface-soft);border:1px solid var(--cp-border);border-radius:.625rem;color:var(--cp-text);padding:8px 12px;font-family:inherit;cursor:pointer}
.quiz-choice:hover{border-color:var(--cp-accent)}
.quiz-choice.correct{border-color:var(--cp-success);color:var(--cp-success)}
.quiz-choice.wrong{border-color:var(--cp-danger);color:var(--cp-danger)}
.quiz-feedback{border-top:1px solid var(--cp-border);padding-top:10px;font-size:13px}
.quiz-feedback strong{display:block;color:var(--cp-accent);margin-bottom:3px}
.quiz-feedback span{color:var(--cp-text-muted)}
.study-sources{margin-top:44px}
.study-sources .study-list{columns:2;column-gap:30px}
.study-sources .study-list li{break-inside:avoid}
.empty{display:none;text-align:center;padding:50px 20px;color:var(--cp-text-muted)}
footer{border-top:1px solid var(--cp-border);margin-top:36px;padding-top:20px;color:var(--cp-text-muted);font-size:12.5px}
::-webkit-scrollbar{height:10px;width:10px}
::-webkit-scrollbar-track{background:var(--cp-bg)}
::-webkit-scrollbar-thumb{background:var(--cp-border-strong);border-radius:5px}
@media print{.controls,nav.doms,.tabs,.copy,.study-tools,.quiz-choices,header.top .stats{display:none}.lab-body,.quiz-feedback{display:block!important}.pane{display:block!important}.lab,.quiz-item,.study-topic{break-inside:avoid}}
@media(max-width:800px){.study-notes,.quiz-list{grid-template-columns:1fr}.study-sources .study-list{columns:1}}
@media(max-width:720px){.lab-head{flex-wrap:wrap}.meta{width:100%;justify-content:flex-start}h1{font-size:25px}}
"""

JS = """
document.querySelectorAll('.lab-head').forEach(function(h){
  function tog(){ h.parentElement.classList.toggle('open'); }
  h.addEventListener('click', tog);
  h.addEventListener('keydown', function(e){ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); tog(); } });
});
document.querySelectorAll('.lab').forEach(function(lab){
  lab.querySelectorAll('.tab').forEach(function(t){
    t.addEventListener('click', function(){
      lab.querySelectorAll('.tab').forEach(function(x){x.classList.remove('active');});
      lab.querySelectorAll('.pane').forEach(function(x){x.classList.remove('active');});
      t.classList.add('active');
      var p = lab.querySelector('.pane[data-pane="'+t.dataset.tab+'"]');
      if(p) p.classList.add('active');
    });
  });
});
document.querySelectorAll('.copy').forEach(function(b){
  b.addEventListener('click', function(e){
    e.stopPropagation();
    var txt = b.parentElement.querySelector('code').innerText;
    var done = function(){ b.textContent='Copied'; b.classList.add('done');
      setTimeout(function(){ b.textContent='Copy'; b.classList.remove('done'); },1400); };
    if(navigator.clipboard && navigator.clipboard.writeText){
      navigator.clipboard.writeText(txt).then(done, function(){fallback(txt,done);});
    } else { fallback(txt,done); }
  });
});
function fallback(txt, cb){
  var ta=document.createElement('textarea'); ta.value=txt;
  ta.style.position='fixed'; ta.style.opacity='0'; document.body.appendChild(ta);
  ta.select(); try{ document.execCommand('copy'); cb(); }catch(err){}
  document.body.removeChild(ta);
}
var state={domain:'all',level:'all',q:''};
function apply(){
  var shown=0;
  document.querySelectorAll('.lab').forEach(function(l){
    var ok=(state.domain==='all'||l.dataset.domain===state.domain)
        && (state.level==='all'||l.dataset.level===state.level)
        && (state.q===''||l.dataset.search.indexOf(state.q)>-1);
    l.style.display=ok?'':'none'; if(ok) shown++;
  });
  document.querySelectorAll('.domain').forEach(function(d){
    var any=d.querySelectorAll('.lab:not([style*="display: none"])').length>0;
    d.style.display=any?'':'none';
  });
  document.getElementById('empty').style.display=shown?'none':'block';
}
document.getElementById('q').addEventListener('input',function(e){
  state.q=e.target.value.toLowerCase().trim(); apply();
});
document.querySelectorAll('.navbtn').forEach(function(b){
  b.addEventListener('click',function(){
    var d=b.dataset.domain, was=b.classList.contains('on');
    document.querySelectorAll('.navbtn').forEach(function(x){x.classList.remove('on');});
    if(was){ state.domain='all'; } else { b.classList.add('on'); state.domain=d; }
    apply();
    if(!was){ var s=document.getElementById('dom-'+d); if(s) s.scrollIntoView({behavior:'smooth',block:'start'}); }
  });
});
document.querySelectorAll('.seg button').forEach(function(b){
  b.addEventListener('click',function(){
    b.parentElement.querySelectorAll('button').forEach(function(x){x.classList.remove('on');});
    b.classList.add('on'); state.level=b.dataset.level; apply();
  });
});
document.getElementById('expand').addEventListener('click',function(){
  var any=document.querySelector('.lab.open');
  document.querySelectorAll('.lab').forEach(function(l){ l.classList.toggle('open', !any); });
  this.textContent = any ? 'Expand all' : 'Collapse all';
});
function updateQuizProgress(){
  var answered=document.querySelectorAll('.quiz-item[data-answered="true"]').length;
  document.getElementById('quiz-progress').textContent=answered+' of 100 answered';
}
function revealAnswer(item, choice){
  var answer=item.dataset.answer;
  item.querySelectorAll('.quiz-choice').forEach(function(button){
    button.classList.remove('correct','wrong');
    if(button.dataset.choice===answer){ button.classList.add('correct'); }
    if(choice && button.dataset.choice===choice && choice!==answer){ button.classList.add('wrong'); }
  });
  item.querySelector('.quiz-feedback').hidden=false;
  if(choice){ item.dataset.answered='true'; }
}
document.querySelectorAll('.quiz-choice').forEach(function(button){
  button.addEventListener('click',function(){
    revealAnswer(button.closest('.quiz-item'),button.dataset.choice);
    updateQuizProgress();
  });
});
document.getElementById('show-answers').addEventListener('click',function(){
  document.querySelectorAll('.quiz-item').forEach(function(item){ revealAnswer(item); });
});
document.getElementById('reset-quiz').addEventListener('click',function(){
  document.querySelectorAll('.quiz-item').forEach(function(item){
    delete item.dataset.answered;
    item.querySelectorAll('.quiz-choice').forEach(function(button){ button.classList.remove('correct','wrong'); });
    item.querySelector('.quiz-feedback').hidden=true;
  });
  updateQuizProgress();
});
document.getElementById('study-q').addEventListener('input',function(e){
  var q=e.target.value.toLowerCase().trim(), shown=0;
  document.querySelectorAll('.study-topic,.quiz-item').forEach(function(item){
    var searchable=item.dataset.search || item.textContent.toLowerCase();
    var visible=!q || searchable.indexOf(q)>-1;
    item.style.display=visible?'':'none';
    if(visible){ shown++; }
  });
  document.getElementById('study-empty').style.display=shown?'none':'block';
});
(function(){
  var btn=document.getElementById('theme'), root=document.documentElement;
  function label(){ btn.innerHTML = root.getAttribute('data-theme')==='dark' ? '\\u263C Light' : '\\u263E Dark'; }
  label();
  btn.addEventListener('click',function(){
    var next = root.getAttribute('data-theme')==='dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    try{ localStorage.setItem('ai200Theme', next); }catch(e){}
    label();
  });
})();
"""

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI-200 Hands-On Lab &amp; Study Guide</title>
<meta name="description" content="{total} hands-on AI-200 labs covering every exam domain plus an identity, governance, and monitoring study aid with 100 explained true/false questions.">
<script>
  (() => {{
    const param = new URLSearchParams(window.location.search).get("scoutTheme");
    let saved = null;
    try {{ saved = localStorage.getItem("ai200Theme"); }} catch (error) {{}}
    const requested = param || saved;
    const theme = requested === "dark" || requested === "light"
      ? requested
      : (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    document.documentElement.setAttribute("data-theme", theme);
  }})();
</script>
<style>{CSS}</style>
</head>
<body>
<header class="top"><div class="wrap">
  <p class="eyebrow">Microsoft Certified: Azure AI Cloud Developer Associate</p>
  <h1>AI-200 Hands-On Lab &amp; Study Guide</h1>
  <p class="sub-lede">{total} step-by-step labs covering every AI-200 exam domain, plus a focused identity, governance, and monitoring cheat sheet with 100 explained true/false questions. Labs include <b>Azure Portal</b>, <b>Azure CLI</b>, and <b>Python / SDK</b> paths with exam callouts and traps.</p>
  <div class="stats">
    <div class="stat"><b>{total}</b><span>Labs</span></div>
    <div class="stat"><b>4</b><span>Domains</span></div>
    <div class="stat"><b>3</b><span>Methods each</span></div>
    <div class="stat"><b>100</b><span>Study questions</span></div>
  </div>
  <div class="controls">
    <input id="q" type="search" placeholder="Search labs, commands, exam concepts (e.g. &quot;pgvector&quot;, &quot;change feed&quot;, &quot;KEDA&quot;, &quot;dead-letter&quot;)" autocomplete="off">
    <div class="seg">
      <button data-level="all" class="on" type="button">All levels</button>
      <button data-level="foundational" type="button">Foundational</button>
      <button data-level="core" type="button">Core</button>
      <button data-level="advanced" type="button">Advanced</button>
    </div>
    <button id="expand" class="btn" type="button">Expand all</button>
    <a class="btn primary" href="#study-aid">Identity study aid</a>
    <button id="theme" class="btn" type="button" title="Toggle light / dark theme" aria-label="Toggle light or dark theme">&#9788; Light</button>
  </div>
</div></header>

<div class="wrap">
  <nav class="doms" aria-label="Guide sections">{"".join(nav)}</nav>
  {"".join(sections)}
  <div class="empty" id="empty"><h3>No labs match that filter</h3><p>Try a different search term or clear the level filter.</p></div>
{STUDY_HTML}
  <footer>
    <p><b>How to use this guide.</b> AI-200 is a <i>developer</i> exam &mdash; the question bank tests SDK calls, trigger/binding names, connection patterns and CLI flags directly. Read the exam callout <i>before</i> the steps, work the Portal path first for orientation, then rebuild it with the CLI and Python panes so the SDK method names and parameters stick. Read the traps <i>after</i>.</p>
    <p><b>Cost warning.</b> AKS clusters, Container Apps environments, Cosmos DB throughput, Azure Database for PostgreSQL flexible servers and Managed Redis bill continuously whether or not you send traffic. Run the cleanup block at the end of each lab, and prefer deleting the whole resource group when you are done.</p>
    <p>Command syntax reflects Azure CLI 2.x and the current Azure Python SDKs (<code>azure-*</code> packages). Azure and its SDKs change frequently &mdash; verify against Microsoft Learn before relying on any specific flag or method name.</p>
  </footer>
</div>
<script>{JS}</script>
</body>
</html>"""

with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write(HTML)
print("WROTE", OUT_PATH, f"{len(HTML):,}", "chars |", total, "labs")
