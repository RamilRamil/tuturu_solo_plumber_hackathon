---
type: Spec Quality Checklist
title: Stream C — качество спеки фазы 2
description: Валидация stream-c-phase2.md до /speckit-plan и до кода POST /api/price.
tags: [spec-kit, "001", stream-c, checklist]
timestamp: 2026-08-19T16:25:00Z
feature: 001-burger-mvp
status: draft
---

# Specification Quality Checklist: Stream C — фаза 2 (SSE / Tutu)

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-19
**Feature**: [stream-c-phase2.md](../stream-c-phase2.md)

Это чеклист **потоковой** спеки C внутри бандла 001 (не новый `specs/002-*`).
Продуктовая рамка MVP — [spec.md](../spec.md). Имена швов (SSE, FastAPI, nginx)
здесь — идентичность замороженного контракта, не новая архитектура.

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Stream C gates (оркестратор)

- [x] Одна фраза: origin+даты → поток цен/чекаута
- [x] Границы: не фаза 1, не фронт, не ингест; один процесс с B
- [x] Старт на `fixtures/` legs+hotel+эталон; цена `fixture-confirmed` до live Tutu
- [x] `SC-ranking` не валит C; `SC-price` ±15% только после живого прогона
- [x] События `resolved|leg|hotel|breakdown|checkout|warning|done` по одному (G6)
- [x] Первый `leg` ~3 с; окна дат лениво (V3)
- [x] `cluster_id` от B по контракту, иначе HTTP 404
- [x] G10: `/price` по тому же `cluster_id` — `resolved` + ≥1 `leg` + `done` по одному
- [x] `checkout_url` как вернул сервер; отель `stay_total`; 0 RUB = отсутствие; timeout ≥ 30 с
- [x] Guard только через `lib/tutu_mcp.py`; `leg` — свойство ребра (B2)
- [x] Край SSE: nginx `:8080`, не чужой gzip-прокси
- [x] Ссылки на швы вместо копипасты payload/схемы

## Validation (iteration 1)

| Item | Result | Notes |
|---|---|---|
| Implementation details | PASS | Стек и имена событий — цитаты G2/G6/G8, не изобретение. Payload не скопирован. |
| User value | PASS | Поток цен после origin; первое плечо без ожидания полного расчёта. |
| Audience | PASS | Для контроля оркестратора/архитектора; зритель продукта — [spec.md](../spec.md). |
| Mandatory sections | PASS | Сценарии, FR-C1..C20, Success Criteria, entities, assumptions. |
| NEEDS CLARIFICATION | PASS | 0 маркеров. F7/F12 явно в assumptions как on-the-fly. |
| Testable FR | PASS | 404 vs warning, G10 тройка событий, 0 RUB, stay_total, timeout. |
| Measurable SC | PASS | ~3 с, G10, ±15% после live, 404, fixture-confirmed. |
| Tech-agnostic SC | PASS | SC сформулированы как исход для пользователя; G10 — приёмка чекпоинта. |
| Scenarios | PASS | Счастливый путь, 404, мисрезолв, B2, окна, G10. |
| Edge cases | PASS | Пустой быстрый ответ, soft-fail режимов, avia passengers, кэш-фолбэк. |
| Scope | PASS | Явный not-in: B/D/A, второй tutu_mcp, код хендлера на specify. |
| Dependencies | PASS | Таблица швов + приоритет schema > contract > orchestration §0. |
| FR ↔ acceptance | PASS | Сценарии 1–6 покрывают FR-C1..C20. |
| Impl leak | PASS | Нет деревьев каталогов, нет псевдокода хендлера, нет копипасты `tutu_mcp`. |

## Notes

- Все пункты **pass**. Спека готова к контролю оркестратора.
- **Не** запускать `/speckit-plan`, `/speckit-tasks`, код `POST /api/price` без зелёного.
- Бандл остаётся `specs/001-burger-mvp/`. `.specify/` и `specs/002-*` не создавались.
- Index/log/orchestration/schema/`lib/tutu_mcp.py` этим шагом не трогались.
