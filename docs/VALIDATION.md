# Stav ověření

Aktualizace 15. 10. 2026.

## Ověřený původní prototyp

Windows prototyp stejných rámců a rendereru zobrazuje skutečná data HA. Uživatel
potvrdil tři po sobě jdoucí testovací obrazy bez dalšího Wakeup. Server neposílal
Shutdown. Přenosy trvaly přibližně 5,5 sekundy a aktivní relace přetrvala nejméně
27 minut. Následné dashboardy mají ACK; dlouhodobá výdrž baterie se neměřila.

## Nový doplněk

Lokálně prošlo 10 testů: formát rámců, binární ACK, EOF, dvě aktualizace během
jedné relace, validace konfigurace, náhled HTTP, chybějící hodnoty a jednotky,
polarita baterie, zachování posledních dat při výpadku API a obnova po výpadku.
Testy používají syntetická data a localhost. Osobní token ani živý HA nepotřebují.

Verze 0.1.1 prošla nativním sestavením a kontejnerovým testem na amd64 i
aarch64 (GitHub Actions 38793123246). Na skutečném HA se spustila, načetla
všechna tehdejší mapování a displej potvrdil dva automatické přenosy na jednom
spojení. Ingress náhled byl funkční. To nenahrazuje měření výdrže baterie.

## Rozložení 0.2.0

Lokálně prošlo 12 testů včetně migrace nastavení z 0.1.x, validace entity
select, převodů W/kW, znamének baterie a chybějících hodnot. Vizuálně byl
zkontrolován samostatný vzorový obraz 400×300 se šesti stejnými kartami a
režimem Tesly. Kontejnerové testy amd64/aarch64 jsou povinnou součástí
vydávacího workflow před přesunem do stable. Nové fyzické rozložení otestuje
uživatel po aktualizaci; tato verze se během přípravy na jeho HA neinstaluje.

Kontejnerový smoke test ověřuje autentizaci syntetického HA, náhled PNG,
dva TCP přenosy bez Shutdown a zachování dat při výpadku API.

## Rozložení 0.3.0

Lokálně prošlo 14 testů. Navíc se ověřuje rozdíl mezi chybějícím, nulovým a
plným ukazatelem nabití, dostupnost úzkého písma, omezení dlouhého režimu a
zachování označení starých dat i při velkých hodnotách. Vizuálně je zkontrolován
obraz 400×300 s ukázkovými hodnotami i bez dostupných senzorů. Kontejnerový
test ověřuje přítomnost písma také uvnitř Alpine image. Fyzické otestování
nového vzhledu provede uživatel po vlastní instalaci.

## Rozložení 0.4.0

Lokálně prošlo 15 testů. Nová kontrola ověřuje výkonovou stupnici 0–8 kW,
převody W/kW, stejnou délku pro kladný i záporný výkon, plný bar nad 8 kW a
odlišení chybějící hodnoty od nuly. Vizuálně byl ověřen běžný obraz, nedostupné
senzory a velké hodnoty s dlouhým režimem a starými daty. Před vydáním do
stable zůstávají povinné nativní kontejnerové testy amd64/aarch64. Instalaci
a fyzické ověření nového vzhledu provede uživatel.

## Rozložení 0.5.0

Stejných 15 testů prošlo po změně na souvislé bary a větší číslice. Kontroly
stále rozlišují chybějící, nulovou a plnou hodnotu, ověřují 8kW stupnici,
překročení rozsahu i stará data. Vizuálně ověřen běžný obraz 400×300 a krajní
stav s velkými čísly, záporným výkonem sítě a dlouhým režimem wallboxu.
Před stable vydáním zůstávají povinné kontejnerové zkoušky na amd64/aarch64.
Instalaci provede uživatel.
