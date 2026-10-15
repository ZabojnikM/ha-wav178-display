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
