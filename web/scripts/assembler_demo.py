"""Assemble la démonstration construite (dist-demo/) en une seule page : styles et script intégrés.

La page publiée reçoit son squelette (doctype, head, body) à la publication : on n'écrit que le contenu.
"""
import sys
from pathlib import Path

# `assembler_demo.py [dossier construit] [page de sortie] [titre]` : la démonstration par défaut, une maquette sinon.
racine = Path(__file__).resolve().parents[1]
dist = racine / (sys.argv[1] if len(sys.argv) > 1 else "dist-demo")
nom = sys.argv[2] if len(sys.argv) > 2 else "demo-courtage.html"
titre = sys.argv[3] if len(sys.argv) > 3 else "Démonstration Nitch"
css = "".join(p.read_text("utf-8") for p in (dist / "assets").glob("*.css"))
js = "".join(p.read_text("utf-8") for p in (dist / "assets").glob("*.js")).replace("</script", "<\\/script")
page = f"""<title>{titre}</title>
<style>{css}</style>
<div id="racine"></div>
<script type="module">{js}</script>
"""
sortie = dist / nom
sortie.write_text(page, "utf-8")
print(f"{sortie} : {len(page) / 1024:.0f} Ko")
