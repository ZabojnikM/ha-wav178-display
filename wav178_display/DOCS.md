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
| entity_inverter | Výstupní výkon měničů ve W/kW; zobrazen v kW |
| entity_tuv_soc | Odhad nabití zásoby TUV v % |
| entity_tesla_soc | Nabití baterie Tesly v % |
| entity_tesla_power | Výkon nabíjení Tesly ve W/kW; zobrazen v kW |
| entity_wallbox_mode | Stav entity `select` s aktuálním režimem wallboxu |
| entity_tuv_top / entity_tuv_bottom / entity_tuv_power / entity_wallbox | Staré položky 0.1.x; zachované kvůli kompatibilitě, od 0.2.0 se nečtou |

### Aktualizace z 0.1.x na 0.2.0

Stávající mapování panelů, baterie a sítě, intervaly i heslo displeje se zachovají.
Nové položky se doplní takto; v případě potřeby je upravte v nastavení:

```yaml
entity_inverter: sensor.vystupni_vykon
entity_tuv_soc: sensor.tuv_300_l_odhad_zasoby_odhad_nabiti_tuv
entity_tesla_soc: sensor.uroven_baterie
entity_tesla_power: sensor.vykon_nabijecky
entity_wallbox_mode: select.rezim_nabijeni
```

Pro kladný výkon nabíjející FVE baterii nastavte `battery_positive: charging`.
V BATERII se pak zobrazí např. `76 %` a `−0,53 kW` při vybíjení. Od verze 0.3.0 je režim wallboxu vpravo dole pod Teslou; čas načtení vlevo
dole. Dlouhý režim se zkrátí výpustkou. Baterie FVE, TUV i Tesla mají segmentový
ukazatel nabití. Při nedostupném nabití se místo prázdného ukazatele zobrazí
pomlčka, aby stav nebyl zaměněn za skutečných 0 %. Při chybě či zastarání API
se u času objeví STARÁ DATA. Při aktualizaci z 0.2.0 není nutná změna mapování.
Položka `select` se pouze čte; doplněk ji nemění.

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

## Vzhled od 0.4.0

Karty mají rozložení 3 × 2: PANELY / MĚNIČE / TUV a SÍŤ / BATERIE / TESLA.
Spojnice mezi řadami tvoří pouze vizuální společnou sběrnici. Nezobrazují
skutečné zapojení ani ověřený směr toku energie.

Silné segmentové ukazatele výkonu panelů, měničů a sítě používají rozsah
0–8 kW. U sítě se délka odvozuje z absolutní hodnoty; znaménko zůstává u čísla.
Při překročení 8 kW je bar plný, číselná hodnota se neomezuje. Ukazatele nabití
baterie, TUV a Tesly mají rozsah 0–100 %. Chybějící hodnoty mají místo baru
pomlčku, takže se nepletou s potvrzenou nulou.

Režim wallboxu je velkým písmem vpravo dole; dlouhý název se nejprve zmenší,
případně zkrátí. Vlevo zůstává čas a upozornění na stará data. Aktualizace
z 0.2.0 nebo 0.3.0 nepotřebuje změnu mapování senzorů.

## Zjednodušení vzhledu od 0.5.0

Hodnoty mají velké číslice a malé jednotky; pomocné popisky uvnitř karet a
popisky krajů výkonové stupnice se nezobrazují. Kladná hodnota nemá plus,
záporná zachovává mínus. TUV je vycentrováno jako panely a měniče.
Bary mají jednoduchý rámeček a souvislou výplň. Rozsah zůstává 0–8 kW pro
panely, měniče a velikost výkonu sítě, 0–100 % pro nabití baterie/TUV/Tesly.
Mapování entit, význam hodnot a další nastavení není potřeba měnit.
