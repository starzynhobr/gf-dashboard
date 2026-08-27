from __future__ import annotations

import json
from datetime import date
from typing import Any, cast
from uuid import UUID

from PySide6.QtCore import QObject, Slot

from gf_dashboard.application.catalog import DungeonCatalogService
from gf_dashboard.application.ports import FarmUnitOfWork, TowerUnitOfWork
from gf_dashboard.application.services import (
    ActivityCompletionService,
    DashboardLayoutService,
    ManagementService,
    WorkspaceService,
)
from gf_dashboard.application.tower import TowerDropInput, TowerSessionService
from gf_dashboard.domain.errors import ConflictError, DomainError, NotFoundError, ValidationError
from gf_dashboard.domain.value_objects import EntityId, Gold, WorkspaceId
from gf_dashboard.infrastructure.dashboard_reader import SqliteDashboardReader
from gf_dashboard.infrastructure.in_memory import SystemClock, UUIDGenerator
from gf_dashboard.infrastructure.persistence import SqliteDatabase
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
                            }
                            for point in overview.monthly_gold
                        ],
                        "monthlyGoldTotal": overview.monthly_gold_total.amount,
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
        self, database: SqliteDatabase | None = None, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._database = database
        self._dashboard_reader = SqliteDashboardReader(database) if database else None
