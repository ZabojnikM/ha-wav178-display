# Vydání a GitHub

Repozitář má vývojovou větev main a instalační stable. workflow Check app
provádí testy Pythonu, kontrolu veřejných souborů a nativní sestavení/spuštění
kontejnerů na ubuntu-24.04 (amd64) a ubuntu-24.04-arm (aarch64).

Po přípravě verze v config.json a CHANGELOG.md spusťte z main workflow
Release verified app s odpovídajícím číslem verze. Znovu spustí celý Check app.
Teprve po úspěchu vytvoří tag vX.Y.Z a posune stable na stejný ověřený commit.
Push stable a tagu je atomický, změna stable není vynucená přes force.
Existující tag nelze tímto postupem přepsat. Potom vznikne veřejné GitHub vydání.

První verze nepoužívá GHCR: Home Assistant z Dockerfile sestaví stejný zdroj
při instalaci. Nevzniká problém s přístupem k privátním vrstvám registru.
Základní obraz a balíčky OS se při sestavení stahují z oficiálních zdrojů.
Pin základního obrazu na ověřený digest je vhodný před dlouhodobým provozem;
v první verzi se používá dokumentovaný latest obraz Home Assistantu.

Na veřejný GitHub patří jen explicitně zkontrolované zdroje. deployment.local.json,
options.local.json, PROJECT_BRIEF.local.md, snapshoty, exporty senzorů, logy,
hesla a tokeny se nepublikují. Docker build context obsahuje jen app/*.py a run.sh.

Ověření kontejnery vyžaduje Docker nebo GitHub Actions. Samotný Python test na
Windows nedokládá instalaci na HA OS ani správné sestavení aarch64 obrazu.
