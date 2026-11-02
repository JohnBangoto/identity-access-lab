"""Application de test du jalon 2 : accès protégé par rôle Keycloak.

Pages protégées :
    /compta    -> rôle finance-user
    /serveurs  -> rôle it-user

La connexion passe par Keycloak (OpenID Connect). Le rôle est lu dans le jeton
d'accès, dont la signature est vérifiée avec les clés publiques du realm.
Chaque décision (autorisé ou refusé) est écrite dans access.log, une ligne JSON
par événement.
"""
import json
import os
import secrets
import sys
import time
from datetime import datetime, timezone
from functools import wraps
from urllib.parse import urlencode

import requests
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from joserfc import jwt
from joserfc.jwk import KeySet
from flask import Flask, jsonify, redirect, request, session, url_for
from markupsafe import escape

load_dotenv()

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8080").rstrip("/")
REALM = os.getenv("KEYCLOAK_REALM", "labiam")
CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "test-app")
CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET", "")
APP_URL = os.getenv("APP_URL", "http://localhost:5000").rstrip("/")
ISSUER = f"{KEYCLOAK_URL}/realms/{REALM}"
LOG_FILE = os.getenv(
    "ACCESS_LOG", os.path.join(os.path.dirname(os.path.abspath(__file__)), "access.log")
)

# Ressource -> rôle exigé. Tout le reste est refusé par défaut.
RESOURCES = {
    "compta": {"role": "finance-user", "title": "Application Compta"},
    "serveurs": {"role": "it-user", "title": "Application Serveurs"},
}
BUSINESS_ROLES = {cfg["role"] for cfg in RESOURCES.values()}

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32)
app.config.update(
    SESSION_COOKIE_NAME="iam_lab_session",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

oauth = OAuth(app)
keycloak = oauth.register(
    name="keycloak",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    server_metadata_url=f"{ISSUER}/.well-known/openid-configuration",
    client_kwargs={"scope": "openid profile"},
)

_jwks = {"keys": None, "fetched_at": 0.0}


def get_jwks():
    """Clés publiques du realm, mises en cache 10 minutes."""
    now = time.time()
    if _jwks["keys"] is None or now - _jwks["fetched_at"] > 600:
        meta = requests.get(f"{ISSUER}/.well-known/openid-configuration", timeout=5).json()
        data = requests.get(meta["jwks_uri"], timeout=5).json()
        _jwks["keys"] = KeySet.import_key_set(data)
        _jwks["fetched_at"] = now
    return _jwks["keys"]


def read_access_token(access_token):
    """Vérifie la signature (RS256), l'émetteur et l'expiration, puis renvoie les claims.

    Lève une exception si le jeton est falsifié, expiré ou émis par un autre realm.
    """
    token = jwt.decode(access_token, get_jwks(), algorithms=["RS256"])
    registry = jwt.JWTClaimsRegistry(iss={"essential": True, "value": ISSUER})
    registry.validate(token.claims)
    return token.claims


def write_log(**fields):
    entry = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), **fields}
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as exc:
        print(f"Journal inaccessible : {exc}", file=sys.stderr)


STYLE = """
:root{--bg:#f6f7f9;--card:#fff;--text:#1f2328;--muted:#656d76;--line:#d8dee4;--accent:#2b6cb0;
--ok:#1a7f4b;--ok-bg:#e6f4ec;--no:#b42318;--no-bg:#fdecea}
@media (prefers-color-scheme:dark){:root{--bg:#16181c;--card:#1f2227;--text:#e6e6e6;--muted:#9aa4af;
--line:#323841;--accent:#6cb6ff;--ok:#4cc38a;--ok-bg:#16301f;--no:#ff7b72;--no-bg:#3a1c1a}}
*{box-sizing:border-box}
body{margin:0;font-family:system-ui,sans-serif;line-height:1.55;color:var(--text);background:var(--bg)}
header{background:var(--card);border-bottom:1px solid var(--line)}
.bar{max-width:880px;margin:0 auto;padding:.8rem 1rem;display:flex;flex-wrap:wrap;
align-items:center;gap:.4rem 1.2rem}
.brand{font-weight:700;color:var(--text)!important;margin-right:auto}
.bar a{color:var(--accent);text-decoration:none}
.bar a:hover{text-decoration:underline}
.user{color:var(--muted);font-size:.9rem}
main{max-width:880px;margin:2rem auto;padding:0 1rem}
h1{margin:.2rem 0 .4rem;font-size:1.7rem}
p.lead{color:var(--muted);margin-top:0}
.grid{display:grid;gap:1rem;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));margin-top:1.5rem}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:1.2rem 1.4rem}
.card h2{margin:0 0 .3rem;font-size:1.15rem}
.card p{margin:.3rem 0}
.badge{display:inline-block;padding:.15rem .6rem;border-radius:999px;font-size:.82rem;font-weight:600}
.badge.ok{color:var(--ok);background:var(--ok-bg)}
.badge.no{color:var(--no);background:var(--no-bg)}
.badge.role{color:var(--muted);border:1px solid var(--line);font-weight:500}
.banner{border-radius:12px;padding:1.2rem 1.4rem;margin-bottom:1.2rem;border:1px solid}
.banner.ok{color:var(--ok);background:var(--ok-bg);border-color:var(--ok)}
.banner.no{color:var(--no);background:var(--no-bg);border-color:var(--no)}
.banner h1{margin:0 0 .3rem}
.banner p{margin:.2rem 0;color:var(--text)}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);
border-radius:12px;overflow:hidden}
th,td{text-align:left;padding:.6rem .9rem;border-bottom:1px solid var(--line)}
th{font-size:.85rem;color:var(--muted);font-weight:600}
tr:last-child td{border-bottom:0}
code{background:rgba(127,127,127,.2);padding:.1em .35em;border-radius:4px}
.btn{display:inline-block;margin-top:.8rem;padding:.5rem 1rem;border-radius:8px;
background:var(--accent);color:#fff!important;text-decoration:none;font-weight:600}
.note{color:var(--muted);font-size:.85rem;margin-top:1.5rem}
"""


def page(title, user, body):
    """Gabarit commun : en-tête (navigation et utilisateur) + contenu."""
    links = "<a href='/'>Accueil</a><a href='/compta'>Compta</a><a href='/serveurs'>Serveurs</a>"
    if user:
        who = (f"<span class='user'>Connecté : <strong>{escape(user['username'])}</strong></span>"
               "<a href='/logout'>Déconnexion</a>")
    else:
        who = "<a href='/login'>Connexion</a>"
    return (
        "<!doctype html><html lang='fr'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{escape(title)}</title><style>{STYLE}</style></head><body>"
        f"<header><div class='bar'><a class='brand' href='/'>identity-access-lab</a>{links}{who}</div></header>"
        f"<main>{body}</main></body></html>"
    )


def business_roles(user):
    return sorted(r for r in user["roles"] if r in BUSINESS_ROLES)


def fmt_roles(roles):
    return ", ".join(f"<code>{escape(r)}</code>" for r in roles) or "aucun"


def require_role(resource):
    """Refuse l'accès sauf si l'utilisateur connecté possède le rôle de la ressource."""
    cfg = RESOURCES[resource]

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            user = session.get("user")
            if not user:
                session["next"] = request.path
                return redirect(url_for("login"))
            if cfg["role"] in user["roles"]:
                write_log(event="access", decision="allow", user=user["username"],
                          resource=resource, required_role=cfg["role"], ip=request.remote_addr)
                return view(*args, **kwargs)
            write_log(event="access", decision="deny", user=user["username"],
                      resource=resource, required_role=cfg["role"], ip=request.remote_addr)
            body = (
                "<div class='banner no'><h1>403 : accès refusé</h1>"
                f"<p><strong>{escape(user['username'])}</strong> est authentifié, "
                f"mais le rôle <code>{escape(cfg['role'])}</code> est requis pour "
                f"« {escape(cfg['title'])} ».</p>"
                f"<p>Rôles métier de l'utilisateur : {fmt_roles(business_roles(user))}</p></div>"
                "<a class='btn' href='/'>Retour à l'accueil</a>"
            )
            return page("Accès refusé", user, body), 403

        return wrapper

    return decorator


@app.route("/")
def home():
    user = session.get("user")
    body = "<h1>identity-access-lab</h1>"
    if not user:
        body += ("<p class='lead'>Authentification et autorisation avec Keycloak.</p>"
                 "<div class='card'><h2>Vous n'êtes pas connecté</h2>"
                 "<p>Connectez-vous pour voir les applications auxquelles vous avez accès.</p>"
                 "<a class='btn' href='/login'>Se connecter avec Keycloak</a></div>")
        return page("Accueil", None, body)
    body += (f"<p class='lead'>Bonjour <strong>{escape(user['username'])}</strong>. "
             f"Rôles métier : {fmt_roles(business_roles(user))}</p><div class='grid'>")
    for key, cfg in RESOURCES.items():
        allowed = cfg["role"] in user["roles"]
        badge = ("<span class='badge ok'>Accès autorisé</span>" if allowed
                 else "<span class='badge no'>Accès refusé</span>")
        body += (f"<div class='card'><h2>{escape(cfg['title'])}</h2>{badge}"
                 f"<p>Rôle requis : <code>{escape(cfg['role'])}</code></p>"
                 f"<a href='/{key}'>Ouvrir →</a></div>")
    body += "</div>"
    return page("Accueil", user, body)


@app.route("/login")
def login():
    return keycloak.authorize_redirect(f"{APP_URL}/callback")


@app.route("/callback")
def callback():
    try:
        token = keycloak.authorize_access_token()
        claims = read_access_token(token["access_token"])
        username = claims.get("preferred_username", "inconnu")
        roles = sorted(claims.get("realm_access", {}).get("roles", []))
    except Exception as exc:  # noqa: BLE001 : on journalise le type, pas le détail
        write_log(event="login_failed", error=type(exc).__name__, ip=request.remote_addr)
        return page("Erreur", None, "<div class='banner no'><h1>Connexion impossible</h1>"
                    "<p>La connexion a échoué. Consultez le journal du serveur.</p></div>"
                    "<a class='btn' href='/login'>Réessayer</a>"), 400
    nxt = session.get("next", "/")
    if not nxt.startswith("/") or nxt.startswith("//"):
        nxt = "/"
    session.clear()
    session["user"] = {"username": username, "roles": roles}
    write_log(event="login", user=username, ip=request.remote_addr)
    return redirect(nxt)


@app.route("/logout")
def logout():
    user = session.get("user")
    session.clear()
    write_log(event="logout", user=user["username"] if user else None, ip=request.remote_addr)
    query = urlencode({"client_id": CLIENT_ID, "post_logout_redirect_uri": f"{APP_URL}/"})
    return redirect(f"{ISSUER}/protocol/openid-connect/logout?{query}")


@app.route("/whoami")
def whoami():
    user = session.get("user")
    if not user:
        return jsonify(error="non connecté"), 401
    return jsonify(username=user["username"], roles=user["roles"])


@app.route("/compta")
@require_role("compta")
def compta():
    return resource_page("compta")


@app.route("/serveurs")
@require_role("serveurs")
def serveurs():
    return resource_page("serveurs")


# Données fictives, uniquement pour donner un aspect réaliste aux pages autorisées.
DEMO = {
    "compta": (("Facture", "Fournisseur", "Montant", "Statut"), (
        ("F-2026-041", "Papeterie Martin", "184,50 €", "Payée"),
        ("F-2026-042", "Cloud Hébergement", "1 250,00 €", "À payer"),
        ("F-2026-043", "Cabinet Conseil Nord", "3 900,00 €", "En attente"),
    )),
    "serveurs": (("Serveur", "Rôle", "Système", "État"), (
        ("srv-web-01", "Web", "Ubuntu 24.04", "En ligne"),
        ("srv-db-01", "Base de données", "Debian 12", "En ligne"),
        ("srv-bkp-01", "Sauvegarde", "Ubuntu 24.04", "Maintenance"),
    )),
}


def resource_page(resource):
    cfg = RESOURCES[resource]
    user = session["user"]
    head, rows = DEMO[resource]
    thead = "".join(f"<th>{escape(h)}</th>" for h in head)
    tbody = "".join("<tr>" + "".join(f"<td>{escape(c)}</td>" for c in row) + "</tr>" for row in rows)
    body = (
        f"<div class='banner ok'><h1>{escape(cfg['title'])}</h1>"
        f"<p>Accès autorisé : <strong>{escape(user['username'])}</strong> possède le rôle "
        f"<code>{escape(cfg['role'])}</code>.</p></div>"
        f"<table><thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table>"
        "<p class='note'>Données fictives, à titre de démonstration.</p>"
    )
    return page(cfg["title"], user, body)


def main():
    if not CLIENT_SECRET:
        sys.exit("KEYCLOAK_CLIENT_SECRET manquant : copiez .env.example en .env "
                 "et renseignez le secret du client.")
    app.run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    main()
