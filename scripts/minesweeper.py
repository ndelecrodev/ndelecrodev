#!/usr/bin/env python3
"""Gera um campo minado animado a partir do calendário de contribuições do GitHub.

Cada dia do último ano vira uma casa do tabuleiro (7 linhas x ~53 colunas).
- Dias com contribuição são casas seguras, tingidas conforme a intensidade.
- Dias sem contribuição podem esconder uma mina (posição fixa, sorteada com seed).
- A animação abre o tabuleiro da esquerda para a direita, marca as minas e recomeça.

Uso: minesweeper.py <usuario> <pasta-de-saida>
Lê o token de GH_TOKEN ou GITHUB_TOKEN. Sem token, usa dados de exemplo.
"""
import json, os, random, sys, urllib.request

CELL, GAP = 14, 2
PITCH = CELL + GAP
PAD_X, BOARD_Y = 16, 58
CYCLE = 18.0   # duração total do ciclo, em segundos
SWEEP = 9.0    # tempo para abrir o tabuleiro inteiro

PALETTES = {
    "claro": dict(bg="#ffffff", panel="#d0d7de", panel_edge="#8c959f", hidden="#c6ced8", hidden_hi="#ffffff",
                  hidden_lo="#8c959f", levels=["#ebedf0", "#cfe2ff", "#9ec5fe", "#5b9cf6", "#2f6feb"],
                  grid="#d0d7de", face="#f5c518", ink="#1f2328"),
    "escuro": dict(bg="#0d1117", panel="#21262d", panel_edge="#0d1117", hidden="#30363d", hidden_hi="#4b535d",
                   hidden_lo="#161b22", levels=["#161b22", "#0c2d6b", "#1158c7", "#2f6feb", "#79b8ff"],
                   grid="#21262d", face="#f5c518", ink="#e6edf3"),
}
NUM_COLORS = {1: "#2f6feb", 2: "#2da44e", 3: "#cf222e", 4: "#6639ba", 5: "#9a6700", 6: "#0a7a7a", 7: "#57606a", 8: "#8c959f"}


def fetch(user):
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        rnd = random.Random(1)
        return [[max(0, int(rnd.gauss(1.2, 2))) if rnd.random() > .4 else 0 for _ in range(7)] for _ in range(53)]
    q = {"query": "query($u:String!){user(login:$u){contributionsCollection{contributionCalendar{weeks{contributionDays{contributionCount weekday}}}}}}",
         "variables": {"u": user}}
    req = urllib.request.Request("https://api.github.com/graphql", json.dumps(q).encode(),
                                 {"Authorization": f"bearer {token}", "Content-Type": "application/json"})
    data = json.load(urllib.request.urlopen(req, timeout=30))
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    grid = []
    for w in weeks:
        col = [None] * 7
        for d in w["contributionDays"]:
            col[d["weekday"]] = d["contributionCount"]
        grid.append(col)
    return grid


def level(n, top):
    if n <= 0: return 0
    r = n / max(top, 1)
    return 1 if r <= .25 else 2 if r <= .5 else 3 if r <= .75 else 4


def build(grid, pal):
    cols = len(grid)
    rnd = random.Random(2024)
    counts = [[c for c in col] for col in grid]
    top = max((c for col in counts for c in col if c), default=1)
    total = sum(c for col in counts for c in col if c)
    mine = [[False] * 7 for _ in range(cols)]
    for x in range(cols):
        for y in range(7):
            if counts[x][y] == 0 and rnd.random() < .16:
                mine[x][y] = True
    n_mines = sum(m for col in mine for m in col)

    def near(x, y):
        return sum(mine[i][j] for i in range(max(0, x - 1), min(cols, x + 2))
                   for j in range(max(0, y - 1), min(7, y + 2)) if (i, j) != (x, y))

    W = PAD_X * 2 + cols * PITCH - GAP
    H = BOARD_Y + 7 * PITCH - GAP + PAD_X
    base, over, flags = [], [], []
    for x in range(cols):
        for y in range(7):
            if counts[x][y] is None:
                continue
            px, py = PAD_X + x * PITCH, BOARD_Y + y * PITCH
            delay = round(x / cols * SWEEP + rnd.random() * .5, 2)
            if mine[x][y]:
                base.append(f'<rect x="{px}" y="{py}" width="{CELL}" height="{CELL}" rx="2" fill="{pal["levels"][0]}"/>')
                # mina: só aparece marcada com bandeira no fim da varredura
                fd = round(SWEEP + 0.4 + rnd.random() * 1.6, 2)
                flags.append(f'<g transform="translate({px} {py})"><g class="fl" style="animation-delay:{fd}s">'
                             f'<path d="M4 11.5V3.2" stroke="{pal["ink"]}" stroke-width="1.3"/>'
                             f'<path d="M4 3.2 11 5.6 4 8z" fill="#cf222e"/><path d="M2.5 11.8h5" stroke="{pal["ink"]}" stroke-width="1.3"/></g></g>')
            else:
                lv = level(counts[x][y], top)
                base.append(f'<rect x="{px}" y="{py}" width="{CELL}" height="{CELL}" rx="2" fill="{pal["levels"][lv]}"/>')
                n = near(x, y)
                if n:
                    base.append(f'<text x="{px + CELL / 2}" y="{py + 11}" text-anchor="middle" font-size="11" font-weight="700" '
                                f'fill="{NUM_COLORS[n]}">{n}</text>')
            over.append(f'<g class="cv" style="animation-delay:{delay}s"><rect x="{px}" y="{py}" width="{CELL}" height="{CELL}" rx="2" fill="{pal["hidden"]}"/>'
                        f'<path d="M{px + 1} {py + CELL - 1}V{py + 1}H{px + CELL - 1}" fill="none" stroke="{pal["hidden_hi"]}" stroke-width="1.4"/>'
                        f'<path d="M{px + CELL - 1} {py + 1}V{py + CELL - 1}H{px + 1}" fill="none" stroke="{pal["hidden_lo"]}" stroke-width="1.4"/></g>')

    def lcd(x, value, w):
        s = f"{value:0{4}d}"[-4:]
        return (f'<rect x="{x}" y="14" width="{w}" height="30" rx="3" fill="#000"/>'
                f'<text x="{x + w - 6}" y="37" text-anchor="end" font-family="Consolas,Menlo,monospace" font-size="24" '
                f'font-weight="700" fill="#ff3b30" letter-spacing="2">{s}</text>')

    cx = W / 2
    face = (f'<circle cx="{cx}" cy="29" r="14" fill="{pal["face"]}" stroke="#7a5d00" stroke-width="1.4"/>'
            f'<rect class="blink" x="{cx - 6.5}" y="23.5" width="3" height="5" rx="1.5" fill="#222"/>'
            f'<rect class="blink" x="{cx + 3.5}" y="23.5" width="3" height="5" rx="1.5" fill="#222"/>'
            f'<path d="M{cx - 6} 33.5q6 5.5 12 0" fill="none" stroke="#222" stroke-width="1.6" stroke-linecap="round"/>')
    css = f"""
    .cv{{animation:open {CYCLE}s linear infinite}}
    @keyframes open{{0%{{opacity:1}}0.8%{{opacity:0}}92%{{opacity:0}}93.5%{{opacity:1}}100%{{opacity:1}}}}
    .fl{{opacity:0;animation:flag {CYCLE}s linear infinite}}
    @keyframes flag{{0%{{opacity:0;transform:translateY(0)}}1%{{opacity:1}}60%{{opacity:1}}62%{{opacity:0}}100%{{opacity:0}}}}
    .blink{{animation:blink 4.5s infinite;transform-box:fill-box;transform-origin:center}}
    @keyframes blink{{0%,92%,100%{{transform:scaleY(1)}}96%{{transform:scaleY(.1)}}}}
    @media (prefers-reduced-motion:reduce){{.cv,.fl,.blink{{animation:none}}.cv{{opacity:0}}.fl{{opacity:1}}}}
    """
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="Campo minado montado com as minhas contribuições do último ano">'
            f'<style>{css}</style><rect width="{W}" height="{H}" rx="10" fill="{pal["bg"]}"/>'
            f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="9" fill="none" stroke="{pal["grid"]}" stroke-width="2"/>'
            f'<g font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">{lcd(PAD_X, n_mines, 70)}{lcd(W - PAD_X - 70, total, 70)}{face}'
            f'{"".join(base)}{"".join(over)}{"".join(flags)}</g></svg>')


def main():
    user, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    grid = fetch(user)
    for nome, suf in (("claro", ""), ("escuro", "-dark")):
        path = os.path.join(out, f"minesweeper{suf}.svg")
        open(path, "w", encoding="utf-8").write(build(grid, PALETTES[nome]))
        print("gerado", path)


if __name__ == "__main__":
    main()
