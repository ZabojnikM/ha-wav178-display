# Changelog

## 0.5.0

- Větší číslice a malé samostatné jednotky kW a % podle schváleného návrhu.
- Odstraněny malé vysvětlující popisky; názvy karet a ikony zůstávají.
- Jednoduché rámečkové bary se souvislou výplní namísto segmentů.
- Skryté popisky stupnice 0 a 8 kW; výkonová stupnice zůstává 0–8 kW.
- Kladné hodnoty se zobrazují bez plusu, záporné si zachovávají mínus.
- TUV má stejnou velikost číslic a svislé zarovnání jako panely a měniče.
- Zachováno mapování entit, velký režim wallboxu a upozornění na stará data.

## 0.4.0

- Schválené rozložení inspirované Victron: šest stejných karet 116 × 116 px.
- Neutrální společná sběrnice mezi řadami, bez šipek směru energie.
- Silné segmentové bary u všech šesti karet.
- Panely, měniče a síť mají pevnou stupnici 0–8 kW; síť používá velikost výkonu.
- Nabití baterie, TUV a Tesly zůstává v procentech 0–100 %.
- Výrazně zvětšený režim wallboxu vpravo dole, čas načtení vlevo.
- Zachováno mapování entit, upozornění na stará data a provoz TCP bez Shutdown.
- Hodnoty nad 8 kW vyplní celý bar; číselný údaj zůstává skutečný, včetně znaménka.

## 0.3.0

- Finální grafický návrh 2: šest stejně velkých polí s otevřenými dělicími linkami.
- Větší čísla v písmu DejaVu Sans Condensed, samostatné jednotky a ikony všech polí.
- Segmentové ukazatele nabití FVE baterie, TUV a Tesly; nedostupný stav má pomlčku.
- Režim wallboxu vpravo dole pod Teslou, čas načtení vlevo dole.
- Odstraněny nadpisy FVE / DOMOV a HOME ASSISTANT; všechna měření zůstávají.
- Zachováno upozornění na stará data, mapování entit i TCP protokol.
- Ošetřeny dlouhé režimy a velké hodnoty, bez překrývání sousedních polí.

## 0.2.0

- Šest stejně velkých okýnek 188 × 72 px v mřížce 2 × 3.
- PANELY zachovány, BATERIE spojuje SOC a podepsaný výkon v kW bez ikonky.
- MĚNIČE místo vybíjení baterie; SÍŤ zachovává původní znaménko a formát.
- TUV zobrazuje odhad nabití v procentech místo teplot a výkonu ohřevu.
- TESLA zobrazuje SOC, výkon nabíjení v kW a aktuální režim wallboxu.
- Nová mapování entit se doplní při aktualizaci z 0.1.x; stávající nastavení se zachová.
- Režim wallboxu se pouze čte, žádné řízení nabíjení se neposílá.

## 0.1.1

- Přímé spuštění Pythonu se zachováním prostředí od Supervisoru, bez zděděného s6.
- Standardní Docker init pro ukončení procesu; interní token se nezadává ručně.
- Kontejnerový test používá stejný Docker init jako instalace v Home Assistantu.

## 0.1.0

- První samostatný Python doplněk Home Assistantu pro Waveshare 4,2″ Cloud Module.
- TCP 6868, opakované obrazy bez Shutdown a bez změny firmware.
- Interní čtení HA bez ručního zadání dlouhodobého tokenu.
- Přehled FVE, baterie, sítě, TUV a wallboxu s vlastním mapováním entit.
- Náhled a diagnostika přes Ingress, rozlišení nedostupných a starých dat.
- Kontroly protokolu a kontejnery na amd64/aarch64 před vydáním do stable.
