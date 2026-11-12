#!/usr/bin/env python3
"""Gera um gráfico de atividade (últimos 90 dias) a partir das contribuições do GitHub.

Mostra barras diárias discretas e uma linha suavizada (média móvel de 7 dias) que se
desenha ao carregar, com os totais no topo. Saída: activity.svg e activity-dark.svg.

Uso: activity.py <usuario> <pasta-de-saida>
Lê o token de GH_TOKEN ou GITHUB_TOKEN. Sem token, usa dados de exemplo.
"""
import datetime as dt, json, math, os, random, sys, urllib.request

DIAS = 90
W, H = 880, 250
L, R, T, B = 48, 20, 82, 34   # margens do gráfico
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

TEMAS = {
    "claro": dict(bg="#ffffff", borda="#d0d7de", texto="#1f2328", suave="#656d76", grade="#eaeef2",
                  barra="#b6d4fe", linha="#2f6feb", area="#2f6feb", destaque="#0969da"),
    "escuro": dict(bg="#0d1117", borda="#21262d", texto="#e6edf3", suave="#8b949e", grade="#21262d",
                   barra="#16356b", linha="#58a6ff", area="#2f6feb", destaque="#79b8ff"),
}


def buscar(user):
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    hoje = dt.date.today()
    if not token:
        rnd = random.Random(5)
        return [(hoje - dt.timedelta(days=DIAS - 1 - i), 0 if rnd.random() < .45 else int(rnd.gauss(5, 4)) % 20) for i in range(DIAS)]
    q = {"query": "query($u:String!){user(login:$u){contributionsCollection{contributionCalendar{weeks{contributionDays{contributionCount date}}}}}}",
         "variables": {"u": user}}
    req = urllib.request.Request("https://api.github.com/graphql", json.dumps(q).encode(),
                                 {"Authorization": f"bearer {token}", "Content-Type": "application/json"})
    dados = json.load(urllib.request.urlopen(req, timeout=30))
    semanas = dados["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    dias = [(dt.date.fromisoformat(d["date"]), d["contributionCount"]) for s in semanas for d in s["contributionDays"]]
    dias = [d for d in dias if d[0] <= hoje]
    return dias[-DIAS:]


def suave(pontos):
    """Curva Catmull-Rom convertida para Bézier cúbica."""
    d = f"M{pontos[0][0]:.1f} {pontos[0][1]:.1f}"
    for i in range(len(pontos) - 1):
        p0 = pontos[max(i - 1, 0)]; p1 = pontos[i]; p2 = pontos[i + 1]; p3 = pontos[min(i + 2, len(pontos) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {p2[0]:.1f} {p2[1]:.1f}"
    return d


def desenhar(dias, t):
    valores = [v for _, v in dias]
    n = len(valores)
    total = sum(valores)
    ativos = sum(1 for v in valores if v)
    melhor = max(range(n), key=lambda i: valores[i])
    media7 = [sum(valores[max(0, i - 6):i + 1]) / len(valores[max(0, i - 6):i + 1]) for i in range(n)]
    topo = max(max(valores), 4)
    passo = 5 if topo <= 25 else 10 if topo <= 60 else 20
    topo = math.ceil(topo / passo) * passo
    cw, ch = W - L - R, H - T - B
    X = lambda i: L + cw * i / (n - 1)
    Y = lambda v: T + ch * (1 - v / topo)

    grade = "".join(f'<line x1="{L}" x2="{W - R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="{t["grade"]}"/>'
                    f'<text x="{L - 10}" y="{Y(v) + 4:.1f}" text-anchor="end" font-size="11" fill="{t["suave"]}">{v}</text>'
                    for v in range(0, topo + 1, passo))
    barras = "".join(f'<rect x="{X(i) - 2.2:.1f}" y="{Y(v):.1f}" width="4.4" height="{max(Y(0) - Y(v), 0):.1f}" rx="1.5" fill="{t["barra"]}" opacity=".85"/>'
                     for i, v in enumerate(valores) if v)
    pts = [(X(i), Y(m)) for i, m in enumerate(media7)]
    linha = suave(pts)
    area = f"{linha} L{pts[-1][0]:.1f} {Y(0):.1f} L{pts[0][0]:.1f} {Y(0):.1f} Z"
    meses = ""
    ultimo = None
    for i, (d, _) in enumerate(dias):
        if d.month != ultimo and d.day <= 7 and 0 < i < n - 5:
            meses += f'<text x="{X(i):.1f}" y="{H - 12}" text-anchor="middle" font-size="11" fill="{t["suave"]}">{MESES[d.month - 1]}</text>'
        ultimo = d.month
    data_melhor = dias[melhor][0]
    rotulo = f"{data_melhor.day} {MESES[data_melhor.month - 1]}"
    bx = min(max(X(melhor), L + 50), W - R - 50)

    def stat(x, valor, nome):
        return (f'<text x="{x}" y="42" font-size="26" font-weight="700" fill="{t["texto"]}">{valor}</text>'
                f'<text x="{x}" y="62" font-size="12" fill="{t["suave"]}">{nome}</text>')

    stats = (stat(L, total, "contribuições em 90 dias") + stat(L + 230, ativos, "dias com atividade")
             + stat(L + 430, f"{total / (n / 7):.1f}".replace(".", ","), "média por semana")
             + stat(L + 620, valores[melhor], f"melhor dia ({rotulo})"))
    css = f"""
    .linha{{stroke-dasharray:1;stroke-dashoffset:1;animation:desenha 2.4s ease-out .2s forwards}}
    .area{{opacity:0;animation:aparece 1.2s ease-out 1.4s forwards}}
    .bar{{opacity:0;animation:aparece .8s ease-out .2s forwards}}
    .ponto{{transform-box:fill-box;transform-origin:center;opacity:0;animation:aparece .4s ease-out 2.5s forwards,pulso 2.4s ease-in-out 3s infinite}}
    @keyframes desenha{{to{{stroke-dashoffset:0}}}}
    @keyframes aparece{{to{{opacity:1}}}}
    @keyframes pulso{{0%,100%{{transform:scale(1)}}50%{{transform:scale(1.6)}}}}
    @media (prefers-reduced-motion:reduce){{.linha{{animation:none;stroke-dashoffset:0}}.area,.bar,.ponto{{animation:none;opacity:1}}}}
    """
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="Atividade nos últimos 90 dias: {total} contribuições em {ativos} dias">'
            f'<defs><linearGradient id="ar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{t["area"]}" stop-opacity=".32"/>'
            f'<stop offset="1" stop-color="{t["area"]}" stop-opacity="0"/></linearGradient></defs><style>{css}</style>'
            f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="10" fill="{t["bg"]}" stroke="{t["borda"]}"/>'
            f'<g font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">{stats}{grade}'
            f'<g class="bar">{barras}</g><path class="area" d="{area}" fill="url(#ar)"/>'
            f'<path class="linha" pathLength="1" d="{linha}" fill="none" stroke="{t["linha"]}" stroke-width="2.6" stroke-linecap="round"/>'
            f'<circle class="ponto" cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="4" fill="{t["destaque"]}"/>{meses}</g></svg>')


def main():
    user, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    dias = buscar(user)
    for nome, suf in (("claro", ""), ("escuro", "-dark")):
        caminho = os.path.join(out, f"activity{suf}.svg")
        open(caminho, "w", encoding="utf-8").write(desenhar(dias, TEMAS[nome]))
        print("gerado", caminho)


if __name__ == "__main__":
    main()
