"""Gera assets/trofeus.svg com os troféus do perfil, usando só a API do GitHub.

Uso (no workflow): GITHUB_TOKEN=... GITHUB_USER=lucascarper python scripts/gerar_trofeus.py
Sem dependências externas.
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from html import escape
from pathlib import Path

SAIDA = Path(__file__).resolve().parent.parent / "assets" / "trofeus.svg"

RANKS = ["C", "B", "A", "AA", "AAA", "S", "SS", "SSS"]

# Limites mínimos para cada rank, na ordem de RANKS.
LIMITES = {
    "estrelas": [1, 5, 10, 25, 50, 100, 500, 1000],
    "commits": [1, 50, 100, 250, 500, 1000, 2500, 5000],
    "seguidores": [1, 5, 10, 20, 50, 100, 300, 1000],
    "repositorios": [1, 5, 10, 15, 25, 40, 60, 100],
    "pull_requests": [1, 5, 10, 25, 50, 100, 300, 1000],
    "issues": [1, 5, 10, 25, 50, 100, 300, 1000],
    "linguagens": [1, 2, 3, 4, 6, 8, 10, 14],
    "anos": [0.1, 0.5, 1, 2, 3, 5, 7, 10],
}

TITULOS = {
    "estrelas": "Estrelas",
    "commits": "Commits (12m)",
    "seguidores": "Seguidores",
    "repositorios": "Repositórios",
    "pull_requests": "Pull Requests",
    "issues": "Issues",
    "linguagens": "Linguagens",
    "anos": "Tempo de conta",
}

QUERY = """
query($login: String!) {
  user(login: $login) {
    createdAt
    followers { totalCount }
    pullRequests { totalCount }
    issues { totalCount }
    contributionsCollection { totalCommitContributions }
    repositories(ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false,
                 first: 100, orderBy: {field: STARGAZERS, direction: DESC}) {
      totalCount
      nodes { stargazerCount languages(first: 10) { nodes { name } } }
    }
  }
}
"""


def buscar(login: str, token: str) -> dict:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"Bearer {token}", "User-Agent": "trofeus-perfil"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        corpo = json.load(resp)
    if corpo.get("errors") or not corpo.get("data", {}).get("user"):
        raise SystemExit(f"Erro na API do GitHub: {corpo.get('errors')}")
    u = corpo["data"]["user"]
    repos = u["repositories"]["nodes"]
    criado = datetime.fromisoformat(u["createdAt"].replace("Z", "+00:00"))
    return {
        "estrelas": sum(r["stargazerCount"] for r in repos),
        "commits": u["contributionsCollection"]["totalCommitContributions"],
        "seguidores": u["followers"]["totalCount"],
        "repositorios": u["repositories"]["totalCount"],
        "pull_requests": u["pullRequests"]["totalCount"],
        "issues": u["issues"]["totalCount"],
        "linguagens": len({l["name"] for r in repos for l in r["languages"]["nodes"]}),
        "anos": (datetime.now(timezone.utc) - criado).days / 365.25,
    }


def indice_rank(chave: str, valor: float) -> int:
    """-1 se não atingiu o primeiro limite; senão o índice em RANKS."""
    return sum(1 for lim in LIMITES[chave] if valor >= lim) - 1


def formatar(chave: str, valor: float) -> str:
    if chave == "anos":
        return f"{valor:.1f} anos" if valor >= 1 else f"{int(valor * 12)} meses"
    return str(int(valor))


TACA = (
    "M8 4h8v5a4 4 0 0 1-8 0V4z M8 6H5v1.5A2.5 2.5 0 0 0 7.5 10 "
    "M16 6h3v1.5a2.5 2.5 0 0 1-2.5 2.5 M12 13v3 M9 20h6 M10 16h4v4h-4z"
)

LARGURA, ALTURA, GAP = 118, 128, 8


def cartao(x: int, chave: str, valor: float) -> str:
    idx = indice_rank(chave, valor)
    ativo = idx >= 0
    forte = idx >= 5
    cor_borda = "#E10600" if ativo else "#333333"
    cor_icone = "#E10600" if ativo else "#555555"
    rank = RANKS[idx] if ativo else "–"
    fundo_rank = "#E10600" if forte else "#1A1A1A"
    cor_rank = "#FFFFFF" if forte or not ativo else "#E10600"
    return f"""
  <g transform="translate({x},0)">
    <rect x="0.5" y="0.5" width="{LARGURA - 1}" height="{ALTURA - 1}" rx="8" fill="#0D0D0D" stroke="{cor_borda}"/>
    <g transform="translate({LARGURA / 2 - 18},12) scale(1.5)" fill="none" stroke="{cor_icone}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
      <path d="{TACA}"/>
    </g>
    <text x="{LARGURA / 2}" y="68" text-anchor="middle" font-size="11" font-weight="600" fill="#9E9E9E">{escape(TITULOS[chave])}</text>
    <text x="{LARGURA / 2}" y="88" text-anchor="middle" font-size="16" font-weight="700" fill="#FFFFFF">{escape(formatar(chave, valor))}</text>
    <rect x="{LARGURA / 2 - 20}" y="98" width="40" height="20" rx="10" fill="{fundo_rank}" stroke="{cor_borda}"/>
    <text x="{LARGURA / 2}" y="112" text-anchor="middle" font-size="12" font-weight="700" fill="{cor_rank}">{rank}</text>
  </g>"""


def svg(stats: dict) -> str:
    chaves = list(TITULOS)
    largura = len(chaves) * LARGURA + (len(chaves) - 1) * GAP
    cartoes = "".join(
        cartao(i * (LARGURA + GAP), k, stats[k]) for i, k in enumerate(chaves)
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{largura}" height="{ALTURA}" '
        f'viewBox="0 0 {largura} {ALTURA}" role="img" aria-label="Troféus do GitHub" '
        f'font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">'
        f"{cartoes}\n</svg>\n"
    )


def main() -> None:
    login = os.environ.get("GITHUB_USER", "lucascarper")
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("Defina GITHUB_TOKEN.")
    stats = buscar(login, token)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(svg(stats), encoding="utf-8")
    print(json.dumps(stats, indent=2, default=str))


if __name__ == "__main__":
    main()
