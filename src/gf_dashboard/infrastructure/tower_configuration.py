from __future__ import annotations

import json
import sqlite3
from typing import Any
from uuid import UUID

from gf_dashboard.application.ports import Clock, IdGenerator
from gf_dashboard.application.tower_configuration import SaveTowerConfiguration
from gf_dashboard.domain.errors import ConflictError, NotFoundError
from gf_dashboard.domain.tower_configuration import TowerConfiguration, TowerRelevantItem
from gf_dashboard.domain.value_objects import EntityId, Gold, WorkspaceId
from gf_dashboard.infrastructure.in_memory import SystemClock, UUIDGenerator
from gf_dashboard.infrastructure.persistence import SqliteDatabase


def configuration_to_dto(configuration: TowerConfiguration) -> dict[str, Any]:
    return {
        "guildName": configuration.guild_name,
        "entryCostGold": configuration.entry_cost.amount,
        "participantIds": [str(value) for value in configuration.participant_ids],
        "items": [
            {
                "itemId": str(item.item_id),
                "itemName": item.item_name,
                "estimatedUnitValue": (
                    item.estimated_unit_value.amount
                    if item.estimated_unit_value is not None
                    else None
                ),
            }
            for item in configuration.items
        ],
    }


def _configuration_from_dto(value: dict[str, Any]) -> TowerConfiguration:
    return TowerConfiguration(
        value["guildName"],
        Gold(value["entryCostGold"]),
        tuple(EntityId(UUID(raw)) for raw in value["participantIds"]),
        tuple(
            TowerRelevantItem(
                EntityId(UUID(item["itemId"])),
                item["itemName"],
                Gold(item["estimatedUnitValue"])
                if item["estimatedUnitValue"] is not None
                else None,
            )
            for item in value["items"]
        ),
    )


class SqliteTowerConfigurationStore:
    """Keeps reusable Tower settings separate from completed farming facts."""

    def __init__(
        self,
        database: SqliteDatabase,
        ids: IdGenerator | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._database = database
        self._ids = ids or UUIDGenerator()
        self._clock = clock or SystemClock()

    def get(self, workspace_id: WorkspaceId) -> TowerConfiguration:
        connection = self._database.connect(read_only=True)
        try:
            return self._get(connection, workspace_id)
        finally:
            connection.close()

    def _get(self, connection: sqlite3.Connection, workspace_id: WorkspaceId) -> TowerConfiguration:
        workspace = str(workspace_id)
        configuration = connection.execute(
            "SELECT * FROM tower_configurations WHERE workspace_id = ?", (workspace,)
        ).fetchone()
        if configuration is None:
            return self._legacy_configuration(connection, workspace_id)
        participants = connection.execute(
            "SELECT tcp.character_id FROM tower_configuration_participants tcp "
            "JOIN characters c ON c.id = tcp.character_id AND c.workspace_id = tcp.workspace_id "
            "WHERE tcp.workspace_id = ? AND tcp.configuration_id = ? "
            "AND c.deleted_at IS NULL AND c.is_active = 1 ORDER BY tcp.sort_order",
            (workspace, configuration["id"]),
        ).fetchall()
        items = connection.execute(
            "SELECT i.id, i.name, tci.estimated_unit_value_gold AS unit_value "
            "FROM tower_configuration_items tci JOIN items i "
            "ON i.id = tci.item_id AND i.workspace_id = tci.workspace_id "
            "WHERE tci.workspace_id = ? AND tci.configuration_id = ? ORDER BY tci.sort_order",
            (workspace, configuration["id"]),
        ).fetchall()
        return TowerConfiguration(
            configuration["guild_name"],
            Gold(configuration["entry_cost_gold"]),
            tuple(EntityId(UUID(row["character_id"])) for row in participants),
            tuple(self._relevant_item(row) for row in items),
        )

    def _legacy_configuration(
        self, connection: sqlite3.Connection, workspace_id: WorkspaceId
    ) -> TowerConfiguration:
        workspace = str(workspace_id)
        latest = connection.execute(
            "SELECT td.* FROM tower_session_details td JOIN farm_sessions fs "
            "ON fs.id = td.farm_session_id AND fs.workspace_id = td.workspace_id "
            "WHERE td.workspace_id = ? AND td.deleted_at IS NULL AND fs.deleted_at IS NULL "
            "ORDER BY td.opened_at DESC, td.rowid DESC LIMIT 1",
            (workspace,),
        ).fetchone()
        participants = (
            connection.execute(
                "SELECT p.character_id FROM farm_session_participants p JOIN characters c "
                "ON c.id = p.character_id AND c.workspace_id = p.workspace_id "
                "WHERE p.workspace_id = ? AND p.farm_session_id = ? AND p.deleted_at IS NULL "
                "AND c.deleted_at IS NULL AND c.is_active = 1 ORDER BY p.rowid",
                (workspace, latest["farm_session_id"]),
            ).fetchall()
            if latest is not None
            else []
        )
        items = connection.execute(
            """SELECT i.id, i.name, COALESCE(
                (SELECT q.unit_value_gold FROM market_price_quotes q
                 WHERE q.workspace_id = i.workspace_id AND q.item_id = i.id
                   AND q.deleted_at IS NULL ORDER BY q.observed_at DESC, q.rowid DESC LIMIT 1),
                (SELECT fsi.estimated_unit_value_at_drop FROM farm_session_items fsi
                 JOIN farm_sessions fs ON fs.id = fsi.farm_session_id
                   AND fs.workspace_id = fsi.workspace_id
                 WHERE fsi.workspace_id = i.workspace_id AND fsi.item_id = i.id
                   AND fs.session_type = 'tower' AND fs.deleted_at IS NULL
                   AND fsi.deleted_at IS NULL AND fsi.estimated_unit_value_at_drop IS NOT NULL
                 ORDER BY fsi.obtained_at DESC, fsi.rowid DESC LIMIT 1)
                ) AS unit_value
            FROM items i WHERE i.workspace_id = ? AND i.deleted_at IS NULL
              AND (i.category = 'tower_drop' OR EXISTS (
                SELECT 1 FROM farm_session_items fsi JOIN farm_sessions fs
                  ON fs.id = fsi.farm_session_id AND fs.workspace_id = fsi.workspace_id
                WHERE fsi.workspace_id = i.workspace_id AND fsi.item_id = i.id
                  AND fs.session_type = 'tower' AND fs.deleted_at IS NULL
                  AND fsi.deleted_at IS NULL
              )) ORDER BY i.created_at, i.rowid""",
            (workspace,),
        ).fetchall()
        seen: set[str] = set()
        relevant: list[TowerRelevantItem] = []
        for row in items:
            key = str(row["name"]).casefold()
            if key not in seen:
                relevant.append(self._relevant_item(row))
                seen.add(key)
        return TowerConfiguration(
            (latest["guild_name_snapshot"] or "") if latest is not None else "",
            Gold(latest["entry_cost_gold_snapshot"] if latest is not None else 25_000),
            tuple(EntityId(UUID(row["character_id"])) for row in participants),
            tuple(relevant),
        )

    @staticmethod
    def _relevant_item(row: sqlite3.Row) -> TowerRelevantItem:
        return TowerRelevantItem(
            EntityId(UUID(row["id"])),
            row["name"],
            Gold(row["unit_value"]) if row["unit_value"] is not None else None,
        )

    def save(self, command: SaveTowerConfiguration, fingerprint: str) -> TowerConfiguration:
        connection = self._database.connect()
        workspace = str(command.workspace_id)
        now = self._clock.now().isoformat()
        try:
            connection.execute("BEGIN IMMEDIATE")
            replay = connection.execute(
                "SELECT payload_hash, response_json FROM tower_configuration_requests "
                "WHERE workspace_id = ? AND idempotency_key = ?",
                (workspace, str(command.idempotency_key)),
            ).fetchone()
            if replay is not None:
                if replay["payload_hash"] != fingerprint:
                    raise ConflictError("Chave de idempotência já usada com outra configuração")
                connection.rollback()
                return _configuration_from_dto(json.loads(replay["response_json"]))
            if (
                connection.execute(
                    "SELECT 1 FROM workspaces WHERE id = ? AND deleted_at IS NULL", (workspace,)
                ).fetchone()
                is None
            ):
                raise NotFoundError("Workspace não encontrado")
            for participant_id in command.participant_ids:
                if (
                    connection.execute(
                        "SELECT 1 FROM characters WHERE id = ? AND workspace_id = ? "
                        "AND deleted_at IS NULL AND is_active = 1",
                        (str(participant_id), workspace),
                    ).fetchone()
                    is None
                ):
                    raise NotFoundError("Personagem da Torre não encontrado no workspace")
            connection.execute(
                "INSERT INTO tower_configurations "
                "(id, workspace_id, guild_name, entry_cost_gold, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(workspace_id) DO UPDATE SET "
                "guild_name = excluded.guild_name, entry_cost_gold = excluded.entry_cost_gold, "
                "updated_at = excluded.updated_at",
                (
                    str(self._ids.new()),
                    workspace,
                    command.guild_name,
                    command.entry_cost_gold,
                    now,
                    now,
                ),
            )
            configuration_id = connection.execute(
                "SELECT id FROM tower_configurations WHERE workspace_id = ?", (workspace,)
            ).fetchone()["id"]
            connection.execute(
                "DELETE FROM tower_configuration_participants WHERE workspace_id = ?",
                (workspace,),
            )
            connection.execute(
                "DELETE FROM tower_configuration_items WHERE workspace_id = ?", (workspace,)
            )
            for index, participant_id in enumerate(command.participant_ids):
                connection.execute(
                    "INSERT INTO tower_configuration_participants "
                    "(id, workspace_id, configuration_id, character_id, sort_order) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (str(self._ids.new()), workspace, configuration_id, str(participant_id), index),
                )
            existing_items = connection.execute(
                "SELECT id, name FROM items WHERE workspace_id = ? AND deleted_at IS NULL",
                (workspace,),
            ).fetchall()
            by_name = {str(item["name"]).casefold(): item["id"] for item in existing_items}
            for index, item in enumerate(command.items):
                item_id = by_name.get(item.item_name.casefold())
                if item_id is None:
                    item_id = str(self._ids.new())
                    connection.execute(
                        "INSERT INTO items "
                        "(id, workspace_id, name, category, created_at, updated_at) "
                        "VALUES (?, ?, ?, 'tower_drop', ?, ?)",
                        (item_id, workspace, item.item_name, now, now),
                    )
                value = item.estimated_unit_value
                connection.execute(
                    "INSERT INTO tower_configuration_items (id, workspace_id, configuration_id, "
                    "item_id, estimated_unit_value_gold, sort_order) VALUES (?, ?, ?, ?, ?, ?)",
                    (str(self._ids.new()), workspace, configuration_id, item_id, value, index),
                )
                quote = connection.execute(
                    "SELECT unit_value_gold FROM market_price_quotes WHERE workspace_id = ? "
                    "AND item_id = ? AND deleted_at IS NULL "
                    "ORDER BY observed_at DESC, rowid DESC LIMIT 1",
                    (workspace, item_id),
                ).fetchone()
                if value is not None and (quote is None or quote["unit_value_gold"] != value):
                    connection.execute(
                        "INSERT INTO market_price_quotes (id, workspace_id, item_id, "
                        "unit_value_gold, observed_at, source, created_at, updated_at) "
                        "VALUES (?, ?, ?, ?, ?, 'Configuração da Torre', ?, ?)",
                        (str(self._ids.new()), workspace, item_id, value, now, now, now),
                    )
            result = self._get(connection, command.workspace_id)
            connection.execute(
                "INSERT INTO tower_configuration_requests (id, workspace_id, idempotency_key, "
                "payload_hash, response_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    str(self._ids.new()),
                    workspace,
                    str(command.idempotency_key),
                    fingerprint,
                    json.dumps(configuration_to_dto(result), ensure_ascii=False),
                    now,
                ),
            )
            connection.commit()
            return result
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
