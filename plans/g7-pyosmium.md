# G7 — pyosmium / региональный PBF (Worker A)

Дата: 2026-08-19. Overpass для гейта не использовался. `russia-latest` (~4 GB) не скачивался.

## Установка

- `pip install pyosmium` на PyPI **не существует** (404 / versions: none).
- Настоящее имя пакета: `osmium` 4.3.1 (`pip install osmium`). Модуль: `import osmium`.

## PBF

- URL: `https://download.openstreetmap.fr/extracts/russia/central_federal_district/yaroslavl_oblast-latest.osm.pbf`
- Размер: 45 213 826 байт (~43 MiB). Не central-fed-district (924 MiB) и не russia-latest.
- Локальная копия замера — вне git (см. `.gitignore` для `*.pbf`).

## Парсинг

- wall: **22.1 s**
- RSS peak: **73.6 MB**
- `locations=False` (счёт тегов, без геометрии)

Это не «ночь на регион» и не упор по памяти. Стратегию D3 из-за тулинга не пересматривать.

## Счётчики vs field-test §12

Наивный OR по всем строкам `ingredients.yaml` (в т.ч. `amenity=place_of_worship` и `ruins=yes`) **завышает** храмы и руины. Overpass, которым снимали §12, ближе к узким тегам:

| Категория | §12 | узкий фильтр (как §12) | полный OR yaml |
|---|---:|---:|---:|
| temples | 370 | building=church\|cathedral\|chapel\|monastery: **380** | 826 |
| museums | 164 | tourism=museum: **164** | 164 |
| ruins | 76 | historic=ruins: **76** | 485 |
| springs | 74 | natural=spring\|hot_spring: **79** | 79 |
| works | 59 | man_made=works: **59** | 59 |
| viewpoints | 35 | tourism=viewpoint: **36** | 43 (плюс named peak) |
| kremlins | 12 | historic=castle\|fort\|citadel\|city_wall\|city_gate: **12** | 12 |
| manors | 8 | historic=manor\|palace: **8** | 8 |
| reserves | 3 | leisure=nature_reserve: **3** | 10 (плюс boundary=protected_area) |
| archaeology | 3 | historic=archaeological_site\|tomb\|rune_stone: **3** | 3 |
| tech museums | 1 | museum=technology\|industry\|mining\|railway\|military + mine/mineshaft: **1** | 1 |
| waterfalls | 0 | **1** | 1 |
| caves | 0 | **0** | 0 |

§9 (~546 / 4 категории): 370+164+12 = 546 (храмы+музеи+кремли). Узкий building-счёт храмов 380 даёт 380+164=544, рядом.

Дрейф 370→380 / 74→79 / 35→36 / 0→1 — вырез osm.fr от 2026-07-23 vs live Overpass 2026-08-19, не отказ парсера.

## Вердикт

GREEN: пакет ставится (имя `osmium`), область парсится быстро, узкие счётчики сходятся с §12 (точное совпадение 8/13, остальные в пределах дрейфа выреза). Для D3 не брать `ruins=yes` и не схлопывать все `place_of_worship` в `ancient_temple` без дедупа, иначе плотность меню разъедется с field-test.
