# Changelog

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
