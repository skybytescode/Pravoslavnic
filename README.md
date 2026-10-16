# Pravoslavnic

Ceaslov pe ceasurile zilei, ca aplicație web (PWA): deschide automat slujba
corespunzătoare orei curente și trimite o notificare cu 5 minute înainte de
fiecare ceas. Construit după modelul [Ceaslovnic](https://github.com/skybytescode/Ceaslovnic),
dintr-un singur document sursă: `Repository/Ceasurile.docx`.

## Program

| Ora   | Slujba                 |
|-------|------------------------|
| 00:00 | Miezonoptica           |
| 05:00 | Utrenia                |
| 06:00 | Ceasul Întâi           |
| 07:30 | Mijloceasul Întâi      |
| 09:00 | Ceasul al treilea      |
| 10:30 | Mijloceasul al treilea |
| 12:00 | Ceasul al șaselea      |
| 13:30 | Mijloceasul al șaselea |
| 15:00 | Ceasul al nouălea      |
| 16:30 | Mijloceasul al nouălea |
| 18:00 | Vecernia               |
| 21:00 | Pavecernița mică       |

## Calendar cu alarme

`docs/pravoslavnic.ics` conține cele 12 slujbe ca evenimente zilnice, fiecare
cu o alarmă cu 5 minute înainte (utilă pe iPhone, unde aplicația web nu poate
programa notificări). Se importă deschizând
<https://skybytescode.github.io/Pravoslavnic/pravoslavnic.ics> și apăsând
**Add All**. Regenerare după schimbarea programului: `python3 gen_calendar.py`.

## Reconstruire după modificarea textului

```sh
python3 split.py        # Repository/Ceasurile.docx → extracted/<slug>.xml
python3 extract.py      # extracted/ → content.json
python3 build_pages.py  # content.json → docs/content/*.html (+ versiunea cache din sw.js)
node test_schedule.js   # verifică alegerea slujbei după oră
```

## Rulare locală

```sh
cd docs && python3 -m http.server 8000
```

apoi deschideți <http://localhost:8000/>.
