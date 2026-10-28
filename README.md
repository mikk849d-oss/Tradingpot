# Gratis GitHub Actions-investeringbot (v1 cloud)

Dette er en **lille første version**: Den henter **rigtige historiske kurser** på et begrænset udvalg af 32 aktier, kører fire faktorberegninger parallelt, rangerer kandidater og gemmer en rapport. **Den handler aldrig**. Kimi, Grok og OpenAI kan tilsluttes med separate API-nøgler (valgfrit, kan koste penge).

**VIGTIGT:** Ingen valideret strategi, ingen fundamentals, ingen fuld global screening eller avanceret risikostyring. Sæt ikke penge efter scores alene. Yahoo-data er uofficielle og kan fejle. Botten stopper ved utilstrækkelige data.

## Kom i gang uden at installere Python

1. Opret en gratis konto på [github.com](https://github.com).
2. Vælg **New repository**, navn f.eks. `min-investeringsbot`, vælg **Private**, og vælg **Create repository**.
3. Pak ZIP-filen ud. Upload filerne og **mappen `.github` med undermappen `workflows`** til repositoryet. Det er vigtigt, at filstien `.github/workflows/daily-scan.yml` bevares. Hvis web-upload ikke bevarer mapperne, brug GitHub Desktop til at kopiere projektfilerne ind og tryk **Commit** / **Push**, eller opret workflowfilen direkte via **Add file → Create new file** og indtast hele stien.
4. Åbn repositoryet → fanen **Actions** → **Daglig investeringsscanner** → **Run workflow** → **Run workflow**.
5. Klik ind på seneste kørsel. Når den er færdig, vises en **rapport i job-resuméet**. Nederst i kørslen under **Artifacts** kan `aktiescanner-rapport` hentes med `rapport.md` og `resultater.json`.
6. Herefter starter den automatisk mandag-fredag kl. **22:47 UTC** (typisk kl. 23:47 dansk vintertid, 00:47 dansk sommertid). Det er efter normal lukketid på amerikanske børser. GitHub garanterer ikke præcis levering og kan springe en kørsel over.

**Gratis:** GitHub Free har normalt 2.000 inkluderede Actions-minutter pr. måned for private repositories. AI-API'er kan koste penge. Vi behøver **ingen API-nøgler** til første kørsel.

## AI-agenter senere

Under repositoryets **Settings → Secrets and variables → Actions**:
- Under **Secrets** kan du tilføje `KIMI_API_KEY`, `XAI_API_KEY` og/eller `OPENAI_API_KEY`.
- Under **Variables** tilføjes den tilhørende model `KIMI_MODEL`, `GROK_MODEL` og/eller `OPENAI_MODEL` med et **aktivt model-id fra den enkelte leverandørs API**.

Ingen model kontaktes uden både nøgle og model-id. API-forbrug kan koste penge. Skriv aldrig nøgler i filer eller chats.

## Udvikling og fremtidig udvidelse

- `main.py`: henter kurser via `yfinance`, scorer fire prisfaktorer, kører valgfrie AI-kritikere og skriver rapporter.
- `tests/`: offline tests uden net eller API-nøgler.
- `.github/workflows/daily-scan.yml`: automatisk tidsplan, tests, rapport-artefakter.
- `TICKERS` (valgfrit): miljøvariabel med kommaseparerede Yahoo-tickers for et andet afgrænset aktieunivers.

Det kan godt være at AI-agenterne ikke er konfigurerede ved den første kørsel; rapporten viser tydeligt deres status. AIs kommentarer **ændrer ikke den kvantitative rangering**. For en ægte Jim Simons-inspireret model er næste milepæl *punkt-i-tid fundamentaldata, out-of-sample backtest og virkelighedstro handelsomkostninger*.

### Kør lokalt (valgfrit)

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python main.py --demo       # fiktive testkurser, ingen netdata
python main.py              # reelle historiske kurser
```
