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

Na tomto Windows PC není Docker. Sestavení/spuštění Linux kontejneru ani aarch64
proto zatím nebylo provedeno. Připravená CI je ověří před vydáním stable.
Instalace doplňku, přístup přes interní SUPERVISOR_TOKEN, Ingress v reálném HA
a převzetí displeje na HA hostiteli čekají na fyzický instalační test.

Příkaz ke zopakování testů je v README. Kontejnerový smoke test navíc kontroluje
autentizaci proti syntetickému HA, náhled PNG, dva přenosy a výpadek API.
