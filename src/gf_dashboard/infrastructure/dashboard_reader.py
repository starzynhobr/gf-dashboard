from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from gf_dashboard.application.read_models import (
    CharacterDay,
    CharacterDayDungeon,
    ManagementAccount,
    ManagementCharacter,
    ManagementOverview,
    MonthlyGoldPoint,
    RecentDrop,
    RoutineDungeon,
    TodayActivityOverview,
    TodayCharacter,
    TodayEstimate,
)
from gf_dashboard.domain.value_objects import EntityId, Gold, WorkspaceId
from gf_dashboard.infrastructure.persistence import SqliteDatabase


class SqliteDashboardReader:
    def __init__(self, database: SqliteDatabase) -> None:
        self._database = database

    def today_estimate(self, workspace_id: WorkspaceId, activity_date: date) -> TodayEstimate:
        connection = self._database.connect(read_only=True)
        try:
            totals = connection.execute(
                """
                SELECT COUNT(DISTINCT ca.id) AS selected_dungeons,
                       COALESCE(SUM(ca.target_amount * rewards.gold_per_run), 0) AS gold,
                       COALESCE(SUM(ca.target_amount * rewards.bags_per_run), 0) AS bags
                FROM character_activities ca
                JOIN characters c ON c.id = ca.character_id AND c.is_active = 1
                    AND c.deleted_at IS NULL
                JOIN activities a ON a.id = ca.activity_id AND a.category = 'dungeon'
                    AND a.is_active = 1 AND a.deleted_at IS NULL
                JOIN activity_rule_versions rv ON rv.activity_id = a.id
                    AND rv.workspace_id = ca.workspace_id AND rv.rules_status = 'confirmed'
                    AND rv.deleted_at IS NULL AND rv.effective_from <= ?
                    AND (rv.effective_to IS NULL OR rv.effective_to >= ?)
                JOIN (
                    SELECT rule_version_id,
                           SUM(amount_per_completion) AS gold_per_run,
                           SUM(pve_bags_per_completion) AS bags_per_run
                    FROM activity_reward_rules
                    WHERE reward_type = 'gold' AND deleted_at IS NULL
                    GROUP BY rule_version_id
                ) rewards ON rewards.rule_version_id = rv.id
                WHERE ca.workspace_id = ? AND ca.is_active = 1 AND ca.deleted_at IS NULL
                  AND rv.effective_from = (
                    SELECT MAX(latest.effective_from)
                    FROM activity_rule_versions latest
                    WHERE latest.activity_id = a.id AND latest.workspace_id = ca.workspace_id
                      AND latest.rules_status = 'confirmed' AND latest.deleted_at IS NULL
                      AND latest.effective_from <= ?
                      AND (latest.effective_to IS NULL OR latest.effective_to >= ?)
                  )
                """,
                (
                    activity_date.isoformat(),
                    activity_date.isoformat(),
                    str(workspace_id),
                    activity_date.isoformat(),
                    activity_date.isoformat(),
                ),
            ).fetchone()
            quote = connection.execute(
                """
                SELECT mpq.unit_value_gold FROM market_price_quotes mpq
                JOIN items i ON i.id = mpq.item_id AND i.name = 'Saco PvE'
                WHERE mpq.workspace_id = ? AND mpq.deleted_at IS NULL AND i.deleted_at IS NULL
                ORDER BY mpq.observed_at DESC, mpq.rowid DESC LIMIT 1
                """,
                (str(workspace_id),),
            ).fetchone()
            bags = int(totals["bags"])
            bag_value = Gold(int(quote["unit_value_gold"]) * bags) if quote else None
            return TodayEstimate(
                activity_date,
                int(totals["selected_dungeons"]),
                Gold(int(totals["gold"])),
                bags,
                bag_value,
            )
        finally:
            connection.close()

    def today_estimate_for_default_workspace(self, activity_date: date) -> TodayEstimate | None:
        connection = self._database.connect(read_only=True)
        try:
            row = connection.execute(
                "SELECT id FROM workspaces WHERE deleted_at IS NULL ORDER BY created_at LIMIT 1"
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            return None
        return self.today_estimate(WorkspaceId(EntityId(UUID(row["id"]))), activity_date)

    def has_workspace(self) -> bool:
        connection = self._database.connect(read_only=True)
        try:
            return (
                connection.execute(
                    "SELECT 1 FROM workspaces WHERE deleted_at IS NULL LIMIT 1"
                ).fetchone()
                is not None
            )
        finally:
            connection.close()

    def default_workspace_id(self) -> WorkspaceId | None:
        connection = self._database.connect(read_only=True)
        try:
            row = connection.execute(
                "SELECT id FROM workspaces WHERE deleted_at IS NULL ORDER BY created_at LIMIT 1"
            ).fetchone()
            return WorkspaceId(EntityId(UUID(row["id"]))) if row else None
        finally:
            connection.close()

    def management_overview(self) -> ManagementOverview | None:
        connection = self._database.connect(read_only=True)
        try:
            workspace = connection.execute(
                "SELECT id, name FROM workspaces WHERE deleted_at IS NULL "
                "ORDER BY created_at LIMIT 1"
            ).fetchone()
            if workspace is None:
                return None
            account_rows = connection.execute(
                "SELECT id, name, server_name FROM accounts WHERE workspace_id = ? "
                "AND is_active = 1 AND deleted_at IS NULL ORDER BY created_at, name",
                (workspace["id"],),
            ).fetchall()
            character_rows = connection.execute(
                "SELECT id, account_id, name, class_name, level, sort_order FROM characters "
                "WHERE workspace_id = ? AND is_active = 1 AND deleted_at IS NULL "
                "ORDER BY account_id, sort_order, name",
                (workspace["id"],),
            ).fetchall()
            characters_by_account: dict[str, list[ManagementCharacter]] = {}
            for row in character_rows:
                characters_by_account.setdefault(row["account_id"], []).append(
                    ManagementCharacter(
                        row["id"],
                        row["account_id"],
                        row["name"],
                        row["class_name"],
                        int(row["level"]),
                        int(row["sort_order"]),
                    )
                )
            dungeon_rows = connection.execute(
                "SELECT id, name, is_active, default_target_amount FROM activities "
                "WHERE workspace_id = ? AND category = 'dungeon' AND deleted_at IS NULL "
                "ORDER BY name",
                (workspace["id"],),
            ).fetchall()
            return ManagementOverview(
                workspace["name"],
                tuple(
                    ManagementAccount(
                        row["id"],
                        row["name"],
                        row["server_name"],
                        tuple(characters_by_account.get(row["id"], [])),
                    )
                    for row in account_rows
                ),
                tuple(
                    RoutineDungeon(
                        row["id"],
                        row["name"],
                        bool(row["is_active"]),
                        int(row["default_target_amount"]),
                    )
                    for row in dungeon_rows
                ),
            )
        finally:
            connection.close()

    def today_characters_for_default_workspace(
        self, activity_date: date
    ) -> tuple[TodayCharacter, ...] | None:
        connection = self._database.connect(read_only=True)
        try:
            workspace = connection.execute(
                "SELECT id FROM workspaces WHERE deleted_at IS NULL ORDER BY created_at LIMIT 1"
            ).fetchone()
            if workspace is None:
                return None
            rows = connection.execute(
                """
                SELECT c.id, c.name, c.class_name, acc.name AS account_name,
                       COUNT(a.id) AS selected_dungeons,
                       COALESCE(SUM(CASE WHEN dae.status = 'completed' THEN 1 ELSE 0 END), 0)
                           AS completed_dungeons
                FROM characters c
                JOIN accounts acc ON acc.id = c.account_id AND acc.is_active = 1
                    AND acc.deleted_at IS NULL
                LEFT JOIN character_activities ca ON ca.character_id = c.id AND ca.is_active = 1
                    AND ca.deleted_at IS NULL
                LEFT JOIN activities a ON a.id = ca.activity_id AND a.is_active = 1
                    AND a.deleted_at IS NULL AND a.category = 'dungeon'
                LEFT JOIN daily_activity_entries dae ON dae.character_activity_id = ca.id
                    AND dae.activity_date = ? AND dae.deleted_at IS NULL AND a.id IS NOT NULL
                WHERE c.workspace_id = ? AND c.is_active = 1 AND c.deleted_at IS NULL
                GROUP BY c.id ORDER BY c.sort_order, c.name
                """,
                (activity_date.isoformat(), workspace["id"]),
            ).fetchall()
            return tuple(
                TodayCharacter(
                    row["id"],
                    row["name"],
                    row["class_name"],
                    row["account_name"],
                    int(row["completed_dungeons"]),
                    int(row["selected_dungeons"]),
                )
                for row in rows
            )
        finally:
            connection.close()

    def character_day_for_default_workspace(
        self, character_id: EntityId, activity_date: date
    ) -> CharacterDay | None:
        connection = self._database.connect(read_only=True)
        try:
            workspace = connection.execute(
                "SELECT id FROM workspaces WHERE deleted_at IS NULL ORDER BY created_at LIMIT 1"
            ).fetchone()
            if workspace is None:
                return None
            character = connection.execute(
                """
                SELECT c.id, c.name, c.class_name, acc.name AS account_name
                FROM characters c
                JOIN accounts acc ON acc.id = c.account_id AND acc.deleted_at IS NULL
                WHERE c.id = ? AND c.workspace_id = ? AND c.is_active = 1
                    AND c.deleted_at IS NULL
                """,
                (str(character_id), workspace["id"]),
            ).fetchone()
            if character is None:
                return None
            rows = connection.execute(
                """
                SELECT ca.id AS character_activity_id, a.id AS activity_id, a.name,
                       ca.target_amount,
                       CASE WHEN dae.status = 'completed' THEN 1 ELSE 0 END AS completed,
                       ca.target_amount * COALESCE(SUM(arr.amount_per_completion), 0) AS gold,
                       ca.target_amount * COALESCE(SUM(arr.pve_bags_per_completion), 0)
                           AS pve_bags
                FROM character_activities ca
                JOIN activities a ON a.id = ca.activity_id AND a.is_active = 1
                    AND a.deleted_at IS NULL AND a.category = 'dungeon'
                JOIN activity_rule_versions rv ON rv.activity_id = a.id
                    AND rv.workspace_id = ca.workspace_id AND rv.rules_status = 'confirmed'
                    AND rv.deleted_at IS NULL AND rv.effective_from <= ?
                    AND (rv.effective_to IS NULL OR rv.effective_to >= ?)
                JOIN activity_reward_rules arr ON arr.rule_version_id = rv.id
                    AND arr.reward_type = 'gold' AND arr.deleted_at IS NULL
                LEFT JOIN daily_activity_entries dae ON dae.character_activity_id = ca.id
                    AND dae.activity_date = ? AND dae.deleted_at IS NULL
                WHERE ca.workspace_id = ? AND ca.character_id = ? AND ca.is_active = 1
                  AND ca.deleted_at IS NULL
                  AND rv.effective_from = (
                    SELECT MAX(latest.effective_from)
                    FROM activity_rule_versions latest
                    WHERE latest.activity_id = a.id AND latest.workspace_id = ca.workspace_id
                      AND latest.rules_status = 'confirmed' AND latest.deleted_at IS NULL
                      AND latest.effective_from <= ?
                      AND (latest.effective_to IS NULL OR latest.effective_to >= ?)
                  )
                GROUP BY ca.id, a.id, a.name, ca.target_amount, dae.status
                ORDER BY ca.sort_order, a.name
                """,
                (
                    activity_date.isoformat(),
                    activity_date.isoformat(),
                    activity_date.isoformat(),
                    workspace["id"],
                    str(character_id),
                    activity_date.isoformat(),
                    activity_date.isoformat(),
                ),
            ).fetchall()
            return CharacterDay(
                character["id"],
                character["name"],
                character["class_name"],
                character["account_name"],
                activity_date,
                tuple(
                    CharacterDayDungeon(
                        row["character_activity_id"],
                        row["activity_id"],
                        row["name"],
                        bool(row["completed"]),
                        int(row["target_amount"]),
                        Gold(int(row["gold"])),
                        int(row["pve_bags"]),
                    )
                    for row in rows
                ),
            )
        finally:
            connection.close()

    def today_activity_for_default_workspace(
        self, activity_date: date
    ) -> TodayActivityOverview | None:
        connection = self._database.connect(read_only=True)
        try:
            workspace = connection.execute(
                "SELECT id FROM workspaces WHERE deleted_at IS NULL ORDER BY created_at LIMIT 1"
            ).fetchone()
            if workspace is None:
                return None
            workspace_id = workspace["id"]
            runs = connection.execute(
                """
                SELECT COUNT(ac.id) AS total
                FROM activity_completions ac
                JOIN daily_activity_entries dae ON dae.id = ac.daily_activity_entry_id
                    AND dae.deleted_at IS NULL
                WHERE ac.workspace_id = ? AND dae.activity_date = ? AND ac.deleted_at IS NULL
                """,
                (workspace_id, activity_date.isoformat()),
            ).fetchone()
            towers = connection.execute(
                """
                SELECT COUNT(fs.id) AS total,
                       COALESCE(SUM(CASE WHEN td.completed = 1 THEN 1 ELSE 0 END), 0)
                           AS completed
                FROM farm_sessions fs
                JOIN tower_session_details td ON td.farm_session_id = fs.id
                    AND td.deleted_at IS NULL
                WHERE fs.workspace_id = ? AND fs.activity_date = ?
                    AND fs.session_type = 'tower' AND fs.deleted_at IS NULL
                """,
                (workspace_id, activity_date.isoformat()),
            ).fetchone()
            drop_rows = connection.execute(
                """
                SELECT i.name, fsi.quantity, fsi.obtained_at
                FROM farm_session_items fsi
                JOIN farm_sessions fs ON fs.id = fsi.farm_session_id
                    AND fs.deleted_at IS NULL
                JOIN items i ON i.id = fsi.item_id AND i.deleted_at IS NULL
                WHERE fsi.workspace_id = ? AND fs.activity_date = ?
                    AND fsi.deleted_at IS NULL
                ORDER BY fsi.obtained_at DESC, fsi.rowid DESC LIMIT 5
                """,
                (workspace_id, activity_date.isoformat()),
            ).fetchall()
            month_start = activity_date.replace(day=1)
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1)
            month_rows = connection.execute(
                """
                SELECT activity_date, SUM(gold) AS gold
                FROM (
                    SELECT dae.activity_date, ac.gold_reward_snapshot AS gold
                    FROM activity_completions ac
                    JOIN daily_activity_entries dae ON dae.id = ac.daily_activity_entry_id
                        AND dae.deleted_at IS NULL
                    WHERE ac.workspace_id = ? AND ac.deleted_at IS NULL
                        AND dae.activity_date >= ? AND dae.activity_date < ?
                    UNION ALL
                    SELECT fs.activity_date, fs.gold_earned AS gold
                    FROM farm_sessions fs
                    WHERE fs.workspace_id = ? AND fs.status = 'completed'
                        AND fs.deleted_at IS NULL AND fs.activity_date >= ?
                        AND fs.activity_date < ? AND fs.gold_earned > 0
                ) facts
                GROUP BY activity_date ORDER BY activity_date
                """,
                (
                    workspace_id,
                    month_start.isoformat(),
                    month_end.isoformat(),
                    workspace_id,
                    month_start.isoformat(),
                    month_end.isoformat(),
                ),
            ).fetchall()
            monthly_gold = tuple(
                MonthlyGoldPoint(date.fromisoformat(row["activity_date"]), Gold(int(row["gold"])))
                for row in month_rows
            )
            return TodayActivityOverview(
                runs_completed=int(runs["total"]),
                tower_completed=int(towers["completed"]),
                tower_total=int(towers["total"]),
                recent_drops=tuple(
                    RecentDrop(
                        row["name"],
                        int(row["quantity"]),
                        datetime.fromisoformat(row["obtained_at"]),
                    )
                    for row in drop_rows
                ),
                monthly_gold=monthly_gold,
                monthly_gold_total=Gold(sum(point.gold.amount for point in monthly_gold)),
            )
        finally:
            connection.close()
