---
type: Execution Prompt
title: Stream C — спека фазы 2
description: Раздача рабочему C. Spec Kit + OKF. Стоп после spec.md. Код не писать.
tags: [spec-kit, "001", stream-c, specify]
timestamp: 2026-08-19T16:20:00Z
feature: 001-burger-mvp
---

# Stream C: только спека (контроль оркестратора)

После G9. Корзина A 10/10. `POST /api/price` **не** писать, пока спека не принята.

OKF: один концепт = один файл в бандле `specs/001-burger-mvp/`. Не создавать
`specs/002-*`. `.specify/` не заводить.

---

## Промпт (скопировать субагенту целиком)

```
Роль: Рабочий C (фаза 2, SSE, Tutu) хакатон-проекта «Бургер». Spec Kit specify + OKF.
Стоп после спеки. Не plan/tasks/implement.

Workspace: корень этого репозитория
Ответ оркестратору — по-русски.

Прочитай:
- specs/001-burger-mvp/spec.md, index.md, readiness-gate.md
- specs/001-burger-mvp/PROMPT-stream-c.md
- plans/00-orchestration.md §0 §3 (G10 час 26, сквозной /places→/price)
- plans/worker-C-phase2.md, plans/api-contract.md, lib/tutu_mcp.py (импорт, не копия)
- plans/deploy-vps.md (край SSE: nginx 8080, proxy_buffering off; не чужой gzip-прокси)
- open-issues.md B2 V3, mvp-spec.md §4 §7 §10 (НЕ §5/§12)

Приоритет: schema.sql > api-contract > orchestration §0 > mvp-spec.
leg = свойство ребра (B2). Guard только из lib/tutu_mcp.py.

Напиши РОВНО два файла:
1) specs/001-burger-mvp/stream-c-phase2.md
2) specs/001-burger-mvp/checklists/stream-c-requirements.md

Frontmatter: type: Feature Spec, feature: 001-burger-mvp, status: draft.

Тело:
- одна фраза: origin+даты → SSE цены/чекаут
- границы: не фаза 1, не фронт, не ингест; один FastAPI-процесс с B (stack.md)
- старт на fixtures/ legs+hotel+эталон; цена = fixture-confirmed пока нет live Tutu
- SC-ranking не твой валить; SC-price live best-effort ±15% после живого прогона
- события resolved|leg|hotel|breakdown|checkout|warning|done по одному (G6)
- первый leg ~3 с; окна дат лениво (V3); cluster_id от B как в контракте, иначе 404
- G10 конец часа 26: /price по тому же cluster_id, resolved+leg+done по одному
- checkout_url как вернул сервер; stay_total; 0 RUB = отсутствие; timeout >= 30s
- user scenarios, FR, assumptions; ссылки на швы не копипаста
- ASCII в идентификаторах

ЗАПРЕЩЕНО: index.md, log.md, orchestration, второй tutu_mcp, product /api/price код.

Выдача: пути + 5 строк к контролю.
```
