---
type: Spec Checklist
title: Stream D — quality checklist
description: Проверка полноты stream-d-frontend.md до plan/tasks/кода. Spec Kit quality + продуктовые ворота потока D.
tags: [spec-kit, "001", stream-d, checklist]
timestamp: 2026-08-19T16:30:00Z
feature: 001-burger-mvp
status: draft
---

# Specification Quality Checklist: Stream D — фронт

**Purpose**: Validate specification completeness and quality before planning or writing the React app
**Created**: 2026-08-19
**Feature**: [stream-d-frontend.md](../stream-d-frontend.md)
**Bundle**: [spec.md](../spec.md) (рамка 001, не дублировать)

Валидация 2026-08-19: все пункты ниже **pass**. `[NEEDS CLARIFICATION]` в спеке нет. Plan / tasks / `frontend/src` — не начинать без зелёного оркестратора.

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
  - Pass с оговоркой шва: React/Vite/MapLibre/npm/Node 20 живут только в Assumptions (стек G8 заморожен, не выбирается). Имена `POST /api/places`, `POST /api/price`, SSE-события и `cluster_id` — **замороженный UX-шов G10**, не выбор реализации. В FR нет компонент, стора, Leaflet.
- [x] Focused on user value and business needs
  - Одна фраза UX + инверсия (направление — выход). Ценность: места до origin, честные дыры, серые карточки, fixture-confirmed до live.
- [x] Written for non-technical stakeholders
  - Проза по-русски для оркестратора/жюри. Идентификаторы контракта в ASCII как в api-contract (иначе G10 непроверим).
- [x] All mandatory sections completed
  - Границы, старт на моках, User Scenarios, Edge Cases, FR-D1…FR-D17, Key Entities, Success Criteria, Assumptions, швы.

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
  - Радиус только 50/100/150 max 150; фаза 1 без цен; SSE по событиям; `checkout_url` as-is; серые не исчезают; «почти подходит» режется первым (B4).
- [x] Success criteria are measurable
  - Топ-5 обоих бургеров; G10 на одном `cluster_id`; 100% меток плотности; цена с меткой `fixture-confirmed`.
- [x] Success criteria are technology-agnostic (no implementation details)
  - SC сформулированы как то, что видит пользователь. Имена эндпоинтов в SC-D4 — критерий интеграции G10 из orchestration §3, не стек.
- [x] All acceptance scenarios are defined
  - US1–US5 Given/When/Then.
- [x] Edge cases are identified
  - Пустой бургер, неверный радиус, 404 на неизвестный id, цена 0, stay_total, misresolved ≠ not_sellable, тот же `cluster_id` при смене радиуса.
- [x] Scope is clearly bounded
  - Входит D в 001 / не входит (полный веб-поиск часов, LLM «другое», вся РФ, чужой домен как край, резать пары).
- [x] Dependencies and assumptions identified
  - api-contract, G9 fixtures, ingredients.yaml, G6 `:8080`, F10 proxy, F13 `ruins`.

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
  - Фаза 1 без origin, фаза 2 SSE, серые + «почти подходит», карта покрытия, часы.
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification
  - Код приложения, структура `frontend/src`, новые зависимости — вне спеки. Старт «на моках контракта» — порядок работ после зелёного, не реализация.

## Stream D product gates (оркестратор)

- [x] UX-фраза: бургер → карта мест без origin → origin и цены по SSE; инверсия зафиксирована
- [x] Старт на моках api-contract + `fixtures/etalon_1.json` + `fixtures/backup_single_hub.json`; переключатель mock/live
- [x] Метка плотности на каждой карточке меню обязательна
- [x] Ползунок 50/100/150, max 150, дефолт 100 (V2)
- [x] Фаза 1 без цен
- [x] SSE инкрементально, не пачкой; `breakdown` обязателен; `checkout_url` не трогать
- [x] Серые карточки остаются; «почти подходит» режется первым при пожаре (B4)
- [x] Карта покрытия — честная дыра (V4)
- [x] Часы: три состояния; полный веб-поиск не в 001
- [x] G10 час 26: пользователь видит топ `/places` и стрим `/price` по одному `cluster_id`
- [x] UI не переранжирует `places[]`; клик пары для SSE; цена `fixture-confirmed` до live обоих сценариев
- [x] Край демо: nginx `:8080` (не чужой домен)
- [x] ASCII в идентификаторах; проза русская
- [x] Не созданы `specs/002-*` и `.specify/`; не правлены index.md, log.md, orchestration, `frontend/src`

## Notes

- Items marked incomplete require spec updates before `/speckit-clarify` or `/speckit-plan`.
- Эта итерация: **стоп после спеки**. Зелёный оркестратора → тогда plan/tasks и моки в приложении.
- Не считать 4 342 ₽ живым SC-price: в фикстуре `price_status: fixture-confirmed`.
