- Conținut:
````markdown name=README.md
# Pipeline Umbra‑Băncii – demo skeleton

Acest repository conține structura minimă pentru a rula pipeline-ul de analiză Umbra Băncii cu GitHub Actions (cron la 15min).  
Vezi fișierul `.github/workflows/umbrella_cron.yml` pentru detalii.  
Primul output va fi generat în folderul `output/` și arhivat ca artifact la fiecare rulare.

**Pași următori:**  
1. Rulează workflow-ul (“Run workflow” în tab-ul Actions).
2. Descarcă artifactul “reports” pentru a vedea fișierele YAML generate.
3. Vom adăuga împreună modulele reale și output-ul complet, pas cu pas.
