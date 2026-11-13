#!/usr/bin/env python3
"""Gera um cartão único com os números do GitHub e as linguagens mais usadas.

Esquerda: commits, pull requests, revisões, repositórios e estrelas.
Direita: barra com as linguagens (por tamanho de código) e legenda com percentuais.
Saída: stats.svg e stats-dark.svg.

Uso: stats.py <usuario> <pasta-de-saida>
Lê o token de GH_TOKEN ou GITHUB_TOKEN. Sem token, usa dados de exemplo.
"""
import json, os, sys, urllib.request

W, H = 880, 250
QUERY = """query($u:String!){user(login:$u){
  contributionsCollection{totalCommitContributions totalPullRequestContributions totalPullRequestReviewContributions totalIssueContributions}
  repositories(first:100, ownerAffiliations:[OWNER,COLLABORATOR,ORGANIZATION_MEMBER], isFork:false, orderBy:{field:PUSHED_AT,direction:DESC}){
    totalCount nodes{stargazerCount languages(first:6, orderBy:{field:SIZE,direction:DESC}){edges{size node{name color}}}}}
}}"""

TEMAS = {
    "claro": dict(bg="#ffffff", borda="#d0d7de", texto="#1f2328", suave="#656d76", trilho="#eaeef2", linha="#d8dee4", acento="#0969da"),
    "escuro": dict(bg="#0d1117", borda="#21262d", texto="#e6edf3", suave="#8b949e", trilho="#21262d", linha="#21262d", acento="#58a6ff"),
}


def buscar(user):
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        return dict(commits=212, prs=18, reviews=9, issues=4, repos=7, stars=3,
                    langs=[("Python", "#3572A5", 52000), ("Java", "#b07219", 31000), ("JavaScript", "#f1e05a", 12000), ("HTML", "#e34c26", 6000), ("CSS", "#563d7c", 3000)])
    req = urllib.request.Request("https://api.github.com/graphql", json.dumps({"query": QUERY, "variables": {"u": user}}).encode(),
                                 {"Authorization": f"bearer {token}", "Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=30))["data"]["user"]
    c = d["contributionsCollection"]; nodes = d["repositories"]["nodes"]
    tot = {}
    for n in nodes:
        for e in n["languages"]["edges"]:
            nome = e["node"]["name"]; cor = e["node"]["color"] or "#8b949e"
            antigo = tot.get(nome, (cor, 0))
            tot[nome] = (cor, antigo[1] + e["size"])
    langs = sorted(((k, v[0], v[1]) for k, v in tot.items()), key=lambda x: -x[2])
    return dict(commits=c["totalCommitContributions"], prs=c["totalPullRequestContributions"], reviews=c["totalPullRequestReviewContributions"], issues=c["totalIssueContributions"],
                repos=d["repositories"]["totalCount"], stars=sum(n["stargazerCount"] for n in nodes), langs=langs)


def pct(a, b):
    return f"{100 * a / b:.1f}".replace(".", ",")


def desenhar(dados, t):
    itens = [(dados["commits"], "commits no último ano"), (dados["prs"], "pull requests"), (dados["reviews"], "revisões de código"),
             (dados["issues"], "issues abertas"), (dados["repos"], "repositórios"), (dados["stars"], "estrelas recebidas")]
    colunas = ""
    for i, (v, nome) in enumerate(itens):
        x, y = 36 + (i % 2) * 190, 78 + (i // 2) * 62
        colunas += (f'<g class="num" style="animation-delay:{.15 * i:.2f}s"><text x="{x}" y="{y}" font-size="30" font-weight="700" fill="{t["texto"]}">{v}</text>'
                    f'<text x="{x}" y="{y + 19}" font-size="12" fill="{t["suave"]}">{nome}</text></g>')
    total = sum(l[2] for l in dados["langs"]) or 1
    top = dados["langs"][:5]
    resto = total - sum(l[2] for l in top)
    barras, legenda = "", ""
    bx, bw, by = 470, 374, 92
    pos = bx
    for i, (nome, cor, tam) in enumerate(top + ([("Outras", "#8b949e", resto)] if resto > total * .01 else [])):
        w = bw * tam / total
        barras += f'<rect class="seg" style="animation-delay:{.2 + .12 * i:.2f}s" x="{pos:.1f}" y="{by}" width="{max(w - 2, 2):.1f}" height="12" rx="3" fill="{cor}"/>'
        pos += w
        lx, ly = bx + (i % 2) * 190, 138 + (i // 2) * 26
        legenda += (f'<circle cx="{lx + 5}" cy="{ly - 4}" r="5" fill="{cor}"/><text x="{lx + 18}" y="{ly}" font-size="13" fill="{t["texto"]}">{nome}</text>'
                    f'<text x="{lx + 168}" y="{ly}" font-size="13" fill="{t["suave"]}" text-anchor="end">{pct(tam, total)}%</text>')
    css = (".num{opacity:0;animation:ap .7s ease-out forwards}.seg{transform-box:fill-box;transform-origin:left;transform:scaleX(0);animation:cr .9s ease-out forwards}"
           "@keyframes ap{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}@keyframes cr{to{transform:scaleX(1)}}"
           "@media (prefers-reduced-motion:reduce){.num{animation:none;opacity:1}.seg{animation:none;transform:none}}")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Números do GitHub e linguagens mais usadas">'
            f'<style>{css}</style><rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="10" fill="{t["bg"]}" stroke="{t["borda"]}"/>'
            f'<g font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">'
            f'<text x="36" y="40" font-size="14" font-weight="600" fill="{t["acento"]}" letter-spacing="1.2">EM NÚMEROS</text>'
            f'<text x="470" y="40" font-size="14" font-weight="600" fill="{t["acento"]}" letter-spacing="1.2">LINGUAGENS MAIS USADAS</text>'
            f'<line x1="440" y1="24" x2="440" y2="{H - 24}" stroke="{t["linha"]}"/>{colunas}{barras}{legenda}'
            f'<text x="470" y="{H - 24}" font-size="11" fill="{t["suave"]}">Por tamanho de código nos repositórios públicos</text></g></svg>')


def main():
    user, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    dados = buscar(user)
    for nome, suf in (("claro", ""), ("escuro", "-dark")):
        caminho = os.path.join(out, f"stats{suf}.svg")
        open(caminho, "w", encoding="utf-8").write(desenhar(dados, TEMAS[nome]))
        print("gerado", caminho)


if __name__ == "__main__":
    main()
