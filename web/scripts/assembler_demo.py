"""Assemble la démonstration construite (dist-demo/) en une seule page : styles et script intégrés.

La page publiée reçoit son squelette (doctype, head, body) à la publication : on n'écrit que le contenu.
"""
from pathlib import Path

racine = Path(__file__).resolve().parents[1]
dist = racine / "dist-demo"
css = "".join(p.read_text("utf-8") for p in (dist / "assets").glob("*.css"))
js = "".join(p.read_text("utf-8") for p in (dist / "assets").glob("*.js")).replace("</script", "<\\/script")
page = f"""<title>Démonstration Courtage</title>
<style>{css}</style>
<div id="racine"></div>
<script type="module">{js}</script>
"""
sortie = dist / "demo-courtage.html"
sortie.write_text(page, "utf-8")
print(f"{sortie} : {len(page) / 1024:.0f} Ko")
