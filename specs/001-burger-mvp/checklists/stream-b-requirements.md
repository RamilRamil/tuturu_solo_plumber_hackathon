---
type: Spec Quality Checklist
title: Stream B — качество спеки фазы 1
description: Чеклист Spec Kit requirements.md для stream-b-phase1.md. Контроль оркестратора до plan/tasks/implement.
tags: [spec-kit, "001", stream-b, checklist]
timestamp: 2026-08-19T12:25:00Z
feature: 001-burger-mvp
status: draft
---

# Specification Quality Checklist: Stream B — фаза 1

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-19
**Feature**: [stream-b-phase1.md](../stream-b-phase1.md)

Итерация валидации: 1 (после написания спеки). Маркеров `[NEEDS CLARIFICATION]` в
спеке нет.

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

## Notes

- Именованные швы `POST /api/places` и `cluster_id` — замороженный продуктовый
  контракт (G2), не стек. В спеке нет Python / FastAPI / SQLite / гаверсинуса.
  Поля входа (`ingredients`, `radius_km`) нужны, чтобы SC-ranking был проверяем.
- SC-B4 сформулирован как «сразу, без внешней транспортной системы», не как
  «p95 < 200 мс». Число 200 мс оставлено в допущениях как шов плана B.
- Обязательные разделы Spec Kit в [stream-b-phase1.md](../stream-b-phase1.md):
  сценарии US1–US5, FR-B1–FR-B12, сущности, SC-B1–SC-B6, допущения, границы.
- **Было блокером SC-B1** (в specify занижено как «вне спеки»): эталон просил
  `industrial_site` при честных POI `industrial_museum`. **Разрешено
  оркестратором 2026-08-19:** эталон = `ancient_temple` + `industrial_museum`
  на замороженном шве. Точный матчинг без подмены категорий сохранён.
  Фейковые `industrial_site`-POI не добавлять. SC-B1 достижим на честных
  фикстурах; до implement шов уже выровнен.
- **Coverage-честность эталона (оркестратор 2026-08-19, 1b+2a):** одиночный
  Ярославль закрывает бургер. **SC-B1 hard** = пара существует в `places[]`
  с полным покрытием при пустой `cluster`, плюс SC-B3. «Пара в топ-5» —
  smoke. US3 = полное покрытие выше неполного, не «пара выше полного
  одиночки».

**Вердикт:** pass. Готово к контролю оркестратора. Не переходить к
`/speckit-plan`, `tasks.md` или коду без зелёного.
