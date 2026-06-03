import re
import os

INPUT_FILE = r"static/index.html"
OUTPUT_FILE = INPUT_FILE

print(f"Loading {INPUT_FILE}...")
with open(INPUT_FILE, "r", encoding="utf-8") as fh:
    lines = fh.readlines()

total_lines = len(lines)
print(f"Loaded {total_lines} lines.")

# Find dynamic markers
def find_line(pattern, start_idx=0):
    for idx in range(start_idx, len(lines)):
        if pattern in lines[idx]:
            return idx
    return -1

style_start = find_line("<style>")
ops_widget_comment = find_line("/* WIDGET PANEL DE CONTROL DE OPERARIOS */")
style_end = find_line("</style>", start_idx=style_start+1)
header_start = find_line("<header>")
nav_start = find_line("<nav>")
nav_end = find_line("</nav>", start_idx=nav_start+1)
main_start = find_line("<main>", start_idx=nav_end+1)
main_end = find_line("</main>", start_idx=main_start+1)
workspace_end = find_line("</div>", start_idx=main_end+1)
body_end = find_line("</body>")

if -1 in [style_start, ops_widget_comment, style_end, header_start, nav_start, nav_end, main_start, main_end, workspace_end, body_end]:
    print("CRITICAL ERROR: A marker was not found! Aborting.")
    exit(1)

# New CSS Core Block (replacing lines from style_start + 1 to ops_widget_comment - 1)
NEW_CSS_CORE = """        /* =========================================================================
           PETROFLOW ENTERPRISE v2.0 — DUAL-THEME PROFESSIONAL INDUSTRIAL UI
           Supports Dark & Light Mode dynamically with local storage persistence.
           Inspired by Aveva, AspenTech, Hysys, AFT Arrow.
           ========================================================================= */
        :root {
            /* ── Core Light Theme (Default) ── */
            --bg-app:        #F0F2F5; /* clean light-grey workspace */
            --bg-surface:    #FFFFFF; /* white sidebar/panels */
            --bg-panel:      #F8FAFC; /* cool grey titlebar/toolbar */
            --bg-card:       #FFFFFF; /* crisp white cards */
            --bg-hover:      #E4E6EB; /* hover states */
            --bg-active:     #E1F5FE; /* active selected state (light teal tint) */

            /* ── Borders ── */
            --border:        #D2D2D2;
            --border-light:  #E5E5E5;
            --border-focus:  #0078D4;

            /* ── Text ── */
            --text-primary:  #1A1A1A;
            --text-secondary:#4F4F4F;
            --text-muted:    #808080;
            --text-invert:   #FFFFFF;

            /* ── Accent Blue/Teal (primary brand) ── */
            --brand-color:   #0078D4;
            --brand-dim:     #005A9E;
            --brand-glow:    rgba(0, 120, 212, 0.12);
            --brand-subtle:  rgba(0, 120, 212, 0.06);

            /* ── Status Colors ── */
            --green:         #107C41;
            --green-bg:      rgba(16, 124, 65, 0.08);
            --amber:         #D83B01;
            --amber-bg:      rgba(216, 59, 1, 0.08);
            --red:           #A80000;
            --red-bg:        rgba(168, 0, 0, 0.08);
            --blue:          #0078D4;
            --blue-bg:       rgba(0, 120, 212, 0.08);
            --purple:        #8764B8;

            /* ── Compatibility Mappings for View-Specific CSS ── */
            --border-color:  var(--border);
            --accent-blue:   var(--brand-color);
            --accent-hover:  var(--brand-dim);
            --state-normal:  var(--green);
            --state-warning: var(--amber);
            --state-critical:var(--red);
            --state-info:    var(--blue);
            --bg-mica:       var(--bg-app);

            /* ── Typography ── */
            --font: 'Inter', system-ui, -apple-system, sans-serif;
            --font-mono: 'Consolas', 'JetBrains Mono', monospace;

            /* ── Shadows ── */
            --shadow-sm:   0 1px 2px rgba(0,0,0,0.05);
            --shadow-md:   0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
            --shadow-lg:   0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05);
            --shadow-brand: 0 0 12px rgba(0,120,212,0.15);

            /* ── Geometry ── */
            --radius-sm: 4px;
            --radius-md: 6px;
            --radius-lg: 8px;

            /* ── Layout dimensions ── */
            --titlebar-h: 30px;
            --toolbar-h:  40px;
            --sidebar-w:  220px;
            --props-w:    268px;
            --statusbar-h:24px;
        }

        body.dark-theme {
            /* ── Core Dark Theme ── */
            --bg-app:        #0D1117; /* Slate dark background */
            --bg-surface:    #161B22; /* Sleek sidebar/titlebar */
            --bg-panel:      #1F242C; /* Darker header panels */
            --bg-card:       #21262D; /* Card panels */
            --bg-hover:      #2D333B; /* Active list hover */
            --bg-active:     #172A3A; /* Dark active accent container */

            /* ── Borders ── */
            --border:        #30363D; /* Sleek high contrast dark border */
            --border-light:  #21262D; /* Low contrast divider */
            --border-focus:  #388BFD;

            /* ── Text ── */
            --text-primary:  #E6EDF3; /* High contrast light grey */
            --text-secondary:#8B949E; /* Medium muted light grey */
            --text-muted:    #5F6670; /* Deep muted text */
            --text-invert:   #0D1117;

            /* ── Accent Teal ── */
            --brand-color:   #00D4FF; /* Vibrant teal */
            --brand-dim:     #0099BB;
            --brand-glow:    rgba(0, 212, 255, 0.15);
            --brand-subtle:  rgba(0, 212, 255, 0.08);

            /* ── Status Colors ── */
            --green:         #3FB950;
            --green-bg:      rgba(63,185,80,0.12);
            --amber:         #FFB800;
            --amber-bg:      rgba(255,184,0,0.12);
            --red:           #F85149;
            --red-bg:        rgba(248,81,73,0.12);
            --blue:          #388BFD;
            --blue-bg:       rgba(56,139,253,0.12);
            --purple:        #BC8CFF;

            /* ── Shadows ── */
            --shadow-sm:   0 1px 3px rgba(0,0,0,0.4);
            --shadow-md:   0 4px 12px rgba(0,0,0,0.5);
            --shadow-lg:   0 8px 24px rgba(0,0,0,0.6);
            --shadow-brand: 0 0 20px rgba(0,212,255,0.12);
        }

        *, *::before, *::after { margin:0; padding:0; box-sizing:border-box; }

        html, body {
            width: 100vw;
            height: 100vh;
            overflow: hidden;
            font-family: var(--font);
            background: var(--bg-app);
            color: var(--text-primary);
            font-size: 13px;
            line-height: 1.5;
            transition: background-color 0.15s, color 0.15s;
        }

        /* scrollbar */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

        /* ── APP SHELL ───────────────────────────────────────── */
        #app-shell {
            display: grid;
            grid-template-rows: var(--titlebar-h) var(--toolbar-h) 1fr var(--statusbar-h);
            grid-template-columns: var(--sidebar-w) 1fr var(--props-w);
            grid-template-areas:
                "titlebar titlebar titlebar"
                "toolbar  toolbar  toolbar"
                "sidebar  canvas   props"
                "statusbar statusbar statusbar";
            width: 100vw;
            height: 100vh;
            overflow: hidden;
        }

        /* ── TITLEBAR (menu bar) ─────────────────────────────── */
        .titlebar {
            grid-area: titlebar;
            background: var(--bg-panel);
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            padding: 0 12px;
            user-select: none;
            z-index: 200;
        }

        .titlebar-logo {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 0 12px 0 4px;
            margin-right: 8px;
            border-right: 1px solid var(--border);
        }
        .titlebar-logo svg { width:14px; height:14px; fill: var(--brand-color); flex-shrink:0; }
        .titlebar-logo span { font-size:11px; font-weight:700; color:var(--text-primary); letter-spacing:0.5px; white-space:nowrap; }

        .menu-bar {
            display: flex;
            align-items: center;
            gap: 0;
        }

        .menu-item {
            padding: 0 10px;
            font-size: 11.5px;
            color: var(--text-secondary);
            cursor: pointer;
            height: var(--titlebar-h);
            display: flex;
            align-items: center;
            transition: background 0.12s, color 0.12s;
            white-space: nowrap;
        }
        .menu-item:hover { background: var(--bg-hover); color: var(--text-primary); }

        .titlebar-center {
            font-size: 11px;
            color: var(--text-muted);
            margin-left: auto;
            margin-right: auto;
            position: absolute;
            left: 50%;
            transform: translateX(-50%);
            pointer-events: none;
            font-weight: 500;
        }

        .titlebar-right {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-left: auto;
        }

        .titlebar-badge {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 11px;
            color: var(--text-secondary);
        }

        .status-dot {
            width: 7px; height: 7px;
            border-radius: 50%;
            flex-shrink: 0;
            display: inline-block;
        }
        .dot-green  { background: var(--green); box-shadow: 0 0 5px var(--green); }
        .dot-amber  { background: var(--amber); box-shadow: 0 0 5px var(--amber); }
        .dot-red    { background: var(--red);   box-shadow: 0 0 5px var(--red); }
        .dot-teal   { background: var(--brand-color);  box-shadow: 0 0 5px var(--brand-color); }
        .dot-grey   { background: var(--text-muted); }

        .titlebar-user {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 0 6px;
            height: 22px;
            border-radius: var(--radius-sm);
            cursor: pointer;
            border: 1px solid transparent;
            transition: all 0.12s;
            position: relative;
        }
        .titlebar-user:hover { border-color: var(--border); background: var(--bg-hover); }
        .user-avatar-sm {
            width: 18px; height: 18px;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--brand-dim), #005A77);
            color: var(--text-invert);
            font-size: 8px;
            font-weight: 700;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .titlebar-username { font-size: 11.5px; color: var(--text-secondary); font-weight: 500; }

        /* ── TOOLBAR ─────────────────────────────────────────── */
        .toolbar {
            grid-area: toolbar;
            background: var(--bg-surface);
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            padding: 0 12px;
            gap: 4px;
            z-index: 100;
        }

        .tb-sep {
            width: 1px;
            height: 20px;
            background: var(--border);
            margin: 0 6px;
            flex-shrink: 0;
        }

        .tb-btn {
            display: flex;
            align-items: center;
            gap: 5px;
            padding: 0 8px;
            height: 28px;
            border-radius: var(--radius-sm);
            background: transparent;
            border: 1px solid transparent;
            color: var(--text-secondary);
            font-family: var(--font);
            font-size: 12px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.12s;
            white-space: nowrap;
        }
        .tb-btn svg { width:14px; height:14px; flex-shrink:0; }
        .tb-btn:hover {
            background: var(--bg-hover);
            border-color: var(--border);
            color: var(--text-primary);
        }
        .tb-btn:active { transform: scale(0.97); }
        .tb-btn.tb-primary {
            background: var(--brand-subtle);
            border-color: rgba(0, 120, 212, 0.25);
            color: var(--brand-color);
        }
        .tb-btn.tb-primary:hover {
            background: rgba(0, 120, 212, 0.14);
            border-color: rgba(0, 120, 212, 0.4);
            box-shadow: var(--shadow-brand);
        }
        body.dark-theme .tb-btn.tb-primary {
            background: var(--brand-subtle);
            border-color: rgba(0, 212, 255, 0.25);
            color: var(--brand-color);
        }
        body.dark-theme .tb-btn.tb-primary:hover {
            background: rgba(0, 212, 255, 0.14);
            border-color: rgba(0, 212, 255, 0.4);
            box-shadow: var(--shadow-brand);
        }
        
        .tb-btn.tb-risk {
            background: rgba(216, 59, 1, 0.05);
            border-color: rgba(216, 59, 1, 0.15);
            color: var(--amber);
        }
        .tb-btn.tb-risk:hover { background: rgba(216, 59, 1, 0.12); }
        
        .toolbar-right {
            margin-left: auto;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        /* ── SIDEBAR ─────────────────────────────────────────── */
        .sidebar {
            grid-area: sidebar;
            background: var(--bg-surface);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            overflow-y: auto;
            padding: 8px 0;
            z-index: 90;
        }

        .nav-group { margin-bottom: 8px; }

        .nav-group-label {
            display: block;
            padding: 8px 14px 4px 14px;
            font-size: 9.5px;
            font-weight: 700;
            letter-spacing: 1px;
            text-transform: uppercase;
            color: var(--text-muted);
        }

        .nav-item {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 0 14px;
            height: 32px;
            color: var(--text-secondary);
            cursor: pointer;
            font-size: 12px;
            font-weight: 500;
            transition: background 0.1s, color 0.1s;
            border-left: 2px solid transparent;
            white-space: nowrap;
            text-decoration: none;
        }
        .nav-item svg { width:13px; height:13px; flex-shrink:0; opacity:0.75; }
        .nav-item:hover {
            background: var(--bg-hover);
            color: var(--text-primary);
        }
        .nav-item.active {
            background: var(--bg-active);
            color: var(--brand-color);
            border-left-color: var(--brand-color);
            font-weight: 600;
        }
        .nav-item.active svg { opacity:1; color: var(--brand-color); stroke: var(--brand-color); }

        .sidebar-footer {
            margin-top: auto;
            padding: 12px 14px;
            border-top: 1px solid var(--border);
            font-size: 10px;
            color: var(--text-muted);
            line-height: 1.5;
        }

        /* ── CANVAS (main workspace) ─────────────────────────── */
        main {
            grid-area: canvas;
            background: var(--bg-app);
            overflow-y: auto;
            padding: 24px;
            position: relative;
            z-index: 10;
            transition: background-color 0.15s;
        }

        .view-section {
            display: none;
            animation: fadeIn 0.2s ease-out;
            max-width: 100%;
            margin: 0;
        }

        .view-section.active {
            display: block;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(3px); }
            to   { opacity: 1; transform: translateY(0); }
        }

        /* ── PROPERTIES PANEL (right) ────────────────────────── */
        .properties-panel {
            grid-area: props;
            background: var(--bg-surface);
            border-left: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            z-index: 90;
        }

        .prop-titlebar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 12px;
            height: 34px;
            background: var(--bg-panel);
            border-bottom: 1px solid var(--border);
            flex-shrink: 0;
        }
        .prop-titlebar span { font-size: 11.5px; font-weight: 600; color: var(--text-primary); }
        .prop-titlebar-icon svg { width:12px; height:12px; color: var(--text-muted); }

        .prop-body {
            flex: 1;
            overflow-y: auto;
            padding: 14px;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }

        .prop-section { display: flex; flex-direction: column; gap: 8px; }
        .prop-section-title {
            font-size: 9.5px;
            font-weight: 700;
            letter-spacing: 1px;
            text-transform: uppercase;
            color: var(--text-muted);
            border-bottom: 1px solid var(--border);
            padding-bottom: 6px;
            margin-bottom: 4px;
        }

        .prop-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 8px;
        }
        .prop-label { font-size: 11.5px; color: var(--text-secondary); }
        .prop-value {
            font-size: 11.5px;
            font-weight: 600;
            color: var(--text-primary);
            font-family: var(--font-mono);
        }
        .prop-value.highlight { color: var(--brand-color); }
        .prop-value.ok { color: var(--green); }
        .prop-value.warn { color: var(--amber); }
        .prop-value.danger { color: var(--red); }

        .prop-input {
            width: 100%;
            background: var(--bg-panel);
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            color: var(--text-primary);
            font-size: 11.5px;
            font-family: var(--font);
            padding: 4px 8px;
            outline: none;
            transition: border-color 0.12s;
        }
        .prop-input:focus { border-color: var(--border-focus); }

        .prop-select {
            width: 100%;
            background: var(--bg-panel);
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            color: var(--text-primary);
            font-size: 11.5px;
            font-family: var(--font);
            padding: 4px 8px;
            outline: none;
            cursor: pointer;
        }
        .prop-select:focus { border-color: var(--border-focus); }

        /* ── STATUS BAR ──────────────────────────────────────── */
        .statusbar {
            grid-area: statusbar;
            background: var(--bg-panel);
            border-top: 1px solid var(--border);
            display: flex;
            align-items: center;
            padding: 0 12px;
            gap: 16px;
            font-size: 10.5px;
            color: var(--text-secondary);
            user-select: none;
            z-index: 200;
        }
        .statusbar-item {
            display: flex;
            align-items: center;
            gap: 6px;
            white-space: nowrap;
        }
        .statusbar-sep {
            width: 1px;
            height: 12px;
            background: var(--border);
            flex-shrink: 0;
        }
        .statusbar-right { margin-left: auto; }
        .statusbar-badge {
            background: var(--brand-subtle);
            border: 1px solid rgba(0, 120, 212, 0.2);
            color: var(--brand-color);
            padding: 0 6px;
            border-radius: 2px;
            font-size: 9.5px;
            font-weight: 600;
        }
        body.dark-theme .statusbar-badge {
            border-color: rgba(0, 212, 255, 0.2);
        }

        /* ── GLOBAL COMPONENTS OVERRIDES ─────────────────────── */
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 16px;
            margin-bottom: 16px;
            box-shadow: var(--shadow-sm);
            transition: border-color 0.15s, box-shadow 0.15s;
        }
        .card:hover { border-color: var(--text-muted); box-shadow: var(--shadow-md); }
        .card-title {
            font-size: 13.5px;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .grid-dashboard-kpis {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 14px;
            margin-bottom: 16px;
        }
        .kpi-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 14px;
            display: flex;
            flex-direction: column;
            position: relative;
            overflow: hidden;
            box-shadow: var(--shadow-sm);
            transition: border-color 0.15s, transform 0.15s, box-shadow 0.15s;
        }
        .kpi-card:hover { border-color: var(--brand-color); transform: translateY(-1px); box-shadow: var(--shadow-md); }
        .kpi-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 10.5px;
            font-weight: 600;
            letter-spacing: 0.5px;
            color: var(--text-secondary);
            margin-bottom: 8px;
        }
        .kpi-value {
            font-size: 22px;
            font-weight: 700;
            color: var(--text-primary);
            font-family: var(--font-mono);
            line-height: 1.1;
        }
        .kpi-trend {
            font-size: 10.5px;
            margin-top: 5px;
            color: var(--text-secondary);
            display: flex;
            align-items: center;
            gap: 4px;
        }
        .kpi-accent-bar {
            position: absolute;
            bottom: 0; left: 0; right: 0;
            height: 2px;
        }

        button, .btn {
            font-family: var(--font);
            font-size: 12px;
            font-weight: 500;
            padding: 5px 12px;
            border-radius: var(--radius-sm);
            border: 1px solid var(--border);
            background: var(--bg-panel);
            color: var(--text-primary);
            cursor: pointer;
            transition: all 0.12s;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            outline: none;
        }
        button:hover, .btn:hover { background: var(--bg-hover); border-color: var(--text-muted); }
        button:active, .btn:active { transform: scale(0.98); }

        .btn-primary {
            background: var(--brand-subtle);
            border-color: rgba(0, 120, 212, 0.25);
            color: var(--brand-color);
        }
        .btn-primary:hover {
            background: rgba(0, 120, 212, 0.14);
            border-color: rgba(0, 120, 212, 0.4);
        }
        body.dark-theme .btn-primary {
            border-color: rgba(0, 212, 255, 0.25);
        }
        body.dark-theme .btn-primary:hover {
            background: rgba(0, 212, 255, 0.14);
            border-color: rgba(0, 212, 255, 0.4);
            box-shadow: var(--shadow-brand);
        }

        .btn-danger {
            background: var(--red-bg);
            border-color: rgba(168, 0, 0, 0.2);
            color: var(--red);
        }
        .btn-danger:hover { background: rgba(168, 0, 0, 0.12); border-color: var(--red); }
        body.dark-theme .btn-danger {
            background: var(--red-bg);
            border-color: rgba(248, 81, 73, 0.2);
            color: var(--red);
        }
        body.dark-theme .btn-danger:hover { background: rgba(248, 81, 73, 0.15); }

        .btn-secondary { background: var(--bg-panel); }

        label {
            font-size: 11px;
            font-weight: 600;
            color: var(--text-secondary);
            display: block;
            margin-bottom: 4px;
        }
        input[type="text"], input[type="number"], select, textarea {
            font-family: var(--font);
            font-size: 12px;
            padding: 6px 10px;
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            background: var(--bg-panel);
            color: var(--text-primary);
            outline: none;
            transition: border-color 0.12s;
            width: 100%;
        }
        input:focus, select:focus, textarea:focus {
            border-color: var(--border-focus);
            box-shadow: 0 0 0 2px var(--brand-glow);
        }

        input[type="range"] {
            -webkit-appearance: none;
            width: 100%;
            height: 3px;
            border-radius: 2px;
            background: var(--border);
            outline: none;
            border: none;
            padding: 0;
        }
        input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 12px; height: 12px;
            border-radius: 50%;
            background: var(--brand-color);
            cursor: pointer;
            transition: transform 0.1s;
        }
        input[type="range"]::-webkit-slider-thumb:hover { transform: scale(1.25); }

        .slider-group { margin-bottom: 12px; }
        .slider-header {
            display: flex;
            justify-content: space-between;
            font-size: 11px;
            margin-bottom: 4px;
        }
        .slider-label { color: var(--text-secondary); }
        .slider-val { color: var(--brand-color); font-weight: 600; font-family: var(--font-mono); }

        table { width: 100%; border-collapse: collapse; font-size: 12px; }
        th {
            background: var(--bg-panel);
            color: var(--text-secondary);
            font-weight: 600;
            font-size: 11px;
            letter-spacing: 0.3px;
            text-transform: uppercase;
            padding: 8px 10px;
            border-bottom: 1px solid var(--border);
            text-align: left;
        }
        td {
            padding: 9px 10px;
            border-bottom: 1px solid var(--border-light);
            color: var(--text-primary);
        }
        tr:hover td { background: var(--bg-hover); }

        .badge {
            display: inline-flex;
            align-items: center;
            padding: 2px 7px;
            border-radius: 3px;
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 0.3px;
            text-transform: uppercase;
        }
        .badge-success { background: var(--green-bg); color: var(--green); }
        .badge-warning { background: var(--amber-bg); color: var(--amber); }
        .badge-danger  { background: var(--red-bg);   color: var(--red);   }
        .badge-info    { background: var(--blue-bg);  color: var(--blue);  }
        .badge-teal    { background: var(--brand-subtle); color: var(--brand-color); }

        .section-header {
            margin-bottom: 16px;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }
        .section-title {
            font-size: 15px;
            font-weight: 600;
            color: var(--text-primary);
            letter-spacing: -0.2px;
        }
        .section-subtitle {
            font-size: 11.5px;
            color: var(--text-secondary);
            margin-top: 2px;
        }

        .control-row {
            display: flex;
            gap: 12px;
            margin-bottom: 12px;
            flex-wrap: wrap;
        }
        .control-group {
            display: flex;
            flex-direction: column;
            flex: 1;
            min-width: 160px;
        }
        
        .split-content {
            display: flex;
            gap: 16px;
            height: calc(100vh - var(--titlebar-h) - var(--toolbar-h) - var(--statusbar-h) - 48px);
        }
        .split-sidebar {
            width: 320px;
            display: flex;
            flex-direction: column;
            gap: 12px;
            flex-shrink: 0;
            overflow-y: auto;
        }
        .split-view {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 16px;
            overflow-y: auto;
        }
        
        /* ── APP GRID LAYOUT FRAME OVERRIDES ── */
"""

# New Shell HTML Block (replacing lines from header_start to main_start - 1)
NEW_SHELL_HTML = """    <div id="app-shell">
        <!-- TITLEBAR: MENUS SUPERIORES & WINDOW BRAND -->
        <div class="titlebar">
            <div class="titlebar-logo">
                <svg viewBox="0 0 24 24">
                    <path d="M12 2L2 22h20L12 2zm0 3.8L18.4 18H5.6L12 5.8zM11 10v4h2v-4h-2zm0 5v2h2v-2h-2z"/>
                </svg>
                <span>PetroFlow Enterprise</span>
            </div>
            
            <div class="menu-bar">
                <div class="menu-item" onclick="alert('Proyecto Guardado Correctamente: PetroFlow_Refinery_Optimization_v2.pet')">Archivo</div>
                <div class="menu-item" onclick="alert('Edición de diagrama habilitada')">Editar</div>
                <div class="menu-item" onclick="alert('Cambiando densidad de vista...')">Ver</div>
                <div class="menu-item" onclick="alert('Iniciando pre-simulador hidráulico...')">Simular</div>
                <div class="menu-item" onclick="alert('Ejecutando árbol recursivo FTA...')">Riesgo</div>
                <div class="menu-item" onclick="alert('Abriendo herramientas de calibración...')">Herramientas</div>
                <div class="menu-item" onclick="alert('Manual de PetroFlow v2.0 - Jhon Villegas')">Ayuda</div>
            </div>

            <div class="titlebar-center">PetroFlow Enterprise v2.0 - Consola de Control Industrial</div>

            <div class="titlebar-right">
                <div class="titlebar-badge">
                    <span class="status-dot dot-green" id="headerApiDot"></span>
                    <span>API: <strong id="headerApiText">Conectando...</strong></span>
                </div>
                
                <!-- Dual-Theme Light/Dark Switcher Button -->
                <button id="theme-toggle-btn" class="tb-btn" title="Alternar Tema Claro / Oscuro" style="padding:0 8px; height:24px; border-radius:4px; display:flex; align-items:center; justify-content:center; border:1px solid var(--border);">
                    <!-- Moon icon (shows in light mode to switch to dark) -->
                    <svg id="theme-moon-icon" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" style="display:none;"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
                    <!-- Sun icon (shows in dark mode to switch to light) -->
                    <svg id="theme-sun-icon" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" style="display:none;"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
                </button>

                <div class="user-profile" style="position:relative; display:flex; align-items:center; gap:8px;">
                    <div class="settings-icon" onclick="toggleSettingsModal()" style="cursor: pointer; display: flex; align-items: center;" title="Ajustes de IA">
                        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" style="color: var(--text-secondary);">
                            <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l-.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
                        </svg>
                    </div>
                    <div class="user-avatar-sm" id="headerUserAvatar" onclick="document.getElementById('user-menu-dropdown').style.display=document.getElementById('user-menu-dropdown').style.display==='block'?'none':'block'">AD</div>
                    <span id="headerUserName" class="titlebar-username" onclick="document.getElementById('user-menu-dropdown').style.display=document.getElementById('user-menu-dropdown').style.display==='block'?'none':'block'">Cargando...</span>
                    
                    <!-- User Dropdown Menu -->
                    <div id="user-menu-dropdown" style="display:none; position:absolute; top:calc(100% + 8px); right:0; background:var(--bg-card); border:1px solid var(--border); border-radius:6px; box-shadow:var(--shadow-lg); min-width:180px; z-index:1000; overflow:hidden;">
                        <div style="padding:12px 14px; border-bottom:1px solid var(--border-light);">
                            <div style="font-size:10px; color:var(--text-muted); margin-bottom:2px; font-weight:600;">SESIÓN ACTIVA COMO:</div>
                            <div id="dropdown-user-name" style="font-size:12px; font-weight:700; color:var(--text-primary);">Administrador</div>
                        </div>
                        <button onclick="logout()" style="width:100%; display:flex; align-items:center; gap:8px; padding:10px 14px; background:none; border:none; cursor:pointer; font-size:12px; color:var(--red); font-family:var(--font); transition:background 0.15s; font-weight:600;" onmouseover="this.style.background='var(--bg-hover)'" onmouseout="this.style.background='none'">
                            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
                            Cerrar Sesión
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- TOOLBAR: ACCIONES RÁPIDAS & SIMULADOR CONTROLS -->
        <div class="toolbar">
            <button class="tb-btn" onclick="alert('Nuevo proyecto creado!')" title="Nuevo Proyecto (Ctrl+N)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/></svg>
                Nuevo
            </button>
            <button class="tb-btn" onclick="alert('Cargando archivo de proyecto...')" title="Abrir Proyecto (Ctrl+O)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/><polygon points="12 11 12 17 22 17 22 11 12 11"/></svg>
                Abrir...
            </button>
            <button class="tb-btn" onclick="alert('Proyecto Guardado Exitosamente')" title="Guardar Proyecto (Ctrl+S)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
                Guardar
            </button>
            
            <div class="tb-sep"></div>

            <button class="tb-btn tb-primary" onclick="const runSimBtn = document.querySelector('#view-piping .fluent-btn-primary') || document.querySelector('#view-equipment .fluent-btn-primary'); if(runSimBtn) runSimBtn.click(); else alert('Iniciando Simulación Hidráulica Combinada...');" title="Correr Simulación Completa (F5)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                Correr Simulación
            </button>
            
            <button class="tb-btn tb-risk" onclick="switchView('view-reliability')" title="Abrir Reliability Hub e Historial CMMS">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                Análisis de Riesgo
            </button>

            <button class="tb-btn" onclick="switchView('view-operators')" title="Ver Reporte e Integración SAP">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
                Ordenes de Trabajo SAP
            </button>

            <div class="toolbar-right">
                <div class="statusbar-item" style="gap: 5px;">
                    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="var(--text-secondary)" stroke-width="2"><path d="M4 7h16M4 12h16M4 17h16"/></svg>
                    <span style="color: var(--text-secondary); font-size: 11px; font-weight: 600;">Sistema:</span>
                    <select id="unit-system-selector" onchange="toggleUnitSystem(this.value)" style="background: var(--bg-panel); color: var(--text-primary); border: 1px solid var(--border); border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: 600; cursor: pointer; outline: none; transition: border-color 0.15s;">
                        <option value="SI">Internacional (SI)</option>
                        <option value="Imperial">Imperial (US)</option>
                    </select>
                </div>
            </div>
        </div>

        <!-- SIDEBAR: GRUPOS COLAPSABLES DE NAVEGACIÓN -->
        <nav class="sidebar">
            <div class="nav-group">
                <span class="nav-group-label">DISEÑO & MODELADO</span>
                <div class="nav-item active" onclick="switchView('view-home')" id="nav-view-home">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
                    <span>Dashboard Operativo</span>
                </div>
                <div class="nav-item" onclick="switchView('view-piping')" id="nav-view-piping">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M16.2 7.8l-2 2a4 4 0 1 0-4.2 4.2l-2 2"/><path d="M15 15l5 5"/><path d="M9 9l-5-5"/></svg>
                    <span>Simulador de Línea</span>
                </div>
                <div class="nav-item" onclick="switchView('view-equipment')" id="nav-view-equipment">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"/><rect x="2" y="14" width="20" height="8" rx="2" ry="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/></svg>
                    <span>Gemelos de Equipos</span>
                </div>
                <div class="nav-item" onclick="switchView('view-well-analysis')" id="nav-view-well-analysis">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
                    <span>Análisis de Pozos</span>
                </div>
            </div>
            
            <div class="nav-group">
                <span class="nav-group-label">CÁLCULO & ANÁLISIS</span>
                <div class="nav-item" onclick="switchView('view-fft')" id="nav-view-fft">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
                    <span>Análisis Espectral (FFT)</span>
                </div>
                <div class="nav-item" onclick="switchView('view-reliability')" id="nav-view-reliability">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20v-6M9 20v-10M15 20v-4M18 20V4M6 20v-2"/></svg>
                    <span>Reliability Hub</span>
                </div>
            </div>

            <div class="nav-group">
                <span class="nav-group-label">OPERACIONES & SOPORTE</span>
                <div class="nav-item" onclick="switchView('view-operators')" id="nav-view-operators">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                    <span>Operarios & SAP CMMS</span>
                </div>
                <div class="nav-item" onclick="switchView('view-ai')" id="nav-view-ai">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>
                    <span>Copiloto Diagnóstico IA</span>
                </div>
            </div>
            
            <div class="sidebar-footer">
                <p>PetroFlow Suite v2.0</p>
                <p>Jhon Villegas | © 2026</p>
            </div>
        </nav>
"""

# New Workspace Closing + Panels HTML Block (replacing line workspace_end)
NEW_WORKSPACE_CLOSE_AND_PANELS = """    </main><!-- main canvas ends -->
    
    <!-- PROPERTIES PANEL (derecho, contextual) -->
    <aside class="properties-panel" id="properties-panel">
        <div class="prop-titlebar">
            <span>Panel de Propiedades</span>
            <div class="prop-titlebar-icon">
                <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
            </div>
        </div>
        <div class="prop-body" id="prop-body">
            <!-- Rendered dynamically by javascript depending on the active view -->
        </div>
    </aside>

    <!-- STATUS BAR (inferior) -->
    <div class="statusbar">
        <div class="statusbar-item">
            <span>Proyecto:</span>
            <strong style="color: var(--text-primary);">PetroFlow_Refinery_Optimization_v2.pet</strong>
        </div>
        <div class="statusbar-sep"></div>
        <div class="statusbar-item">
            <span class="status-dot dot-green"></span>
            <span>Unidades: <strong id="statusbar-units">Internacional (SI)</strong></span>
        </div>
        <div class="statusbar-sep"></div>
        <div class="statusbar-item">
            <span class="status-dot dot-teal"></span>
            <span>Simulador Hidráulico: Swamee-Jain OK</span>
        </div>
        <div class="statusbar-sep"></div>
        <div class="statusbar-item">
            <span class="status-dot dot-grey" id="statusbar-ai-dot"></span>
            <span>Copiloto: Activo</span>
        </div>
        <div class="statusbar-right statusbar-item">
            <span class="statusbar-badge">MODO DIARIO</span>
            <span>Cursor: X: <strong id="cursor-x">452.4</strong> Y: <strong id="cursor-y">890.1</strong></span>
        </div>
    </div>
</div><!-- app-shell ends -->
"""

# Append Theme Toggle + Properties JS (inserting before body_end)
THEME_SWITCHER_AND_PROPS_JS = """    <!-- Theme Toggle, Properties Panel, and Cursor Tracking Script -->
    <script>
        // Theme Toggle Functionality
        function initTheme() {
            const savedTheme = localStorage.getItem('petroflow-theme') || 'dark';
            const body = document.body;
            const moonIcon = document.getElementById('theme-moon-icon');
            const sunIcon = document.getElementById('theme-sun-icon');
            
            if (savedTheme === 'dark') {
                body.classList.add('dark-theme');
                if (moonIcon) moonIcon.style.display = 'none';
                if (sunIcon) sunIcon.style.display = 'block';
            } else {
                body.classList.remove('dark-theme');
                if (moonIcon) moonIcon.style.display = 'block';
                if (sunIcon) sunIcon.style.display = 'none';
            }
        }

        function toggleTheme() {
            const body = document.body;
            const moonIcon = document.getElementById('theme-moon-icon');
            const sunIcon = document.getElementById('theme-sun-icon');
            
            if (body.classList.contains('dark-theme')) {
                body.classList.remove('dark-theme');
                localStorage.setItem('petroflow-theme', 'light');
                if (moonIcon) moonIcon.style.display = 'block';
                if (sunIcon) sunIcon.style.display = 'none';
            } else {
                body.classList.add('dark-theme');
                localStorage.setItem('petroflow-theme', 'dark');
                if (moonIcon) moonIcon.style.display = 'none';
                if (sunIcon) sunIcon.style.display = 'block';
            }
        }

        // Contextual Properties Panel Updates
        function updatePropertiesPanel(viewId) {
            const propBody = document.getElementById('prop-body');
            if (!propBody) return;
            
            let html = '';
            
            if (viewId === 'view-home') {
                html = `
                    <div class="prop-section">
                        <span class="prop-section-title">INDICADORES DE PLANTA</span>
                        <div class="prop-row">
                            <span class="prop-label">OEE Objetivo:</span>
                            <span class="prop-value highlight">95.0%</span>
                        </div>
                        <div class="prop-row">
                            <span class="prop-label">OEE Actual:</span>
                            <span class="prop-value ok">94.8%</span>
                        </div>
                        <div class="prop-row">
                            <span class="prop-label">Disponibilidad:</span>
                            <span class="prop-value">97.2%</span>
                        </div>
                        <div class="prop-row">
                            <span class="prop-label">Rendimiento:</span>
                            <span class="prop-value">98.5%</span>
                        </div>
                    </div>
                    <div class="prop-section">
                        <span class="prop-section-title">ESTADO DE ACTIVOS</span>
                        <div class="prop-row">
                            <span class="prop-label">Bombas Operativas:</span>
                            <span class="prop-value">4 / 4</span>
                        </div>
                        <div class="prop-row">
                            <span class="prop-label">Líneas en Simulación:</span>
                            <span class="prop-value">2</span>
                        </div>
                        <div class="prop-row">
                            <span class="prop-label">Alertas Activas:</span>
                            <span class="prop-value ok">0</span>
                        </div>
                    </div>
                    <div class="prop-section">
                        <span class="prop-section-title">INTEGRACIÓN</span>
                        <div class="prop-row">
                            <span class="prop-label">Servicio API:</span>
                            <span class="prop-value ok">Conectado</span>
                        </div>
                        <div class="prop-row">
                            <span class="prop-label">Base de Datos:</span>
                            <span class="prop-value ok">SQLITE</span>
                        </div>
                    </div>
                `;
            } else if (viewId === 'view-piping') {
                html = `
                    <div class="prop-section">
                        <span class="prop-section-title">PARÁMETROS FÍSICOS</span>
                        <div class="prop-row">
                            <span class="prop-label">Diámetro Tubería:</span>
                            <span class="prop-value">8.0 in</span>
                        </div>
                        <div class="prop-row">
                            <span class="prop-label">Longitud Línea:</span>
                            <span class="prop-value">1200 m</span>
                        </div>
                        <div class="prop-row">
                            <span class="prop-label">Rugosidad Rel.:</span>
                            <span class="prop-value">0.045 mm</span>
                        </div>
                        <div class="prop-row">
                            <span class="prop-label">Inclinación:</span>
                            <span class="prop-value">2.5 deg</span>
                        </div>
                    </div>
                    <div class="prop-section">
                        <span class="prop-section-title">MODELO HIDRÁULICO</span>
                        <div class="prop-row">
                            <span class="prop-label">Fricción:</span>
                            <span class="prop-value highlight">Swamee-Jain</span>
                        </div>
                        <div class="prop-row">
                            <span class="prop-label">Multifásico:</span>
                            <span class="prop-value">Beggs & Brill</span>
                        </div>
                        <div class="prop-row">
                            <span class="prop-label">Fluido:</span>
                            <span class="prop-value">Crudo Liviano</span>
                        </div>
                    </div>
                    <div class="prop-section">
                        <span class="prop-section-title">CONTROLES DE ENTRADA</span>
                        <label for="prop-flow-val">Caudal Deseado (m³/h)</label>
                        <input type="number" id="prop-flow-val" class="prop-input" value="150" onchange="
                            const mainInput = document.getElementById('flow-rate');
                            if(mainInput) { mainInput.value = this.value; mainInput.dispatchEvent(new Event('input')); }
                        ">
                    </div>
                `;
            } else if (viewId === 'view-equipment') {
                html = `
                    <div class="prop-section">
                        <span class="prop-section-title">OPERACIÓN DE BOMBA</span>
                        <div class="prop-row">
                            <span class="prop-label">Velocidad Motor:</span>
                            <span class="prop-value highlight" id="prop-eq-speed">1800 RPM</span>
                        </div>
                        <div class="prop-row">
                            <span class="prop-label">Eficiencia Motor:</span>
                            <span class="prop-value ok">92.4%</span>
                        </div>
                        <div class="prop-row">
                            <span class="prop-label">Presión Succión:</span>
                            <span class="prop-value">2.4 bar</span>
                        </div>
                        <div class="prop-row">
                            <span class="prop-label">Presión Descarga:</span>
                            <span class="prop-value highlight">8.5 bar</span>
                        </div>
                    </div>
                    <div class="prop-section">
                        <span class="prop-section-title">LEYES DE AFINIDAD</span>
                        <div class="prop-row">
                            <span class="prop-label">Factor Velocidad (s):</span>
                            <span class="prop-value">1.00</span>
                        </div>
                        <div class="prop-row">
                            <span class="prop-label">Arreglo Bombas:</span>
                            <span class="prop-value">Serie / Paralelo</span>
                        </div>
                    </div>
                    <div class="prop-section">
                        <span class="prop-section-title">CONTROL REMOTO</span>
                        <label for="prop-pump-speed-slider">Ajuste de Velocidad (%)</label>
                        <input type="range" id="prop-pump-speed-slider" min="50" max="120" value="100" style="margin-top:6px;" oninput="
                            const mainSlider = document.getElementById('pump-speed-1') || document.getElementById('pump-speed');
                            if(mainSlider) { mainSlider.value = this.value; mainSlider.dispatchEvent(new Event('input')); }
                            document.getElementById('prop-eq-speed').innerText = Math.round(1800 * (this.value / 100)) + ' RPM';
                        ">
                    </div>
                `;
            } else if (viewId === 'view-well-analysis') {
                html = `
                    <div class="prop-section">
                        <span class="prop-section-title">RESERVORIO & POZO</span>
                        <div class="prop-row">
                            <span class="prop-label">Presión Estática (Pr):</span>
                            <span class="prop-value">3200 psi</span>
                        </div>
                        <div class="prop-row">
                            <span class="prop-label">Índice Prod. (J):</span>
                            <span class="prop-value">1.8 bbl/d/psi</span>
                        </div>
                        <div class="prop-row">
                            <span class="prop-label">Presión Fondo (Pwf):</span>
                            <span class="prop-value highlight">1500 psi</span>
                        </div>
                    </div>
                    <div class="prop-section">
                        <span class="prop-section-title">PROPIEDADES FLUIDOS</span>
                        <div class="prop-row">
                            <span class="prop-label">Corte de Agua (WC):</span>
                            <span class="prop-value">12%</span>
                        </div>
                        <div class="prop-row">
                            <span class="prop-label">Gas-Oil Ratio (GOR):</span>
                            <span class="prop-value">450 scf/bbl</span>
                        </div>
                        <div class="prop-row">
                            <span class="prop-label">Gravedad API:</span>
                            <span class="prop-value">32° API</span>
                        </div>
                    </div>
                    <div class="prop-section">
                        <span class="prop-section-title">MÉTODO DE ANÁLISIS</span>
                        <div class="prop-row">
                            <span class="prop-label">IPR Engine:</span>
                            <span class="prop-value highlight">Vogel (1968)</span>
                        </div>
                    </div>
                `;
            } else if (viewId === 'view-fft') {
                html = `
                    <div class="prop-section">
                        <span class="prop-section-title">ADQUISICIÓN SEÑALES</span>
                        <div class="prop-row">
                            <span class="prop-label">Frecuencia Vibración:</span>
                            <span class="prop-value highlight">60 Hz</span>
                        </div>
                        <div class="prop-row">
                            <span class="prop-label">Frecuencia Muestreo:</span>
                            <span class="prop-value">1024 Hz</span>
                        </div>
                        <div class="prop-row">
                            <span class="prop-label">Puntos Muestra (N):</span>
                            <span class="prop-value">512</span>
                        </div>
                    </div>
                    <div class="prop-section">
                        <span class="prop-section-title">PROCESAMIENTO DIGITAL</span>
                        <div class="prop-row">
                            <span class="prop-label">Ventana FFT:</span>
                            <span class="prop-value highlight">Hanning</span>
                        </div>
                        <div class="prop-row">
                            <span class="prop-label">Algoritmo FFT:</span>
                            <span class="prop-value">NumPy Cooley-Tukey</span>
                        </div>
                    </div>
                `;
            } else if (viewId === 'view-reliability') {
                html = `
                    <div class="prop-section">
                        <span class="prop-section-title">AJUSTE WEIBULL</span>
                        <div class="prop-row">
                            <span class="prop-label">Beta (β):</span>
                            <span class="prop-value highlight" id="prop-weibull-beta">1.85</span>
                        </div>
                        <div class="prop-row">
                            <span class="prop-label">Eta (η):</span>
                            <span class="prop-value" id="prop-weibull-eta">4200 h</span>
                        </div>
                        <div class="prop-row">
                            <span class="prop-label">Modo Falla:</span>
                            <span class="prop-value warn" id="prop-weibull-mode">Desgaste (Beta > 1)</span>
                        </div>
                    </div>
                    <div class="prop-section">
                        <span class="prop-section-title">MÉTRICAS DE FIABILIDAD</span>
                        <div class="prop-row">
                            <span class="prop-label">MTBF:</span>
                            <span class="prop-value">3850 hours</span>
                        </div>
                        <div class="prop-row">
                            <span class="prop-label">MTTR Promedio:</span>
                            <span class="prop-value">14.2 hours</span>
                        </div>
                    </div>
                `;
            } else if (viewId === 'view-operators') {
                html = `
                    <div class="prop-section">
                        <span class="prop-section-title">ESTADO ORDENES CMMS</span>
                        <div class="prop-row">
                            <span class="prop-label">Operarios Libres:</span>
                            <span class="prop-value ok">4</span>
                        </div>
                        <div class="prop-row">
                            <span class="prop-label">Ordenes en Curso:</span>
                            <span class="prop-value">3</span>
                        </div>
                        <div class="prop-row">
                            <span class="prop-label">Sincronización SAP:</span>
                            <span class="prop-value ok">Conectado</span>
                        </div>
                    </div>
                `;
            } else if (viewId === 'view-ai') {
                html = `
                    <div class="prop-section">
                        <span class="prop-section-title">COPILOTO AGENTE</span>
                        <div class="prop-row">
                            <span class="prop-label">Modelo LLM:</span>
                            <span class="prop-value highlight">Gemini 3.5 Flash</span>
                        </div>
                        <div class="prop-row">
                            <span class="prop-label">Temperatura:</span>
                            <span class="prop-value">0.2 (Predictivo)</span>
                        </div>
                        <div class="prop-row">
                            <span class="prop-label">Estado Agente:</span>
                            <span class="prop-value ok">Online / Listo</span>
                        </div>
                    </div>
                `;
            }
            
            propBody.innerHTML = html;
        }

        // Monkey-patch standard switchView to trigger properties panel and change sidebar highlight
        document.addEventListener('DOMContentLoaded', () => {
            initTheme();
            
            // Enable Theme Switcher button click
            const btn = document.getElementById('theme-toggle-btn');
            if (btn) btn.addEventListener('click', toggleTheme);

            // Wrap switchView
            if (typeof switchView === 'function') {
                const originalSwitchView = switchView;
                switchView = function(viewId) {
                    originalSwitchView(viewId);
                    updatePropertiesPanel(viewId);
                    
                    // Track properties open state
                    document.body.classList.add('properties-open');
                };
                
                // Initialize for active view
                switchView('view-home');
            }

            // Sync units selector in statusbar with changes in top selector
            const unitSelector = document.getElementById('unit-system-selector');
            const statusbarUnits = document.getElementById('statusbar-units');
            if (unitSelector && statusbarUnits) {
                unitSelector.addEventListener('change', (e) => {
                    statusbarUnits.innerText = e.target.value === 'SI' ? 'Internacional (SI)' : 'Imperial (US)';
                });
            }

            // Cursor Coordinates Simulator
            const mainCanvas = document.querySelector('main');
            const cursorX = document.getElementById('cursor-x');
            const cursorY = document.getElementById('cursor-y');
            if (mainCanvas && cursorX && cursorY) {
                mainCanvas.addEventListener('mousemove', (e) => {
                    const rect = mainCanvas.getBoundingClientRect();
                    const x = (e.clientX - rect.left).toFixed(1);
                    const y = (e.clientY - rect.top).toFixed(1);
                    cursorX.innerText = x;
                    cursorY.innerText = y;
                });
            }
            
            // Periodically pulse status indicators to feel alive
            setInterval(() => {
                const aiDot = document.getElementById('statusbar-ai-dot');
                if (aiDot) {
                    aiDot.className = 'status-dot dot-teal';
                    setTimeout(() => {
                        aiDot.className = 'status-dot dot-grey';
                    }, 500);
                }
            }, 3000);
        });
    </script>
"""

# Let's rebuild the file step by step!
new_lines = []

# 1. Everything before the style tag
new_lines.extend(lines[:style_start+1])

# 2. Add Google Fonts Link for Inter
new_lines.append('    <link rel="preconnect" href="https://fonts.googleapis.com">\\n')
new_lines.append('    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">\\n')

# 3. Add New CSS Core Block
new_lines.append(NEW_CSS_CORE)

# 4. Add the preserved view-specific styles (from ops_widget_comment to style_end)
new_lines.extend(lines[ops_widget_comment:style_end+1])

# 5. Everything between style_end and header_start
new_lines.extend(lines[style_end+1:header_start])

# 6. Add the New Shell HTML Block
new_lines.append(NEW_SHELL_HTML)

# 7. Everything from main_start to main_end
new_lines.extend(lines[main_start:main_end+1])

# 8. Add the workspace closing + panels HTML
new_lines.append(NEW_WORKSPACE_CLOSE_AND_PANELS)

# 9. Everything from workspace_end+1 to body_end
new_lines.extend(lines[workspace_end+1:body_end])

# 10. Add the Theme Switcher + Properties dynamic scripts
new_lines.append(THEME_SWITCHER_AND_PROPS_JS)

# 11. Keep the body and html ending tags
new_lines.extend(lines[body_end:])

print(f"Reconstructed index.html with {len(new_lines)} lines.")

# Write the new content in-place
with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
    fh.writelines(new_lines)

print("index.html rewritten successfully!")
