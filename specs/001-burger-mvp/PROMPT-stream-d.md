---
type: Execution Prompt
title: Stream D — спека фронта
description: Раздача рабочему D. Spec Kit + OKF. Стоп после spec.md. Код не писать.
tags: [spec-kit, "001", stream-d, specify]
timestamp: 2026-08-19T16:20:00Z
feature: 001-burger-mvp
---

# Stream D: только спека (контроль оркестратора)

После G9. Корзина A 10/10. React/карту **не** писать, пока спека не принята.
Старт исполнения потом на моках контракта + фикстурах эталона и запасного бургера.

OKF: концепт в `specs/001-burger-mvp/`. Не `specs/002-*`.

---

## Промпт (скопировать субагенту целиком)

```
Роль: Рабочий D (фронт) хакатон-проекта «Бургер». Spec Kit specify + OKF.
Стоп после спеки. Не plan/tasks/implement. Не писать приложение.

Workspace: корень этого репозитория
Ответ оркестратору — по-русски.

Прочитай:
- specs/001-burger-mvp/spec.md, index.md, readiness-gate.md
- specs/001-burger-mvp/PROMPT-stream-d.md
- plans/00-orchestration.md §0 §3 (G10 час 26)
- plans/worker-D-frontend.md, plans/api-contract.md, plans/stack.md, plans/deploy-vps.md
- mvp-spec.md §3 §10 (НЕ §5/§12), open-issues.md V2 V4, ingredients.yaml (плотность)

Приоритет: schema.sql > api-contract > orchestration §0 > mvp-spec.
Стек заморожен: React 18 + Vite + TS + MapLibre (не Leaflet), npm, Node 20.
Демо-край: nginx :8080 (не чужой домен).

Напиши РОВНО два файла:
1) specs/001-burger-mvp/stream-d-frontend.md
2) specs/001-burger-mvp/checklists/stream-d-requirements.md

Frontmatter: type: Feature Spec, feature: 001-burger-mvp, status: draft.

Тело:
- одна фраза UX: бургер → карта мест без origin → потом origin и цены по SSE
- инверсия: направление — выход
- старт на моках api-contract + fixtures эталон №1 и запасной бургер
- меню с плотностью; ползунок 50/100/150 max 150; фаза 1 без цен
- SSE по мере событий, не пачкой; breakdown обязателен; checkout_url не трогать
- серые карточки не исчезают; «почти подходит» режется первым при пожаре (B4)
- карта покрытия (V4) честная дыра; часы: три состояния, веб-поиск не в 001 как полный
- G10 час 26: пользователь видит /places топ и стрим /price по одному cluster_id
- SC-ranking в UI как топ-5 с фикстур; цена fixture-confirmed до live
- user scenarios, FR, assumptions
- ASCII в идентификаторах

ЗАПРЕЩЕНО: index.md, log.md, orchestration, frontend/src продукт, новые зависимости.

Выдача: пути + 5 строк к контролю.
```
