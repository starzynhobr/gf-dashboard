from __future__ import annotations

import json
from datetime import UTC, date, datetime
from typing import Any, cast
from uuid import UUID

from PySide6.QtCore import QObject, Slot

from gf_dashboard.application.catalog import DungeonCatalogService
from gf_dashboard.application.currency_rates import CurrencyRateService
from gf_dashboard.application.market_quotes import MarketQuoteService
from gf_dashboard.application.ports import FarmUnitOfWork, TowerUnitOfWork
from gf_dashboard.application.sales import SaleCommand, SaleService
from gf_dashboard.application.services import (
    ActivityCompletionService,
    DashboardLayoutService,
    ManagementService,
    WorkspaceService,
)
from gf_dashboard.application.tower import TowerDropInput, TowerSessionService
from gf_dashboard.domain.errors import ConflictError, DomainError, NotFoundError, ValidationError
from gf_dashboard.domain.value_objects import EntityId, Gold, WorkspaceId
from gf_dashboard.infrastructure.autostart import WindowsAutostartService
from gf_dashboard.infrastructure.daily_operations import SqliteDailyOperations
from gf_dashboard.infrastructure.dashboard_reader import SqliteDashboardReader
from gf_dashboard.infrastructure.in_memory import SystemClock, UUIDGenerator
from gf_dashboard.infrastructure.persistence import SqliteDatabase
from gf_dashboard.infrastructure.sales_ledger import SqliteSaleLedger
from gf_dashboard.infrastructure.sqlite_repositories import SqliteUnitOfWork


class AppBridge(QObject):
    """Small, versioned boundary exposed to the trusted desktop frontend."""

    @Slot(str, result=str)
    def invoke(self, raw_request: str) -> str:
        request_id: str | None = None
        try:
            request = json.loads(raw_request)
            if not isinstance(request, dict):
                raise ValueError("request must be an object")

            request_id = self._required_string(request, "requestId")
            if request.get("version") != 1:
                return self._error(request_id, "unsupported_version", "Versão não suportada")

            method = self._required_string(request, "method")
            payload = request.get("payload", {})
            if not isinstance(payload, dict):
                return self._error(request_id, "invalid_payload", "Payload deve ser um objeto")

            if method == "system.ping":
                return self._success(
                    request_id,
                    {"message": "pong", "runtime": "desktop", "bridgeVersion": 1},
                )
            if method == "system.getAutostart":
                svc = self._autostart_service or WindowsAutostartService()
                return self._success(request_id, {"enabled": svc.is_enabled()})
            if method == "system.setAutostart":
                enabled = self._required_bool(payload, "enabled")
                svc = self._autostart_service or WindowsAutostartService()
                autostart_result = svc.set_enabled(enabled)
                return self._success(request_id, {"enabled": autostart_result})
            if method == "dashboard.today":
                if self._dashboard_reader is None:
                    return self._error(
                        request_id, "service_unavailable", "Dashboard local indisponível"
                    )
                activity_date = self._activity_date(payload)
                today = self._dashboard_reader.today_estimate_for_default_workspace(activity_date)
                if today is None:
                    return self._success(
                        request_id, {"state": "empty", "activityDate": activity_date.isoformat()}
                    )
                return self._success(
                    request_id,
                    {
                        "state": "ready",
                        "activityDate": today.activity_date.isoformat(),
                        "selectedDungeons": today.selected_dungeons,
                        "estimatedGold": today.estimated_gold.amount,
                        "estimatedPveBags": today.estimated_pve_bags,
                        "estimatedPveBagMarketValue": (
                            today.estimated_pve_bag_market_value.amount
                            if today.estimated_pve_bag_market_value
                            else None
                        ),
                        "pveBagUnitValueGold": (
                            today.pve_bag_unit_value.amount if today.pve_bag_unit_value else None
                        ),
                    },
                )
            if method == "dashboard.todayCharacters":
                if self._dashboard_reader is None:
                    return self._error(
                        request_id, "service_unavailable", "Dashboard local indisponível"
                    )
                characters = self._dashboard_reader.today_characters_for_default_workspace(
                    self._activity_date(payload)
                )
                if characters is None:
                    return self._success(request_id, {"state": "empty", "characters": []})
                return self._success(
                    request_id,
                    {
                        "state": "ready",
                        "characters": [
                            {
                                "id": character.id,
                                "name": character.name,
                                "className": character.class_name,
                                "accountName": character.account_name,
                                "completedDungeons": character.completed_dungeons,
                                "selectedDungeons": character.selected_dungeons,
                                "dailyMissionCompleted": character.daily_mission_completed,
                                "vipExpiresAt": (
                                    character.vip_expires_at.isoformat()
                                    if character.vip_expires_at
                                    else None
                                ),
                            }
                            for character in characters
                        ],
                    },
                )
            if method == "dashboard.todayActivity":
                if self._dashboard_reader is None:
                    return self._error(
                        request_id, "service_unavailable", "Dashboard local indisponível"
                    )
                overview = self._dashboard_reader.today_activity_for_default_workspace(
                    self._activity_date(payload)
                )
                if overview is None:
                    return self._success(
                        request_id,
                        {
                            "state": "empty",
                            "runsCompleted": 0,
                            "towerCompleted": 0,
                            "towerTotal": 0,
                            "recentDrops": [],
                            "monthlyGold": [],
                            "monthlyGoldTotal": 0,
                            "pveBagsEarnedToday": 0,
                        },
                    )
                return self._success(
                    request_id,
                    {
                        "state": "ready",
                        "runsCompleted": overview.runs_completed,
                        "towerCompleted": overview.tower_completed,
                        "towerTotal": overview.tower_total,
                        "recentDrops": [
                            {
                                "itemName": drop.item_name,
                                "quantity": drop.quantity,
                                "obtainedAt": drop.obtained_at.isoformat(),
                            }
                            for drop in overview.recent_drops
                        ],
                        "monthlyGold": [
                            {
                                "activityDate": point.activity_date.isoformat(),
                                "gold": point.gold.amount,
                                "pveBags": point.pve_bags,
                            }
                            for point in overview.monthly_gold
                        ],
                        "monthlyGoldTotal": overview.monthly_gold_total.amount,
                        "pveBagUnitValueGold": (
                            overview.pve_bag_unit_value_gold.amount
                            if overview.pve_bag_unit_value_gold
                            else None
                        ),
                        "earnedGoldToday": overview.earned_gold_today.amount,
                        "pveBagsEarnedToday": overview.pve_bags_earned_today,
                        "todaySalesMinor": overview.today_sales_minor,
                    },
                )
            if method == "dashboard.characterDay":
                if self._dashboard_reader is None:
                    return self._error(
                        request_id, "service_unavailable", "Dashboard local indisponível"
                    )
                day = self._dashboard_reader.character_day_for_default_workspace(
                    self._entity_id(payload, "characterId"), self._activity_date(payload)
                )
                if day is None:
                    return self._error(request_id, "not_found", "Personagem não encontrado")
                return self._success(
                    request_id,
                    {
                        "characterId": day.character_id,
                        "characterName": day.character_name,
                        "className": day.class_name,
                        "accountName": day.account_name,
                        "activityDate": day.activity_date.isoformat(),
                        "dungeons": [
                            {
                                "characterActivityId": dungeon.character_activity_id,
                                "activityId": dungeon.activity_id,
                                "name": dungeon.name,
                                "completed": dungeon.completed,
                                "targetAmount": dungeon.target_amount,
                                "gold": dungeon.gold.amount,
                                "pveBags": dungeon.pve_bags,
                            }
                            for dungeon in day.dungeons
                        ],
                    },
                )
            if method == "dashboard.saveCharacterDay":
                workspace_id = self._default_workspace_id()
                raw_ids = payload.get("completedActivityIds")
                if not isinstance(raw_ids, list) or not all(
                    isinstance(value, str) for value in raw_ids
                ):
                    raise ValueError("completedActivityIds must be an array of IDs")
                result = ActivityCompletionService(
                    cast(FarmUnitOfWork, SqliteUnitOfWork(self._required_database())),
                    UUIDGenerator(),
                    SystemClock(),
                ).save_character_day(
                    workspace_id,
                    self._entity_id(payload, "characterId"),
                    self._activity_date(payload),
                    tuple(EntityId(UUID(value)) for value in raw_ids),
                )
                return self._success(
                    request_id,
                    {
                        "completedDungeons": result.completed_dungeons,
                        "gold": result.gold,
                        "pveBags": result.pve_bags,
                    },
                )
            if method == "management.overview":
                if self._dashboard_reader is None:
                    return self._error(
                        request_id, "service_unavailable", "Cadastro local indisponível"
                    )
                management = self._dashboard_reader.management_overview()
                if management is None:
                    return self._success(request_id, {"state": "empty"})
                return self._success(
                    request_id,
                    {
                        "state": "ready",
                        "workspaceName": management.workspace_name,
                        "accounts": [
                            {
                                "id": account.id,
                                "name": account.name,
                                "serverName": account.server_name,
                                "characters": [
                                    {
                                        "id": character.id,
                                        "accountId": character.account_id,
                                        "name": character.name,
                                        "className": character.class_name,
                                        "level": character.level,
                                        "sortOrder": character.sort_order,
                                    }
                                    for character in account.characters
                                ],
                            }
                            for account in management.accounts
                        ],
                        "dungeons": [
                            {
                                "id": dungeon.id,
                                "name": dungeon.name,
                                "enabled": dungeon.enabled,
                                "targetAmount": dungeon.target_amount,
                            }
                            for dungeon in management.dungeons
                        ],
                    },
                )
            if method == "management.createAccount":
                account = ManagementService(
                    cast(FarmUnitOfWork, SqliteUnitOfWork(self._required_database())),
                    UUIDGenerator(),
                    SystemClock(),
                ).create_account(
                    self._default_workspace_id(),
                    self._required_string(payload, "name"),
                    self._required_string(payload, "serverName"),
                )
                return self._success(request_id, {"id": str(account.id), "name": account.name})
            if method == "management.createCharacter":
                character = ManagementService(
                    cast(FarmUnitOfWork, SqliteUnitOfWork(self._required_database())),
                    UUIDGenerator(),
                    SystemClock(),
                ).create_character_with_default_activities(
                    self._default_workspace_id(),
                    self._entity_id(payload, "accountId"),
                    self._required_string(payload, "name"),
                    self._required_string(payload, "className"),
                    self._required_int(payload, "level", minimum=1),
                )
                return self._success(request_id, {"id": str(character.id), "name": character.name})
            if method == "management.updateAccount":
                account = ManagementService(
                    cast(FarmUnitOfWork, SqliteUnitOfWork(self._required_database())),
                    UUIDGenerator(),
                    SystemClock(),
                ).update_account(
                    self._default_workspace_id(),
                    self._entity_id(payload, "accountId"),
                    self._required_string(payload, "name"),
                    self._required_string(payload, "serverName"),
                )
                return self._success(request_id, {"id": str(account.id), "name": account.name})
            if method == "management.updateCharacter":
                character = ManagementService(
                    cast(FarmUnitOfWork, SqliteUnitOfWork(self._required_database())),
                    UUIDGenerator(),
                    SystemClock(),
                ).update_character(
                    self._default_workspace_id(),
                    self._entity_id(payload, "characterId"),
                    self._required_string(payload, "name"),
                    self._required_string(payload, "className"),
                    self._required_int(payload, "level", minimum=1),
                )
                return self._success(request_id, {"id": str(character.id), "name": character.name})
            if method == "management.setDungeonActive":
                ManagementService(
                    cast(FarmUnitOfWork, SqliteUnitOfWork(self._required_database())),
                    UUIDGenerator(),
                    SystemClock(),
                ).set_dungeon_active(
                    self._default_workspace_id(),
                    self._entity_id(payload, "activityId"),
                    self._required_bool(payload, "enabled"),
                )
                return self._success(request_id, {"updated": True})
            if method == "tower.registerCompleted":
                raw_participants = payload.get("participantIds", [])
                if not isinstance(raw_participants, list) or not all(
                    isinstance(value, str) for value in raw_participants
                ):
                    raise ValueError("participantIds must be an array of IDs")
                raw_drops = payload.get("drops", [])
                if not isinstance(raw_drops, list):
                    raise ValueError("drops must be an array")
                drops: list[TowerDropInput] = []
                for raw_drop in raw_drops:
                    if not isinstance(raw_drop, dict):
                        raise ValueError("each drop must be an object")
                    estimated_value = raw_drop.get("estimatedUnitValue")
                    if estimated_value is not None and (
                        isinstance(estimated_value, bool)
                        or not isinstance(estimated_value, int)
                        or estimated_value < 0
                    ):
                        raise ValueError("estimatedUnitValue must be a non-negative integer")
                    drops.append(
                        TowerDropInput(
                            self._required_string(raw_drop, "itemName"),
                            self._required_int(raw_drop, "quantity", minimum=1),
                            Gold(estimated_value) if estimated_value is not None else None,
                        )
                    )
                guild_name = payload.get("guildName")
                if guild_name is not None and not isinstance(guild_name, str):
                    raise ValueError("guildName must be a string")
                tower_result = TowerSessionService(
                    cast(TowerUnitOfWork, SqliteUnitOfWork(self._required_database())),
                    UUIDGenerator(),
                    SystemClock(),
                ).register_completed(
                    self._default_workspace_id(),
                    self._activity_date(payload),
                    tuple(EntityId(UUID(value)) for value in raw_participants),
                    guild_name.strip() or None if guild_name is not None else None,
                    tuple(drops),
                )
                return self._success(
                    request_id,
                    {
                        "sessionId": str(tower_result.session.id),
                        "participantCount": len(tower_result.participants),
                        "dropCount": len(tower_result.drops),
                        "entryCostGold": 25_000,
                    },
                )
            if method == "dashboard.layout":
                visibility = DashboardLayoutService(
                    cast(FarmUnitOfWork, SqliteUnitOfWork(self._required_database())),
                    UUIDGenerator(),
                    SystemClock(),
                ).get_visibility(self._default_workspace_id())
                return self._success(request_id, {"visibility": visibility, "schemaVersion": 1})
            if method == "dashboard.setModuleVisible":
                visibility = DashboardLayoutService(
                    cast(FarmUnitOfWork, SqliteUnitOfWork(self._required_database())),
                    UUIDGenerator(),
                    SystemClock(),
                ).set_visibility(
                    self._default_workspace_id(),
                    self._required_string(payload, "moduleKey"),
                    self._required_bool(payload, "enabled"),
                )
                return self._success(request_id, {"visibility": visibility, "schemaVersion": 1})
            if method == "dashboard.resetLayout":
                visibility = DashboardLayoutService(
                    cast(FarmUnitOfWork, SqliteUnitOfWork(self._required_database())),
                    UUIDGenerator(),
                    SystemClock(),
                ).reset(self._default_workspace_id())
                return self._success(request_id, {"visibility": visibility, "schemaVersion": 1})
            if method == "history.overview":
                if self._dashboard_reader is None:
                    return self._error(
                        request_id, "service_unavailable", "Histórico local indisponível"
                    )
                start_date_str = payload.get("startDate")
                end_date_str = payload.get("endDate")
                start_date = (
                    date.fromisoformat(start_date_str)
                    if isinstance(start_date_str, str) and start_date_str.strip()
                    else None
                )
                end_date = (
                    date.fromisoformat(end_date_str)
                    if isinstance(end_date_str, str) and end_date_str.strip()
                    else None
                )
                account_id = (
                    payload.get("accountId")
                    if isinstance(payload.get("accountId"), str) and payload["accountId"].strip()
                    else None
                )
                character_id = (
                    payload.get("characterId")
                    if isinstance(payload.get("characterId"), str)
                    and payload["characterId"].strip()
                    else None
                )
                days = self._dashboard_reader.history_overview_for_default_workspace(
                    start_date=start_date,
                    end_date=end_date,
                    account_id=account_id,
                    character_id=character_id,
                )
                if days is None:
                    return self._success(request_id, {"state": "empty", "days": []})
                return self._success(
                    request_id,
                    {
                        "state": "ready",
                        "days": [
                            {
                                "activityDate": day.activity_date.isoformat(),
                                "runsCompleted": day.runs_completed,
                                "charactersCompleted": day.characters_completed,
                                "charactersTotal": day.characters_total,
                                "goldEarned": day.gold_earned.amount,
                                "pveBagsEarned": day.pve_bags_earned,
                                "towerCompleted": day.tower_completed,
                                "towerTotal": day.tower_total,
                                "dropsCount": day.drops_count,
                                "routineDurationSeconds": day.routine_duration_seconds,
                            }
                            for day in days
                        ],
                    },
                )
            if method == "history.dayDetail":
                if self._dashboard_reader is None:
                    return self._error(
                        request_id, "service_unavailable", "Histórico local indisponível"
                    )
                activity_date = self._activity_date(payload)
                account_id = (
                    payload.get("accountId")
                    if isinstance(payload.get("accountId"), str) and payload["accountId"].strip()
                    else None
                )
                character_id = (
                    payload.get("characterId")
                    if isinstance(payload.get("characterId"), str)
                    and payload["characterId"].strip()
                    else None
                )
                detail = self._dashboard_reader.history_day_detail_for_default_workspace(
                    activity_date,
                    account_id=account_id,
                    character_id=character_id,
                )
                if detail is None:
                    return self._error(request_id, "not_found", "Detalhes do dia não encontrados")
                return self._success(
                    request_id,
                    {
                        "state": "ready",
                        "activityDate": detail.activity_date.isoformat(),
                        "runsCompleted": detail.runs_completed,
                        "goldEarned": detail.gold_earned.amount,
                        "pveBagsEarned": detail.pve_bags_earned,
                        "routineDurationSeconds": detail.routine_duration_seconds,
                        "characters": [
                            {
                                "id": ch.character_id,
                                "name": ch.name,
                                "className": ch.class_name,
                                "accountName": ch.account_name,
                                "completedDungeons": ch.completed_dungeons,
                                "selectedDungeons": ch.selected_dungeons,
                                "dungeons": [
                                    {
                                        "activityId": d.activity_id,
                                        "name": d.name,
                                        "completed": d.completed,
                                        "targetAmount": d.target_amount,
                                        "gold": d.gold.amount,
                                        "pveBags": d.pve_bags,
                                    }
                                    for d in ch.dungeons
                                ],
                            }
                            for ch in detail.characters
                        ],
                        "towerSessions": [
                            {
                                "sessionId": ts.session_id,
                                "completed": ts.completed,
                                "costGold": ts.cost_gold.amount,
                                "participantNames": list(ts.participant_names),
                                "drops": [
                                    {
                                        "itemName": drop.item_name,
                                        "quantity": drop.quantity,
                                        "obtainedAt": drop.obtained_at.isoformat(),
                                    }
                                    for drop in ts.drops
                                ],
                            }
                            for ts in detail.tower_sessions
                        ],
                        "drops": [
                            {
                                "itemName": drop.item_name,
                                "quantity": drop.quantity,
                                "obtainedAt": drop.obtained_at.isoformat(),
                            }
                            for drop in detail.drops
                        ],
                    },
                )
            if method == "market.recordPveBagQuote":
                unit_value_gold = self._required_int(payload, "unitValueGold", minimum=0)
                source = payload.get("source")
                if source is not None and not isinstance(source, str):
                    raise ValueError("source must be a string")
                quote = MarketQuoteService(
                    cast(FarmUnitOfWork, SqliteUnitOfWork(self._required_database())),
                    UUIDGenerator(),
                    SystemClock(),
                ).record_pve_bag_quote(
                    self._default_workspace_id(),
                    Gold(unit_value_gold),
                    source=source.strip() or None if source else None,
                )
                return self._success(
                    request_id,
                    {
                        "quoteId": str(quote.id),
                        "unitValueGold": quote.unit_value_gold.amount,
                        "observedAt": quote.observed_at.isoformat(),
                    },
                )
            if method == "currency.getRate":
                base_curr = self._required_string(payload, "baseCurrency")
                raw_quote = payload.get("quoteCurrency")
                quote_curr: str = (
                    raw_quote if isinstance(raw_quote, str) and raw_quote.strip() else "BRL"
                )
                raw_date = payload.get("date")
                rate_date = (
                    date.fromisoformat(raw_date)
                    if isinstance(raw_date, str) and raw_date.strip()
                    else None
                )
                rate_micros, source = CurrencyRateService(self._required_database()).get_rate(
                    base_curr, quote_curr, rate_date
                )
                rate_val = rate_micros / 1_000_000
                rate_formatted = f"{rate_val:.4f}".rstrip("0").rstrip(".").replace(".", ",")
                return self._success(
                    request_id,
                    {
                        "baseCurrency": base_curr.upper(),
                        "quoteCurrency": quote_curr.upper(),
                        "rateMicros": rate_micros,
                        "rateFormatted": rate_formatted,
                        "source": source,
                        "date": (rate_date or date.today()).isoformat(),
                    },
                )
            if method == "sales.record":
                sale_type = self._required_string(payload, "saleType")
                item_desc = self._required_string(payload, "itemDescription")
                quantity = self._required_int(payload, "quantity", minimum=1)
                orig_amount = self._required_int(payload, "originalAmountMinor", minimum=1)
                currency = self._required_string(payload, "currency")
                exchange_rate = self._required_int(payload, "exchangeRateMicros", minimum=1)
                rate_source = self._required_string(payload, "exchangeRateSource")
                idempotency_key = UUID(self._required_string(payload, "idempotencyKey"))
                sold_at_str = payload.get("soldAt")
                sold_at = (
                    datetime.fromisoformat(sold_at_str)
                    if isinstance(sold_at_str, str) and sold_at_str.strip()
                    else datetime.now(UTC)
                )
                sale_res = SaleService(SqliteSaleLedger(self._required_database())).record_sale(
                    SaleCommand(
                        workspace_id=self._default_workspace_id(),
                        idempotency_key=idempotency_key,
                        sale_type=sale_type,
                        item_description=item_desc,
                        quantity=quantity,
                        original_amount_minor=orig_amount,
                        currency=currency,
                        exchange_rate_micros=exchange_rate,
                        exchange_rate_source=rate_source,
                        sold_at=sold_at,
                    )
                )
                return self._success(
                    request_id,
                    {
                        "saleId": sale_res.sale_id,
                        "realAmountMinor": sale_res.real_amount_minor,
                        "originalAmountMinor": sale_res.original_amount_minor,
                        "currency": sale_res.currency,
                        "exchangeRateMicros": sale_res.exchange_rate_micros,
                        "exchangeRateSource": sale_res.exchange_rate_source,
                        "soldAt": sale_res.sold_at.isoformat(),
                        "alreadyRecorded": sale_res.already_recorded,
                    },
                )
            if method == "dashboard.setDailyMission":
                character_id = str(self._entity_id(payload, "characterId"))
                completed = self._required_bool(payload, "completed")
                activity_date = self._activity_date(payload)
                daily_mission_completed = SqliteDailyOperations(
                    self._required_database()
                ).set_character_daily_mission(
                    str(self._default_workspace_id()), character_id, activity_date, completed
                )
                return self._success(request_id, {"completed": daily_mission_completed})
            if method == "vip.save":
                character_id = str(self._entity_id(payload, "characterId"))
                paid_gold = self._required_int(payload, "paidGold", minimum=1)
                remaining_days = self._required_int(payload, "remainingDays", minimum=0)
                remaining_hours = self._required_int(payload, "remainingHours", minimum=0)
                expires_at = SqliteDailyOperations(self._required_database()).save_character_vip(
                    str(self._default_workspace_id()),
                    character_id,
                    paid_gold,
                    remaining_days,
                    remaining_hours,
                )
                return self._success(
                    request_id, {"expiresAt": expires_at.isoformat(), "paidGold": paid_gold}
                )
            if method == "expenses.record":
                category = self._required_string(payload, "category")
                amount_gold = self._required_int(payload, "amountGold", minimum=1)
                occurred_on = date.fromisoformat(self._required_string(payload, "occurredOn"))
                description = payload.get("description")
                if description is not None and not isinstance(description, str):
                    raise ValueError("description must be a string")
                transaction_id = SqliteDailyOperations(self._required_database()).record_expense(
                    str(self._default_workspace_id()),
                    category,
                    amount_gold,
                    datetime.combine(occurred_on, datetime.min.time(), tzinfo=UTC),
                    description,
                )
                return self._success(request_id, {"transactionId": transaction_id})
            if method == "expenses.history":
                expenses = SqliteDailyOperations(self._required_database()).list_manual_expenses(
                    str(self._default_workspace_id())
                )
                return self._success(
                    request_id,
                    {
                        "expenses": [
                            {
                                "id": expense["id"],
                                "category": expense["category"],
                                "amountGold": expense["amount_gold"],
                                "occurredAt": expense["occurred_at"],
                                "description": expense["description"],
                                "createdAt": expense["created_at"],
                            }
                            for expense in expenses
                        ]
                    },
                )
            if method == "expenses.update":
                transaction_id = str(self._entity_id(payload, "transactionId"))
                category = self._required_string(payload, "category")
                amount_gold = self._required_int(payload, "amountGold", minimum=1)
                occurred_on = date.fromisoformat(self._required_string(payload, "occurredOn"))
                description = payload.get("description")
                if description is not None and not isinstance(description, str):
                    raise ValueError("description must be a string")
                replacement_id = SqliteDailyOperations(
                    self._required_database()
                ).update_manual_expense(
                    str(self._default_workspace_id()),
                    transaction_id,
                    category,
                    amount_gold,
                    datetime.combine(occurred_on, datetime.min.time(), tzinfo=UTC),
                    description,
                )
                return self._success(request_id, {"transactionId": replacement_id})
            if method == "expenses.void":
                transaction_id = str(self._entity_id(payload, "transactionId"))
                SqliteDailyOperations(self._required_database()).void_manual_expense(
                    str(self._default_workspace_id()), transaction_id
                )
                return self._success(request_id, {"voided": True})
            if method == "routine.current":
                routine = SqliteDailyOperations(self._required_database()).get_work_routine(
                    str(self._default_workspace_id())
                )
                return self._success(request_id, {"routine": routine})
            if method == "routine.start":
                routine = SqliteDailyOperations(self._required_database()).start_work_routine(
                    str(self._default_workspace_id())
                )
                return self._success(request_id, routine)
            if method == "routine.pause":
                routine = SqliteDailyOperations(self._required_database()).pause_work_routine(
                    str(self._default_workspace_id())
                )
                return self._success(request_id, routine)
            if method == "routine.resume":
                routine = SqliteDailyOperations(self._required_database()).resume_work_routine(
                    str(self._default_workspace_id())
                )
                return self._success(request_id, routine)
            if method == "routine.stop":
                routine = SqliteDailyOperations(self._required_database()).stop_work_routine(
                    str(self._default_workspace_id())
                )
                return self._success(request_id, routine)
            if method == "reports.setMonthlyTarget":
                target_month = self._required_string(payload, "targetMonth")
                target_gold = self._required_int(payload, "targetGold", minimum=1)
                value = SqliteDailyOperations(self._required_database()).set_monthly_target(
                    str(self._default_workspace_id()), target_month, target_gold
                )
                return self._success(request_id, {"targetMonth": target_month, "targetGold": value})
            if method == "reports.overview":
                if self._dashboard_reader is None:
                    return self._error(
                        request_id, "service_unavailable", "Relatório local indisponível"
                    )
                ref_date: date | None = None
                raw_ref = payload.get("referenceDate")
                if raw_ref is not None:
                    if not isinstance(raw_ref, str):
                        raise ValueError("referenceDate must be an ISO date string")
                    ref_date = date.fromisoformat(raw_ref)

                reports = self._dashboard_reader.reports_overview_for_default_workspace(ref_date)
                if reports is None:
                    return self._success(request_id, {"state": "empty"})

                return self._success(
                    request_id,
                    {
                        "state": "ready",
                        "kpis": {
                            "monthlySalesMinor": reports.kpis.monthly_sales_minor,
                            "salesChangePercent": reports.kpis.sales_change_percent,
                            "previousSalesMinor": reports.kpis.previous_sales_minor,
                            "salesChangeStatus": reports.kpis.sales_change_status,
                            "monthlyFarmGold": reports.kpis.monthly_farm_gold.amount,
                            "farmGoldChangePercent": reports.kpis.farm_gold_change_percent,
                            "previousFarmGold": reports.kpis.previous_farm_gold.amount,
                            "farmGoldChangeStatus": reports.kpis.farm_gold_change_status,
                            "allTimeFarmGold": reports.kpis.all_time_farm_gold.amount,
                            "dailyAverageGold": reports.kpis.daily_average_gold.amount,
                            "monthlyPveBagsEarned": reports.kpis.monthly_pve_bags_earned,
                            "pveBagsEarnedChangePercent": (
                                reports.kpis.pve_bags_earned_change_percent
                            ),
                            "previousPveBagsEarned": reports.kpis.previous_pve_bags_earned,
                            "pveBagsEarnedChangeStatus": reports.kpis.pve_bags_change_status,
                            "isPartialMonth": reports.kpis.is_partial_month,
                            "comparisonPeriodDays": reports.kpis.comparison_period_days,
                        },
                        "dailyEvolution": [
                            {
                                "day": pt.day,
                                "activityDate": pt.activity_date.isoformat(),
                                "gold": pt.gold.amount,
                                "runs": pt.runs,
                            }
                            for pt in reports.daily_evolution
                        ],
                        "monthlyComparison": {
                            "previousMonthName": reports.monthly_comparison.previous_month_name,
                            "previousMonthGold": (
                                reports.monthly_comparison.previous_month_gold.amount
                            ),
                            "currentMonthName": reports.monthly_comparison.current_month_name,
                            "currentMonthGold": (
                                reports.monthly_comparison.current_month_gold.amount
                            ),
                            "growthPercent": reports.monthly_comparison.growth_percent,
                            "growthStatus": reports.monthly_comparison.growth_status,
                            "isPartial": reports.monthly_comparison.is_partial,
                            "previousPeriodLabel": (
                                reports.monthly_comparison.previous_period_label
                            ),
                            "currentPeriodLabel": reports.monthly_comparison.current_period_label,
                        },
                        "cumulativeHistory": [
                            {
                                "monthLabel": cpt.month_label,
                                "monthKey": cpt.month_key,
                                "cumulativeGold": cpt.cumulative_gold.amount,
                            }
                            for cpt in reports.cumulative_history
                        ],
                        "financialSummary": {
                            "salesAmountMinor": reports.financial_summary.sales_amount_minor,
                            "itemsSoldCount": reports.financial_summary.items_sold_count,
                            "goldConvertedTotal": (
                                reports.financial_summary.gold_converted_total.amount
                            ),
                            "averageTicketMinor": reports.financial_summary.average_ticket_minor,
                            "expensesGold": reports.financial_summary.expenses_gold.amount,
                            "vipExpensesGold": reports.financial_summary.vip_expenses_gold.amount,
                            "towerExpensesGold": (
                                reports.financial_summary.tower_expenses_gold.amount
                            ),
                            "manualExpensesGold": (
                                reports.financial_summary.manual_expenses_gold.amount
                            ),
                        },
                        "recentSales": [
                            {
                                "id": sale.id,
                                "itemName": sale.item_name,
                                "quantity": sale.quantity,
                                "amountMinor": sale.amount_minor,
                                "currency": sale.currency,
                                "soldAt": sale.sold_at.isoformat(),
                            }
                            for sale in reports.recent_sales
                        ],
                        "recentMovements": [
                            {
                                "id": movement.id,
                                "kind": movement.kind,
                                "title": movement.title,
                                "detail": movement.detail,
                                "occurredAt": movement.occurred_at.isoformat(),
                                "goldAmount": (
                                    movement.gold_amount.amount
                                    if movement.gold_amount is not None
                                    else None
                                ),
                                "pveBags": movement.pve_bags,
                                "amountMinor": movement.amount_minor,
                            }
                            for movement in reports.recent_movements
                        ],
                        "workRoutineHistory": {
                            "monthSeconds": reports.work_routine_history.month_seconds,
                            "weekSeconds": reports.work_routine_history.week_seconds,
                            "previousWeekSeconds": (
                                reports.work_routine_history.previous_week_seconds
                            ),
                            "monthSessionCount": (reports.work_routine_history.month_session_count),
                            "activeDaysInMonth": (
                                reports.work_routine_history.active_days_in_month
                            ),
                            "recentSessions": [
                                {
                                    "id": session.id,
                                    "startedAt": session.started_at.isoformat(),
                                    "finishedAt": session.finished_at.isoformat(),
                                    "elapsedSeconds": session.elapsed_seconds,
                                }
                                for session in reports.work_routine_history.recent_sessions
                            ],
                        },
                        "monthlyTarget": {
                            "targetMonth": reports.monthly_target.target_month,
                            "targetGold": reports.monthly_target.target_gold.amount,
                            "currentGold": reports.monthly_target.current_gold.amount,
                            "currentPveBags": reports.monthly_target.current_pve_bags,
                            "pveBagUnitValueGold": (
                                reports.monthly_target.pve_bag_unit_value.amount
                                if reports.monthly_target.pve_bag_unit_value
                                else None
                            ),
                            "currentTotalValueGold": (
                                reports.monthly_target.current_total_value_gold.amount
                            ),
                            "percentage": reports.monthly_target.percentage,
                            "remainingGold": reports.monthly_target.remaining_gold.amount,
                            "daysRemaining": reports.monthly_target.days_remaining,
                        },
                        "topCharacters": [
                            {
                                "rank": tc.rank,
                                "characterId": tc.character_id,
                                "characterName": tc.character_name,
                                "className": tc.class_name,
                                "goldEarned": tc.gold_earned.amount,
                            }
                            for tc in reports.top_characters
                        ],
                        "monthlySalesHistory": [
                            {
                                "monthKey": m.month_key,
                                "monthLabel": m.month_label,
                                "salesAmountMinor": m.sales_amount_minor,
                                "salesCount": m.sales_count,
                                "isPartial": m.is_partial,
                            }
                            for m in reports.monthly_sales_history
                        ],
                    },
                )
            if method == "workspace.create":
                if self._database is None or self._dashboard_reader is None:
                    return self._error(
                        request_id, "service_unavailable", "Banco local indisponível"
                    )
                if self._dashboard_reader.has_workspace():
                    return self._error(request_id, "conflict", "O workspace local já foi criado")
                name = self._required_string(payload, "name")
                uow = cast(FarmUnitOfWork, SqliteUnitOfWork(self._database))
                ids = UUIDGenerator()
                clock = SystemClock()
                workspace = WorkspaceService(uow, ids, clock).create_workspace(name)
                DungeonCatalogService(uow, ids, clock).seed_confirmed_dungeons(workspace.id)
                return self._success(request_id, {"name": workspace.name})
            return self._error(request_id, "unknown_method", "Método não reconhecido")
        except ConflictError as exc:
            return self._error(request_id, "conflict", str(exc))
        except NotFoundError as exc:
            return self._error(request_id, "not_found", str(exc))
        except ValidationError as exc:
            return self._error(request_id, "validation_error", str(exc))
        except DomainError as exc:
            return self._error(request_id, "domain_error", str(exc))
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            return self._error(request_id, "invalid_request", str(exc))

    @staticmethod
    def _required_string(payload: dict[str, Any], key: str) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} must be a non-empty string")
        return value

    @staticmethod
    def _activity_date(payload: dict[str, Any]) -> date:
        value = payload.get("activityDate")
        if value is None:
            return date.today()
        if not isinstance(value, str):
            raise ValueError("activityDate must be an ISO date")
        return date.fromisoformat(value)

    @staticmethod
    def _required_int(payload: dict[str, Any], key: str, minimum: int = 0) -> int:
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            raise ValueError(f"{key} must be an integer greater than or equal to {minimum}")
        return value

    @staticmethod
    def _required_bool(payload: dict[str, Any], key: str) -> bool:
        value = payload.get(key)
        if not isinstance(value, bool):
            raise ValueError(f"{key} must be a boolean")
        return value

    @staticmethod
    def _entity_id(payload: dict[str, Any], key: str) -> EntityId:
        value = AppBridge._required_string(payload, key)
        return EntityId(UUID(value))

    def _required_database(self) -> SqliteDatabase:
        if self._database is None:
            raise NotFoundError("Banco local indisponível")
        return self._database

    def _default_workspace_id(self) -> WorkspaceId:
        if self._dashboard_reader is None:
            raise NotFoundError("Workspace local indisponível")
        workspace_id = self._dashboard_reader.default_workspace_id()
        if workspace_id is None:
            raise NotFoundError("Crie o workspace local antes de continuar")
        return workspace_id

    @staticmethod
    def _success(request_id: str, data: dict[str, Any]) -> str:
        return json.dumps(
            {"version": 1, "requestId": request_id, "ok": True, "data": data},
            ensure_ascii=False,
        )

    @staticmethod
    def _error(request_id: str | None, code: str, message: str) -> str:
        return json.dumps(
            {
                "version": 1,
                "requestId": request_id,
                "ok": False,
                "error": {"code": code, "message": message},
            },
            ensure_ascii=False,
        )

    def __init__(
        self,
        database: SqliteDatabase | None = None,
        parent: QObject | None = None,
        autostart_service: WindowsAutostartService | None = None,
    ) -> None:
        super().__init__(parent)
        self._database = database
        self._dashboard_reader = SqliteDashboardReader(database) if database else None
        self._autostart_service = autostart_service
