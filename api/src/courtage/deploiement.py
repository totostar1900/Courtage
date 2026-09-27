"""Au démarrage d'un conteneur : migrer, ouvrir le rôle applicatif, puis PROUVER l'état de la base.

    python -m courtage.deploiement            # lit COURTAGE_URL_PROPRIETAIRE et DATABASE_URL

1. Les migrations s'exécutent avec le rôle PROPRIÉTAIRE (`COURTAGE_URL_PROPRIETAIRE`).
   Jamais avec `courtage_app` : un rôle qui crée une table en devient propriétaire,
   et un propriétaire contourne la RLS — la couche entière deviendrait inerte
   sans que rien ne le dise.
2. `courtage_app` reçoit le droit de se connecter avec le mot de passe de
   `DATABASE_URL` (la migration 0001 le crée sans ce droit).
3. Des contrôles lus DANS la base, chacun PASS ou FAIL. Un seul FAIL arrête le
   démarrage : une base mal verrouillée se comporte exactement comme une bonne
   jusqu'au jour où quelqu'un y écrit ce qu'il ne devrait pas.
"""
import os
import sys
from dataclasses import dataclass

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url

from courtage.db.migrations import migrer, revision_attendue

ROLE_APP = "courtage_app"
IMMUABLES = ("etudes_immuables", "baremes_immuables", "regimes_versions_immuables", "regimes_categories_immuables",
             "fichiers_personnel_vidage")
SANS_MODIFICATION = ("journal", "sceaux", "catalogue_regimes", "catalogue_retraits", "etats_dossier")      # insertion et lecture seulement, pour le rôle applicatif
# Porte une organisation mais se lit AVANT qu'une organisation soit connue (qui est membre de quoi) :
# hors RLS par construction. Toute autre table qui en porte une doit avoir la RLS.
HORS_RLS = ("adhesions",)


@dataclass(frozen=True)
class Controle:
    nom: str
    ok: bool
    detail: str = ""

    def __str__(self) -> str:
        return f"{'PASS' if self.ok else 'FAIL'}  {self.nom}" + (f" — {self.detail}" if self.detail else "")


def ouvrir_role_applicatif(proprio: Engine, url_app: str) -> None:
    url = make_url(url_app)
    if url.username != ROLE_APP:
        raise RuntimeError(f"DATABASE_URL doit utiliser le rôle {ROLE_APP}, pas « {url.username} ».")
    if not url.password:
        raise RuntimeError("DATABASE_URL n'a pas de mot de passe.")
    litteral = "'" + url.password.replace("'", "''") + "'"
    with proprio.begin() as c:
        c.execute(text(f"ALTER ROLE {ROLE_APP} LOGIN PASSWORD {litteral}"))


def controler(proprio: Engine) -> list[Controle]:
    with proprio.connect() as c:
        un = lambda sql, **p: c.execute(text(sql), p).scalar()          # noqa: E731
        tous = lambda sql, **p: [r[0] for r in c.execute(text(sql), p)]  # noqa: E731

        en_base, attendue = un("SELECT version_num FROM alembic_version"), revision_attendue()
        possedees = tous("SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tableowner = :r", r=ROLE_APP)
        sans_rls = tous("""
            SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relkind = 'r' AND NOT c.relrowsecurity
              AND EXISTS (SELECT 1 FROM information_schema.columns k
                          WHERE k.table_schema = 'public' AND k.table_name = c.relname
                            AND k.column_name = 'organisation_id')
              AND c.relname <> ALL(:hors)""", hors=list(HORS_RLS))
        superutilisateur = un("SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = :r", r=ROLE_APP)
        declencheurs = tous("SELECT tgname FROM pg_trigger WHERE NOT tgisinternal AND tgenabled <> 'D'")
        modifiables = tous("""
            SELECT table_name || ':' || privilege_type FROM information_schema.role_table_grants
            WHERE grantee = :r AND table_name = ANY(:t) AND privilege_type IN ('UPDATE', 'DELETE', 'TRUNCATE')""",
                           r=ROLE_APP, t=list(SANS_MODIFICATION))
        peut_se_connecter = un("SELECT rolcanlogin FROM pg_roles WHERE rolname = :r", r=ROLE_APP)

    manquants = [t for t in IMMUABLES if t not in declencheurs]
    return [
        Controle("schéma à jour", en_base == attendue, f"base {en_base}, code {attendue}"),
        Controle(f"{ROLE_APP} ne possède aucune table", not possedees, ", ".join(possedees)),
        Controle(f"{ROLE_APP} n'est ni superutilisateur ni exempté de RLS", superutilisateur is False),
        Controle(f"{ROLE_APP} peut se connecter", bool(peut_se_connecter)),
        Controle("RLS active sur toute table d'une organisation", not sans_rls, ", ".join(sans_rls)),
        Controle("déclencheurs d'immuabilité actifs", not manquants, "manquent : " + ", ".join(manquants)
                 if manquants else ""),
        Controle("journal et sceaux : ni modification ni suppression", not modifiables, ", ".join(modifiables)),
    ]


def preparer(url_proprio: str, url_app: str) -> list[Controle]:
    migrer(url_proprio)
    proprio = create_engine(url_proprio)
    try:
        ouvrir_role_applicatif(proprio, url_app)
        return controler(proprio)
    finally:
        proprio.dispose()


def url_applicative(env) -> str:
    """L'URL du rôle applicatif : `DATABASE_URL` si elle est donnée ; sinon celle du propriétaire, avec
    `courtage_app` et `COURTAGE_MOT_DE_PASSE_APP` — un hébergeur (Render) ne fournit que la première."""
    if env.get("DATABASE_URL"):
        return _psycopg(env["DATABASE_URL"])
    proprio, mot_de_passe = env.get("COURTAGE_URL_PROPRIETAIRE"), env.get("COURTAGE_MOT_DE_PASSE_APP")
    if not (proprio and mot_de_passe):
        raise RuntimeError("Donner DATABASE_URL, ou COURTAGE_URL_PROPRIETAIRE et COURTAGE_MOT_DE_PASSE_APP.")
    return make_url(_psycopg(proprio)).set(username=ROLE_APP, password=mot_de_passe).render_as_string(hide_password=False)


def _psycopg(url: str) -> str:
    """Les hébergeurs donnent `postgres://…` ou `postgresql://…` ; SQLAlchemy veut le pilote nommé."""
    for prefixe in ("postgres://", "postgresql://"):
        if url.startswith(prefixe):
            return "postgresql+psycopg://" + url[len(prefixe):]
    return url


if __name__ == "__main__":
    controles = preparer(_psycopg(os.environ["COURTAGE_URL_PROPRIETAIRE"]), url_applicative(os.environ))
    for c in controles:
        print(f"[base] {c}", flush=True)
    sys.exit(0 if all(c.ok for c in controles) else 1)
