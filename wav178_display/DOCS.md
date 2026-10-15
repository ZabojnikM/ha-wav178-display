# Instalace a konfigurace

## 1. Nainstalovat a nastavit doplněk

1. Přidejte GitHub repozitář s větví `#stable` podle hlavního README.
2. Nainstalujte WAV178 FVE Display. První sestavení vyžaduje přístup HA k internetu.
3. V konfiguraci vyplňte skutečná ID entit. Prázdná položka znamená chybějící údaj,
   na obrazovce se zobrazí pomlčka a v náhledu upozornění.
4. Spusťte doplněk. Zapněte jeho automatický start při spuštění HA.
5. Otevřete webové rozhraní: ověřte aktuální čas čtení a náhled s hodnotami.

Home Assistant doplňku přidělí interní `SUPERVISOR_TOKEN`. Dlouhodobý token
uživatele se do konfigurace nezadává. Doplněk má API oprávnění od HA; jeho
implementace používá pouze GET a žádné povely pro FVE, TUV nebo wallbox neposílá.

| Položka | Význam |
|---|---|
| display_interval | Čekání mezi obrazovými přenosy, 30–3600 s; výchozí 60 s |
| poll_interval | Interval čtení HA, 10–3600 s; výchozí 60 s |
| stale_after_seconds | Limit od posledního úspěšného čtení API, výchozí 180 s |
| device_ip | Volitelné omezení na IPv4 displeje; prázdné přijímá klienty v dosažitelné síti |
| display_password | Heslo zámku displeje, pokud je zamčený; není to heslo HA nebo Wi-Fi |
| battery_positive | `charging` = kladná hodnota nabíjí; `discharging` = vybíjí; `unknown` = bez výkladu znaménka |
| frame_number | `zero` je varianta ověřená původním prototypem; `sector` odpovídá kódu ukázek výrobce |
| entity_soc | SOC baterie FVE v % |
| entity_pv | Výkon panelů ve W/kW |
| entity_battery | Výkon baterie ve W/kW |
| entity_grid | Síť ve W/kW, původní znaménko |
| entity_tuv_top / entity_tuv_bottom | Horní a spodní teplota TUV v °C |
| entity_tuv_power | Vybraná hodnota výkonu TUV ve W/kW |
| entity_wallbox | Výkon wallboxu ve W/kW |

Jednotky a dostupnost se ověřují. `unknown`, `unavailable`, NaN, chybějící
entita a nesprávná jednotka se nikdy nezmění na nulu. Stáří samotného nezměněného
stavu entity není důvod k odmítnutí; sleduje se úspěšné načtení API jako celku.
Při výpadku API zůstanou poslední hodnoty s označením STARÁ DATA. Po restartu
jsou do prvního čtení pomlčky. Zobrazený stav vybraného senzoru nemusí být
nezávislé měření fyzického příkonu; výběr senzoru je odpovědností mapování.

## 2. Přepnout displej na HA

V originální konfigurační aplikaci upravte Host_IP na LAN IPv4 počítače/Raspberry
Pi s Home Assistantem, ponechte správnou Wi-Fi a použijte Upload. Server je TCP
6868; číslo portu nepřidávejte do pole Host_IP. Je-li displej již nakonfigurovaný,
Bluetooth se dle výrobce zapíná podržením Wakeup alespoň 5 s.

Pokud se po konfiguraci sám nepřipojí, jednou stiskněte Wakeup. Náhled doplňku
ukáže připojený displej a čítač potvrzených přenosů. ACK dokládá převzetí dat
protokolem; skutečné vykreslení ověřte na panelu.

## 3. Běžný provoz

Automatické přenosy během otevřené relace nepotřebují další Wakeup. Doplněk
neposílá S/R/r ani OTA. Vypnutí/uspání rádia, slabá baterie a chování po dlouhém
výpadku sítě musí být ověřené na konkrétním firmware. Aktualizace doplňku ukončí
TCP relaci; automatické připojení displeje není univerzálně garantované.

Všechny živé hodnoty jsou jen v paměti procesu. V /data zůstává standardní
konfigurace HA; heslo zámku zařízení patří mezi její citlivé položky a zálohy.
API token, ID displeje ani živé hodnoty se nevypisují do provozních logů.

Při chybě zkontrolujte logy doplňku a webový náhled. `HTTPError` u API může
znamenat problém oprávnění; `PermissionError` relace displeje zamčený přístroj.
Při chybě přenosu se relace uzavře a server čeká na nové připojení. Podpora OTA
nebo obnovení původního firmware není součástí projektu.
