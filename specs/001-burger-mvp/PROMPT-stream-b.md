---
type: Execution Prompt
title: Stream B — спека фазы 1
description: Раздача рабочему B. Spec Kit + OKF. Стоп после spec.md. Код не писать.
tags: [spec-kit, "001", stream-b, specify]
timestamp: 2026-08-19T16:20:00Z
feature: 001-burger-mvp
---

# Stream B: только спека (контроль оркестратора)

После G9. Корзина A 10/10. Код кластеризации и `POST /api/places` **не** писать,
пока оркестратор не примет эту спеку.

OKF ([v0.1](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing)):
один концепт = один markdown; путь файла = идентичность; YAML frontmatter
(`type`, `title`, `description`, `tags`, `timestamp`); связи — обычные ссылки.
Бандл уже есть: `specs/001-burger-mvp/`. Каркаса `.specify/` нет — **не** заводить
`specs/002-*`. Не плодить второй бандл.

---

## Промпт (скопировать субагенту целиком)

```
Роль: Рабочий B (фаза 1) хакатон-проекта «Бургер». Spec Kit specify + OKF.
Стоп после спеки. Не /speckit-plan, не tasks, не implement.

Workspace: корень этого репозитория
Ответ оркестратору — по-русски.

Прочитай:
- specs/001-burger-mvp/spec.md, index.md, readiness-gate.md
- specs/001-burger-mvp/PROMPT-stream-b.md
- plans/00-orchestration.md §0 §1 §3 (G10 = конец часа 26, /places→/price)
- plans/worker-B-phase1.md, plans/api-contract.md, schema.sql (швы, не копировать схему)
- open-issues.md B3 V2, mvp-spec.md §6 §9 (кластеризация/significance; НЕ §5/§12 как истина)

Приоритет: schema.sql > plans/api-contract.md > orchestration §0 > mvp-spec.md.
§5 sellable_modes-как-узел и §12 cut pairs ОТМЕНЕНЫ (B2, B4).

Напиши РОВНО два файла, больше ничего:
1) specs/001-burger-mvp/stream-b-phase1.md
2) specs/001-burger-mvp/checklists/stream-b-requirements.md

Frontmatter как у spec.md: type: Feature Spec, feature: 001-burger-mvp, status: draft,
timestamp ISO, tags включая spec-kit и stream-b.

Тело (тонкая спека, не дублировать ТЗ):
- одна фраза что строит B
- границы: входит / не входит (фаза 2, фронт, ингест — чужое)
- старт на золотых fixtures/ (эталон №1 + запасной одноузловой бургер B4)
- диски вокруг узлов, НЕ DBSCAN; пары нерезаемы
- coverage_ratio доминирует (лексикографика, потом cluster_score)
- cluster_id из api-contract (множество hub_id, не радиус)
- SC-ranking жёсткий офлайн на фикстурах (оба бургера в топ-5); SC-price НЕ твой
- G10: к концу часа 26 /places отдаёт эталон в топ-5 на фикстурах/волне 1
- ссылки на frozen artifacts, не копипаста schema/api
- user scenarios + testable FR + assumptions
- ASCII в идентификаторах кода; проза на русском

Чеклист Spec Kit quality (requirements.md): отметить pass/fail. Без [NEEDS CLARIFICATION] больше 3.

ЗАПРЕЩЕНО: править index.md, log.md, orchestration, api-contract, schema, lib, backend product routes, fixtures.
ЗАПРЕЩЕНО: писать кластеризацию, /api/places handler, тесты приёмки как код.

Выдача: пути двух файлов + 5 строк «готово к контролю / не готово».
```
