# Původ protokolu

Primární podklady:

- [Waveshare wiki](https://www.waveshare.com/wiki/4.2inch_e-Paper_Cloud_Module)
- [Oficiální Python Windows demo](https://files.waveshare.com/upload/5/57/Cloud_WIN.7z)
- [Oficiální zdroj konfigurační aplikace](https://files.waveshare.com/upload/3/33/Cloud_e-paper.7z)
- [Komunitní wavesharecloud](https://github.com/headblockhead/wavesharecloud/tree/4685009cf106abab7a49f6581403c4580654144b)

Příkaz: `;` + tělo + `/` + binární XOR těla. ACK: `$` + jeden binární bajt + `#`.
Samotné ACK může obsahovat `$`, `#` i NUL. Proto se nečte jako obecný text.
Příkazy C/N ověřují zámek, G vrací ID, F zahajuje obraz a D dokončuje přenos.

Obraz 400×300 má 15000 bajtů, černá 0, bílá 1, po řádcích, MSB první.
Datový rámec: 0x57 + adresa u32 BE + délka u32 BE + num u8 + data + XOR.
Délka je 1024, poslední rámec doplněn 0xFF; celkem patnáct rámců po 1035 bajtech.
XOR nezahrnuje 0x57. Ukázky výrobce i Go posílají zakončení 0x57 + 12 nulových
bajtů (13 celkem), které implementace zachovává včetně paddingu.

Textová dokumentace doporučuje konstantní num, kódy ukázek cyklus 0,1,2,3.
Výchozí zero odpovídá fyzicky ověřenému prototypu. Sector je volitelný.
Před dalším rámcem se čeká na jeho přesné ACK; nejasné odpovědi ukončí relaci.

První nastavení podle aplikace používá Bluetooth Classic SPP s UUID
00001101-0000-1000-8000-00805f9b34fb, nikoli GATT. Doplněk Bluetooth nepotřebuje:
počítá s již nastavenou Wi-Fi a Host_IP. Neimplementuje OTA ani neznámé příkazy.

Napětí `b` se zatím nečte: Windows demo násobí výsledek třemi, Go jej považuje
přímo za mV. Časovaný spánek r výrobce vyhrazuje pro 2,13″. Tyto domněnky se
nepřenášejí do odhadu výdrže nebo automatického probuzení 4,2″.
