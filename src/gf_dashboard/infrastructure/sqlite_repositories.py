from __future__ import annotations

import sqlite3
from datetime import UTC, date, datetime
from typing import Literal
from uuid import uuid4

from gf_dashboard.application.ports import (
    AccountRepository,
    ActivityCompletionRepository,
    ActivityRepository,
    ActivityRuleRepository,
    CharacterActivityRepository,
    CharacterRepository,
    DailyActivityEntryRepository,
    DashboardLayoutRepository,
    ItemRepository,
    MarketPriceQuoteRepository,
    TowerSessionRepository,
    WorkspaceRepository,
)
from gf_dashboard.domain.entities import (
    Activity,
    ActivityCompletion,
    ActivityRuleVersion,
    Character,
    CharacterActivity,
    DailyActivityEntry,
    FarmSession,
    FarmSessionItem,
    FarmSessionParticipant,
    GameAccount,
    Item,
    MarketPriceQuote,
    MissionRewardRule,
    TowerSessionDetails,
    Workspace,
)
from gf_dashboard.domain.enums import (
    ActivityCategory,
    ActivityFrequency,
    ActivityStatus,
    MissionLimitType,
    RuleStatus,
    SessionStatus,
    SessionType,
)
from gf_dashboard.domain.value_objects import EntityId, Gold, RewardSnapshot, WorkspaceId
from gf_dashboard.infrastructure.persistence import SqliteDatabase


def _id(value: str) -> EntityId:
    from uuid import UUID

    return EntityId(UUID(value))


def _workspace_id(value: str) -> WorkspaceId:
    return WorkspaceId(_id(value))


def _timestamp(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value is not None else None


def _required_timestamp(value: str) -> datetime:
    parsed = _timestamp(value)
    assert parsed is not None
    return parsed


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


class SqliteWorkspaceRepository(WorkspaceRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def get(self, workspace_id: WorkspaceId) -> Workspace | None:
        row = self._connection.execute(
            "SELECT id, name, mode, created_at FROM workspaces WHERE id = ? AND deleted_at IS NULL",
            (str(workspace_id),),
        ).fetchone()
        return (
            Workspace(
                _workspace_id(row["id"]),
                row["name"],
                _required_timestamp(row["created_at"]),
                row["mode"],
            )
            if row
            else None
        )

    def save(self, workspace: Workspace) -> None:
        now = workspace.created_at.isoformat()
        self._connection.execute(
            "INSERT INTO workspaces (id, name, mode, created_at, updated_at) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET name = excluded.name, mode = excluded.mode, updated_at = excluded.updated_at",
            (str(workspace.id), workspace.name, workspace.mode, now, now),
        )


class SqliteAccountRepository(AccountRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def get(self, account_id: EntityId, workspace_id: WorkspaceId) -> GameAccount | None:
        row = self._connection.execute(
            "SELECT * FROM accounts WHERE id = ? AND workspace_id = ? AND deleted_at IS NULL",
            (str(account_id), str(workspace_id)),
        ).fetchone()
        return _account(row) if row else None

    def save(self, account: GameAccount) -> None:
        self._connection.execute(
            "INSERT INTO accounts (id, workspace_id, name, server_name, notes, is_active, created_at, updated_at, deleted_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET "
            "name=excluded.name, server_name=excluded.server_name, notes=excluded.notes, is_active=excluded.is_active, "
            "updated_at=excluded.updated_at, deleted_at=excluded.deleted_at",
            (
                str(account.id),
                str(account.workspace_id),
                account.name,
                account.server_name,
                account.notes,
                int(account.is_active),
                account.created_at.isoformat(),
                account.created_at.isoformat(),
                _iso(account.deleted_at),
            ),
        )

    def exists_by_name(self, workspace_id: WorkspaceId, name: str) -> bool:
        return (
            self._connection.execute(
                "SELECT 1 FROM accounts WHERE workspace_id = ? AND name = ? COLLATE NOCASE "
                "AND is_active = 1 AND deleted_at IS NULL",
                (str(workspace_id), name.strip()),
            ).fetchone()
            is not None
        )

    def list_active(self, workspace_id: WorkspaceId) -> list[GameAccount]:
        rows = self._connection.execute(
            "SELECT * FROM accounts WHERE workspace_id = ? AND is_active = 1 "
            "AND deleted_at IS NULL ORDER BY created_at, name",
            (str(workspace_id),),
        ).fetchall()
        return [_account(row) for row in rows]


class SqliteCharacterRepository(CharacterRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def get(self, character_id: EntityId, workspace_id: WorkspaceId) -> Character | None:
        row = self._connection.execute(
            "SELECT * FROM characters WHERE id = ? AND workspace_id = ? AND deleted_at IS NULL",
            (str(character_id), str(workspace_id)),
        ).fetchone()
        return _character(row) if row else None

    def save(self, character: Character) -> None:
        self._connection.execute(
            "INSERT INTO characters (id, workspace_id, account_id, name, class_name, level, sort_order, is_active, notes, created_at, updated_at, deleted_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET "
            "name=excluded.name, class_name=excluded.class_name, level=excluded.level, sort_order=excluded.sort_order, "
            "is_active=excluded.is_active, notes=excluded.notes, updated_at=excluded.updated_at, deleted_at=excluded.deleted_at",
            (
                str(character.id),
                str(character.workspace_id),
                str(character.account_id),
                character.name,
                character.class_name,
                character.level,
                character.sort_order,
                int(character.is_active),
                character.notes,
                character.created_at.isoformat(),
                character.created_at.isoformat(),
                _iso(character.deleted_at),
            ),
        )

    def exists_by_account_and_name(
        self, workspace_id: WorkspaceId, account_id: EntityId, name: str
    ) -> bool:
        return (
            self._connection.execute(
                "SELECT 1 FROM characters WHERE workspace_id = ? AND account_id = ? AND name = ? COLLATE NOCASE "
                "AND is_active = 1 AND deleted_at IS NULL",
                (str(workspace_id), str(account_id), name.strip()),
            ).fetchone()
            is not None
        )

    def list_active(
        self, workspace_id: WorkspaceId, account_id: EntityId | None = None
    ) -> list[Character]:
        sql = (
            "SELECT * FROM characters WHERE workspace_id = ? AND is_active = 1 "
            "AND deleted_at IS NULL"
        )
        parameters: tuple[str, ...] = (str(workspace_id),)
        if account_id is not None:
            sql += " AND account_id = ?"
            parameters += (str(account_id),)
        rows = self._connection.execute(
            sql + " ORDER BY account_id, sort_order, name", parameters
        ).fetchall()
        return [_character(row) for row in rows]

    def next_sort_order(self, workspace_id: WorkspaceId, account_id: EntityId) -> int:
        row = self._connection.execute(
            "SELECT COALESCE(MAX(sort_order), 0) + 1 AS next_order FROM characters "
            "WHERE workspace_id = ? AND account_id = ? AND is_active = 1 "
            "AND deleted_at IS NULL",
            (str(workspace_id), str(account_id)),
        ).fetchone()
        return int(row["next_order"])


class SqliteActivityRepository(ActivityRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def get(self, activity_id: EntityId, workspace_id: WorkspaceId) -> Activity | None:
        row = self._connection.execute(
            "SELECT * FROM activities WHERE id = ? AND workspace_id = ? AND deleted_at IS NULL",
            (str(activity_id), str(workspace_id)),
        ).fetchone()
        return _activity(row) if row else None

    def save(self, activity: Activity) -> None:
        now = activity.created_at.isoformat()
        self._connection.execute(
            "INSERT INTO activities (id, workspace_id, name, category, frequency_type, default_target_amount, is_active, is_special, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET name=excluded.name, is_active=excluded.is_active, updated_at=excluded.updated_at",
            (
                str(activity.id),
                str(activity.workspace_id),
                activity.name,
                activity.category.value,
                activity.frequency.value,
                activity.default_target_amount,
                int(activity.is_active),
                int(activity.is_special),
                now,
                now,
            ),
        )

    def exists_by_name(self, workspace_id: WorkspaceId, name: str) -> bool:
        return (
            self._connection.execute(
                "SELECT 1 FROM activities WHERE workspace_id = ? AND name = ? COLLATE NOCASE "
                "AND is_active = 1 AND deleted_at IS NULL",
                (str(workspace_id), name.strip()),
            ).fetchone()
            is not None
        )

    def list_active(self, workspace_id: WorkspaceId) -> list[Activity]:
        rows = self._connection.execute(
            "SELECT * FROM activities WHERE workspace_id = ? AND is_active = 1 "
            "AND deleted_at IS NULL ORDER BY name",
            (str(workspace_id),),
        ).fetchall()
        return [_activity(row) for row in rows]

    def list_all(self, workspace_id: WorkspaceId) -> list[Activity]:
        rows = self._connection.execute(
            "SELECT * FROM activities WHERE workspace_id = ? AND deleted_at IS NULL ORDER BY name",
            (str(workspace_id),),
        ).fetchall()
        return [_activity(row) for row in rows]


class SqliteCharacterActivityRepository(CharacterActivityRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def get(
        self, character_activity_id: EntityId, workspace_id: WorkspaceId
    ) -> CharacterActivity | None:
        row = self._connection.execute(
            "SELECT * FROM character_activities WHERE id = ? AND workspace_id = ? AND deleted_at IS NULL",
            (str(character_activity_id), str(workspace_id)),
        ).fetchone()
        return _character_activity(row) if row else None

    def save(self, character_activity: CharacterActivity) -> None:
        self._connection.execute(
            "INSERT INTO character_activities (id, workspace_id, character_id, activity_id, target_amount, sort_order, is_active, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET target_amount=excluded.target_amount, sort_order=excluded.sort_order, is_active=excluded.is_active, updated_at=excluded.updated_at",
            (
                str(character_activity.id),
                str(character_activity.workspace_id),
                str(character_activity.character_id),
                str(character_activity.activity_id),
                character_activity.target_amount,
                character_activity.sort_order,
                int(character_activity.is_active),
                datetime.now().astimezone().isoformat(),
                datetime.now().astimezone().isoformat(),
            ),
        )

    def list_for_character(
        self, workspace_id: WorkspaceId, character_id: EntityId
    ) -> list[CharacterActivity]:
        rows = self._connection.execute(
            "SELECT * FROM character_activities WHERE workspace_id = ? AND character_id = ? "
            "AND deleted_at IS NULL ORDER BY sort_order",
            (str(workspace_id), str(character_id)),
        ).fetchall()
        return [_character_activity(row) for row in rows]


class SqliteActivityRuleRepository(ActivityRuleRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def find_effective(
        self, workspace_id: WorkspaceId, activity_id: EntityId, activity_date: date
    ) -> ActivityRuleVersion | None:
        row = self._connection.execute(
            "SELECT * FROM activity_rule_versions WHERE workspace_id = ? AND activity_id = ? AND deleted_at IS NULL "
            "AND effective_from <= ? AND (effective_to IS NULL OR effective_to >= ?) ORDER BY effective_from DESC LIMIT 1",
            (
                str(workspace_id),
                str(activity_id),
                activity_date.isoformat(),
                activity_date.isoformat(),
            ),
        ).fetchone()
        return self._with_rewards(row) if row else None

    def save(self, rule: ActivityRuleVersion) -> None:
        now = rule.created_at.isoformat()
        self._connection.execute(
            "INSERT INTO activity_rule_versions (id, workspace_id, activity_id, effective_from, effective_to, max_completions, target_amount, rules_status, notes, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET effective_to=excluded.effective_to, max_completions=excluded.max_completions, target_amount=excluded.target_amount, rules_status=excluded.rules_status, notes=excluded.notes, updated_at=excluded.updated_at",
            (
                str(rule.id),
                str(rule.workspace_id),
                str(rule.activity_id),
                rule.effective_from.isoformat(),
                rule.effective_to.isoformat() if rule.effective_to else None,
                rule.max_completions,
                rule.target_amount,
                rule.status.value,
                rule.notes,
                now,
                now,
            ),
        )
        self._connection.execute(
            "DELETE FROM activity_reward_rules WHERE rule_version_id = ?", (str(rule.id),)
        )
        for reward in rule.rewards:
            self._connection.execute(
                "INSERT INTO activity_reward_rules (id, workspace_id, rule_version_id, mission_key, mission_limit_type, reward_type, amount_per_completion, pve_bags_per_completion, created_at, updated_at) VALUES (lower(hex(randomblob(16))), ?, ?, ?, ?, 'gold', ?, ?, ?, ?)",
                (
                    str(rule.workspace_id),
                    str(rule.id),
                    reward.mission_key,
                    reward.limit_type.value,
                    reward.gold_per_completion.amount,
                    reward.pve_bags_per_completion,
                    now,
                    now,
                ),
            )

    def _with_rewards(self, row: sqlite3.Row) -> ActivityRuleVersion:
        reward_rows = self._connection.execute(
            "SELECT mission_key, mission_limit_type, amount_per_completion, pve_bags_per_completion FROM activity_reward_rules WHERE rule_version_id = ? AND deleted_at IS NULL ORDER BY mission_key",
            (row["id"],),
        ).fetchall()
        return ActivityRuleVersion(
            id=_id(row["id"]),
            workspace_id=_workspace_id(row["workspace_id"]),
            activity_id=_id(row["activity_id"]),
            effective_from=date.fromisoformat(row["effective_from"]),
            effective_to=date.fromisoformat(row["effective_to"]) if row["effective_to"] else None,
            max_completions=row["max_completions"],
            target_amount=row["target_amount"],
            status=RuleStatus(row["rules_status"]),
            rewards=tuple(
                MissionRewardRule(
                    reward["mission_key"],
                    MissionLimitType(reward["mission_limit_type"]),
                    Gold(reward["amount_per_completion"]),
                    reward["pve_bags_per_completion"],
                )
                for reward in reward_rows
            ),
            created_at=_required_timestamp(row["created_at"]),
            notes=row["notes"],
        )


class SqliteDailyActivityEntryRepository(DailyActivityEntryRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def find_by_activity_and_date(
        self, workspace_id: WorkspaceId, character_activity_id: EntityId, activity_date: date
    ) -> DailyActivityEntry | None:
        row = self._connection.execute(
            "SELECT * FROM daily_activity_entries WHERE workspace_id = ? AND character_activity_id = ? AND activity_date = ? AND deleted_at IS NULL",
            (str(workspace_id), str(character_activity_id), activity_date.isoformat()),
        ).fetchone()
        return _entry(row) if row else None

    def save(self, entry: DailyActivityEntry) -> None:
        self._connection.execute(
            "INSERT INTO daily_activity_entries (id, workspace_id, character_activity_id, activity_date, status, progress_amount, started_at, completed_at, skipped_at, notes, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET status=excluded.status, progress_amount=excluded.progress_amount, started_at=excluded.started_at, completed_at=excluded.completed_at, skipped_at=excluded.skipped_at, notes=excluded.notes, updated_at=excluded.updated_at",
            (
                str(entry.id),
                str(entry.workspace_id),
                str(entry.character_activity_id),
                entry.activity_date.isoformat(),
                entry.status.value,
                entry.progress_amount,
                _iso(entry.started_at),
                _iso(entry.completed_at),
                _iso(entry.skipped_at),
                entry.notes,
                entry.created_at.isoformat(),
                datetime.now().astimezone().isoformat(),
            ),
        )


class SqliteActivityCompletionRepository(ActivityCompletionRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def list_for_entry(
        self, workspace_id: WorkspaceId, daily_activity_entry_id: EntityId
    ) -> list[ActivityCompletion]:
        rows = self._connection.execute(
            "SELECT * FROM activity_completions WHERE workspace_id = ? AND daily_activity_entry_id = ? AND deleted_at IS NULL ORDER BY sequence_no",
            (str(workspace_id), str(daily_activity_entry_id)),
        ).fetchall()
        return [_completion(row) for row in rows]

    def save_many(self, completions: list[ActivityCompletion]) -> None:
        self._connection.executemany(
            "INSERT INTO activity_completions (id, workspace_id, daily_activity_entry_id, rule_version_id, sequence_no, completed_at, gold_reward_snapshot, pve_bags_snapshot, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    str(item.id),
                    str(item.workspace_id),
                    str(item.daily_activity_entry_id),
                    str(item.rule_version_id),
                    item.sequence_no,
                    item.completed_at.isoformat(),
                    item.reward_snapshot.gold.amount,
                    item.reward_snapshot.pve_bags,
                    item.completed_at.isoformat(),
                    item.completed_at.isoformat(),
                )
                for item in completions
            ],
        )

    def delete_for_entry(
        self, workspace_id: WorkspaceId, daily_activity_entry_id: EntityId
    ) -> None:
        self._connection.execute(
            "DELETE FROM activity_completions WHERE workspace_id = ? AND daily_activity_entry_id = ?",
            (str(workspace_id), str(daily_activity_entry_id)),
        )


class SqliteTowerSessionRepository(TowerSessionRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def save(
        self,
        session: FarmSession,
        details: TowerSessionDetails,
        participants: tuple[FarmSessionParticipant, ...],
    ) -> None:
        now = session.created_at.isoformat()
        self._connection.execute(
            "INSERT INTO farm_sessions (id, workspace_id, session_type, activity_date, status, started_at, finished_at, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET status=excluded.status, finished_at=excluded.finished_at, notes=excluded.notes, updated_at=excluded.updated_at",
            (
                str(session.id),
                str(session.workspace_id),
                session.session_type.value,
                session.activity_date.isoformat(),
                session.status.value,
                _iso(session.started_at),
                _iso(session.finished_at),
                session.notes,
                now,
                now,
            ),
        )
        self._connection.execute(
            "INSERT INTO tower_session_details (farm_session_id, workspace_id, guild_name_snapshot, opened_at, entry_cost_gold_snapshot, completed, completed_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(farm_session_id) DO UPDATE SET completed=excluded.completed, completed_at=excluded.completed_at, updated_at=excluded.updated_at",
            (
                str(session.id),
                str(session.workspace_id),
                details.guild_name_snapshot,
                details.opened_at.isoformat(),
                details.entry_cost.amount,
                int(details.completed),
                _iso(details.completed_at),
                now,
                now,
            ),
        )
        for participant in participants:
            self._connection.execute(
                "INSERT OR IGNORE INTO farm_session_participants (id, workspace_id, farm_session_id, character_id, role, joined_at, left_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    str(uuid4()),
                    str(session.workspace_id),
                    str(session.id),
                    str(participant.character_id),
                    participant.role,
                    _iso(participant.joined_at),
                    _iso(participant.left_at),
                    now,
                    now,
                ),
            )

    def get(
        self, workspace_id: WorkspaceId, session_id: EntityId
    ) -> tuple[FarmSession, TowerSessionDetails, tuple[FarmSessionParticipant, ...]] | None:
        row = self._connection.execute(
            "SELECT fs.*, td.guild_name_snapshot, td.opened_at, td.entry_cost_gold_snapshot, td.completed AS tower_completed, td.completed_at AS tower_completed_at FROM farm_sessions fs JOIN tower_session_details td ON td.farm_session_id = fs.id WHERE fs.id = ? AND fs.workspace_id = ? AND fs.deleted_at IS NULL",
            (str(session_id), str(workspace_id)),
        ).fetchone()
        if row is None:
            return None
        session = FarmSession(
            _id(row["id"]),
            _workspace_id(row["workspace_id"]),
            SessionType(row["session_type"]),
            date.fromisoformat(row["activity_date"]),
            SessionStatus(row["status"]),
            _required_timestamp(row["created_at"]),
            _id(row["primary_character_id"]) if row["primary_character_id"] else None,
            _id(row["activity_id"]) if row["activity_id"] else None,
            _timestamp(row["started_at"]),
            _timestamp(row["finished_at"]),
            row["notes"],
        )
        details = TowerSessionDetails(
            session.id,
            Gold(row["entry_cost_gold_snapshot"]),
            bool(row["tower_completed"]),
            _required_timestamp(row["opened_at"]),
            _timestamp(row["tower_completed_at"]),
            row["guild_name_snapshot"],
        )
        participants = tuple(
            FarmSessionParticipant(
                session.id,
                _id(item["character_id"]),
                item["role"],
                _timestamp(item["joined_at"]),
                _timestamp(item["left_at"]),
            )
            for item in self._connection.execute(
                "SELECT * FROM farm_session_participants WHERE workspace_id = ? AND farm_session_id = ? AND deleted_at IS NULL",
                (str(workspace_id), str(session_id)),
            ).fetchall()
        )
        return session, details, participants

    def add_drop(self, drop: FarmSessionItem) -> None:
        self._connection.execute(
            "INSERT INTO farm_session_items (id, workspace_id, farm_session_id, item_id, quantity, estimated_unit_value_at_drop, obtained_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(drop.id),
                str(drop.workspace_id),
                str(drop.farm_session_id),
                str(drop.item_id),
                drop.quantity,
                drop.estimated_unit_value.amount if drop.estimated_unit_value else None,
                drop.obtained_at.isoformat(),
                drop.obtained_at.isoformat(),
                drop.obtained_at.isoformat(),
            ),
        )


class SqliteItemRepository(ItemRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def get(self, item_id: EntityId, workspace_id: WorkspaceId) -> Item | None:
        row = self._connection.execute(
            "SELECT * FROM items WHERE id = ? AND workspace_id = ? AND deleted_at IS NULL",
            (str(item_id), str(workspace_id)),
        ).fetchone()
        return _item(row) if row else None

    def get_by_name(self, workspace_id: WorkspaceId, name: str) -> Item | None:
        row = self._connection.execute(
            "SELECT * FROM items WHERE workspace_id = ? AND name = ? COLLATE NOCASE "
            "AND deleted_at IS NULL ORDER BY created_at LIMIT 1",
            (str(workspace_id), name.strip()),
        ).fetchone()
        return _item(row) if row else None

    def save(self, item: Item) -> None:
        now = item.created_at.isoformat()
        self._connection.execute(
            "INSERT INTO items (id, workspace_id, name, category, rarity, is_active, created_at, "
            "updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET "
            "name=excluded.name, category=excluded.category, rarity=excluded.rarity, "
            "is_active=excluded.is_active, updated_at=excluded.updated_at",
            (
                str(item.id),
                str(item.workspace_id),
                item.name,
                item.category,
                item.rarity,
                int(item.is_active),
                now,
                now,
            ),
        )


class SqliteMarketPriceQuoteRepository(MarketPriceQuoteRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def save(self, quote: MarketPriceQuote) -> None:
        now = quote.observed_at.isoformat()
        self._connection.execute(
            "INSERT INTO market_price_quotes (id, workspace_id, item_id, unit_value_gold, observed_at, "
            "source, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(quote.id),
                str(quote.workspace_id),
                str(quote.item_id),
                quote.unit_value_gold.amount,
                quote.observed_at.isoformat(),
                quote.source,
                now,
                now,
            ),
        )

    def latest_for_item(
        self, workspace_id: WorkspaceId, item_id: EntityId
    ) -> MarketPriceQuote | None:
        row = self._connection.execute(
            "SELECT * FROM market_price_quotes WHERE workspace_id = ? AND item_id = ? "
            "AND deleted_at IS NULL ORDER BY observed_at DESC, rowid DESC LIMIT 1",
            (str(workspace_id), str(item_id)),
        ).fetchone()
        return _market_price_quote(row) if row else None


class SqliteDashboardLayoutRepository(DashboardLayoutRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def get_enabled(self, workspace_id: WorkspaceId) -> dict[str, bool]:
        rows = self._connection.execute(
            "SELECT dli.module_key, dli.enabled FROM dashboard_layouts dl "
            "JOIN dashboard_layout_items dli ON dli.layout_id = dl.id "
            "WHERE dl.workspace_id = ? AND dl.is_default = 1 AND dl.deleted_at IS NULL "
            "AND dli.deleted_at IS NULL ORDER BY dli.sort_order",
            (str(workspace_id),),
        ).fetchall()
        return {row["module_key"]: bool(row["enabled"]) for row in rows}

    def save_enabled(
        self,
        workspace_id: WorkspaceId,
        module_key: str,
        enabled: bool,
        layout_id: EntityId,
        item_id: EntityId,
        changed_at: datetime,
    ) -> None:
        row = self._connection.execute(
            "SELECT id FROM dashboard_layouts WHERE workspace_id = ? AND is_default = 1 "
            "AND deleted_at IS NULL ORDER BY created_at LIMIT 1",
            (str(workspace_id),),
        ).fetchone()
        timestamp = changed_at.isoformat()
        active_layout_id = str(_id(row["id"])) if row else str(layout_id)
        if row is None:
            self._connection.execute(
                "INSERT INTO dashboard_layouts (id, workspace_id, name, is_default, "
                "layout_version, created_at, updated_at) VALUES (?, ?, 'Padrão', 1, 1, ?, ?)",
                (active_layout_id, str(workspace_id), timestamp, timestamp),
            )
        self._connection.execute(
            "INSERT INTO dashboard_layout_items (id, workspace_id, layout_id, module_key, "
            "enabled, sort_order, region, column_span, row_span, settings_json, created_at, "
            "updated_at) VALUES (?, ?, ?, ?, ?, 0, 'right', 1, 1, '{\"schemaVersion\":1}', ?, ?) "
            "ON CONFLICT(layout_id, module_key) DO UPDATE SET enabled=excluded.enabled, "
            "updated_at=excluded.updated_at, deleted_at=NULL",
            (
                str(item_id),
                str(workspace_id),
                active_layout_id,
                module_key,
                int(enabled),
                timestamp,
                timestamp,
            ),
        )

    def reset(self, workspace_id: WorkspaceId) -> None:
        now = datetime.now(UTC).isoformat()
        self._connection.execute(
            "UPDATE dashboard_layout_items SET deleted_at = ?, updated_at = ? WHERE workspace_id = ? "
            "AND deleted_at IS NULL",
            (now, now, str(workspace_id)),
        )
        self._connection.execute(
            "UPDATE dashboard_layouts SET deleted_at = ?, updated_at = ? WHERE workspace_id = ? "
            "AND deleted_at IS NULL",
            (now, now, str(workspace_id)),
        )


class SqliteUnitOfWork:
    def __init__(self, database: SqliteDatabase) -> None:
        self._database = database
        self._connection: sqlite3.Connection | None = None

    def __enter__(self) -> SqliteUnitOfWork:
        self._connection = self._database.connect()
        self._connection.execute("BEGIN IMMEDIATE")
        self.workspaces = SqliteWorkspaceRepository(self._connection)
        self.accounts = SqliteAccountRepository(self._connection)
        self.characters = SqliteCharacterRepository(self._connection)
        self.activities = SqliteActivityRepository(self._connection)
        self.character_activities = SqliteCharacterActivityRepository(self._connection)
        self.rules = SqliteActivityRuleRepository(self._connection)
        self.daily_entries = SqliteDailyActivityEntryRepository(self._connection)
        self.completions = SqliteActivityCompletionRepository(self._connection)
        self.tower_sessions = SqliteTowerSessionRepository(self._connection)
        self.items = SqliteItemRepository(self._connection)
        self.market_quotes = SqliteMarketPriceQuoteRepository(self._connection)
        self.dashboard_layouts = SqliteDashboardLayoutRepository(self._connection)
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> Literal[False]:
        assert self._connection is not None
        if exc_type is None:
            self._connection.commit()
        else:
            self._connection.rollback()
        self._connection.close()
        self._connection = None
        return False


def _account(row: sqlite3.Row) -> GameAccount:
    return GameAccount(
        _id(row["id"]),
        _workspace_id(row["workspace_id"]),
        row["name"],
        row["server_name"],
        _required_timestamp(row["created_at"]),
        row["notes"],
        bool(row["is_active"]),
        _timestamp(row["deleted_at"]),
    )


def _character(row: sqlite3.Row) -> Character:
    return Character(
        _id(row["id"]),
        _workspace_id(row["workspace_id"]),
        _id(row["account_id"]),
        row["name"],
        row["class_name"],
        row["level"],
        row["sort_order"],
        _required_timestamp(row["created_at"]),
        row["notes"],
        bool(row["is_active"]),
        _timestamp(row["deleted_at"]),
    )


def _activity(row: sqlite3.Row) -> Activity:
    return Activity(
        _id(row["id"]),
        _workspace_id(row["workspace_id"]),
        row["name"],
        ActivityCategory(row["category"]),
        ActivityFrequency(row["frequency_type"]),
        row["default_target_amount"],
        _required_timestamp(row["created_at"]),
        bool(row["is_active"]),
        bool(row["is_special"]),
    )


def _character_activity(row: sqlite3.Row) -> CharacterActivity:
    return CharacterActivity(
        _id(row["id"]),
        _workspace_id(row["workspace_id"]),
        _id(row["character_id"]),
        _id(row["activity_id"]),
        row["target_amount"],
        row["sort_order"],
        bool(row["is_active"]),
    )


def _item(row: sqlite3.Row) -> Item:
    return Item(
        _id(row["id"]),
        _workspace_id(row["workspace_id"]),
        row["name"],
        row["category"],
        _required_timestamp(row["created_at"]),
        row["rarity"],
        bool(row["is_active"]),
    )


def _market_price_quote(row: sqlite3.Row) -> MarketPriceQuote:
    return MarketPriceQuote(
        _id(row["id"]),
        _workspace_id(row["workspace_id"]),
        _id(row["item_id"]),
        Gold(row["unit_value_gold"]),
        _required_timestamp(row["observed_at"]),
        row["source"],
    )


def _entry(row: sqlite3.Row) -> DailyActivityEntry:
    return DailyActivityEntry(
        _id(row["id"]),
        _workspace_id(row["workspace_id"]),
        _id(row["character_activity_id"]),
        date.fromisoformat(row["activity_date"]),
        ActivityStatus(row["status"]),
        row["progress_amount"],
        _required_timestamp(row["created_at"]),
        _timestamp(row["started_at"]),
        _timestamp(row["completed_at"]),
        _timestamp(row["skipped_at"]),
        row["notes"],
    )


def _completion(row: sqlite3.Row) -> ActivityCompletion:
    return ActivityCompletion(
        _id(row["id"]),
        _workspace_id(row["workspace_id"]),
        _id(row["daily_activity_entry_id"]),
        _id(row["rule_version_id"]),
        row["sequence_no"],
        _required_timestamp(row["completed_at"]),
        RewardSnapshot(Gold(row["gold_reward_snapshot"]), row["pve_bags_snapshot"]),
    )
