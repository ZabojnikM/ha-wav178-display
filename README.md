# WAV178 FVE Display pro Home Assistant

Python doplněk pro Waveshare 4,2″ e-Paper Cloud Module, 400×300, s originálním
firmwarem. Čte Home Assistant a posílá černobílý dashboard přes TCP 6868.
Po instalaci běží na zařízení s Home Assistant OS a nevyžaduje zapnutý Windows PC.

Zobrazuje SOC baterie FVE, výkon panelů, baterie a sítě, horní/spodní teplotu TUV,
hodnotu entity výkonu TUV a výkon wallboxu. Znaménko baterie je nastavitelné;
síť se zatím zobrazuje s původním znaménkem. Žádné řídicí služby HA nevolá.

## Instalace přes GitHub

Instalační adresa pro ověřenou větev `stable`:

```text
https://github.com/ZabojnikM/ha-wav178-display#stable
```

V Home Assistant OS otevřete **Nastavení → Aplikace / Doplňky → Obchod → ⋮ →
Repozitáře** a vložte čistou adresu výše. Po obnově seznamu vyberte **WAV178 FVE
Display**, nainstalujte a vyplňte ID svých senzorů v konfiguraci. Přesný postup
je v [návodu doplňku](wav178_display/DOCS.md).

První verze se během instalace sestaví z veřejného zdrojového kódu. Nevyžaduje
přihlášení ke GHCR ani ruční HA token. Podporované cíle: Raspberry Pi 4 s 64bitovým
Home Assistant OS (`aarch64`) a PC (`amd64`). Kontejnery se před vydáním
ověřují na nativních GitHub Actions běžcích pro obě architektury.

## Nastavení displeje

Displej je TCP klient. Jeho **Host_IP musí být LAN IPv4 zařízení s HA**, nikoli
IP displeje, port 8123 nebo původního Windows serveru. Server poslouchá na 6868.
Wi-Fi a Host_IP se nastavují přes Bluetooth; zveřejněná originální aplikace
používá Bluetooth Classic SPP/RFCOMM, nikoli BLE/GATT.

Při přesunu nejprve spusťte doplněk a ověřte načítání HA v jeho webovém náhledu.
Teprve pak změňte Host_IP displeje. Původní Windows server může během přípravy
dál běžet. Port 6868 patří do domácí sítě, ne na veřejný internet.

## Chování a stav ověření

Server průběžně posílá obraz a drží spojení otevřené. Neodesílá Shutdown,
časovaný spánek ani restart zařízení. Při spuštění či skutečném vypnutí může
být potřeba Wakeup; probuzení vypnutého rádia není implementované.

Původní Windows prototyp stejného protokolu fyzicky dokončil tři automatické
aktualizace bez dalšího Wakeup. To není měření dlouhodobé výdrže ani potvrzení
nového doplňku na konkrétní instalaci HA. [Podrobnosti ověření](docs/VALIDATION.md).

## Vývoj

```powershell
python -m pip install Pillow==12.3.0
$env:PYTHONPATH = "$PWD\wav178_display\app"
python -m unittest discover -s tests -v
```

Kontejner:

```sh
docker build --build-arg BUILD_ARCH=amd64 -t wav178:test wav178_display
python scripts/container_smoke.py wav178:test
```

Konfigurace, soukromé exporty a tokeny se nepublikují. Prázdná výchozí mapování
nepředstírají existenci konkrétních entit. [Vydávání](docs/RELEASE.md),
[původ protokolu](docs/PROTOCOL.md), [licence podkladů](THIRD_PARTY_NOTICES.md).
