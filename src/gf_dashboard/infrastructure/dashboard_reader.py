from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from gf_dashboard.application.read_models import (
    CharacterDay,
    CharacterDayDungeon,
    CumulativeMonthPoint,
    DailyEvolutionPoint,
    FinancialSummary,
    HistoryCharacterDetail,
    HistoryDayDetail,
    HistoryDaySummary,
    HistoryDungeonEntry,
    HistoryTowerSession,
    ManagementAccount,
    ManagementCharacter,
    ManagementOverview,
    MonthlyComparison,
    MonthlyGoldPoint,
    MonthlyTarget,
    RecentDrop,
    RecentSaleRow,
    ReportKpis,
    ReportsOverview,
    RoutineDungeon,
    TodayActivityOverview,
    TodayCharacter,
    TodayEstimate,
    TopCharacterRow,
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
            unit_val = Gold(int(quote["unit_value_gold"])) if quote else None
            bag_value = Gold(int(quote["unit_value_gold"]) * bags) if quote else None
            return TodayEstimate(
                activity_date,
                int(totals["selected_dungeons"]),
                Gold(int(totals["gold"])),
                bags,
                bag_value,
                unit_val,
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

            # Today's earned gold & sales
            act_date_str = activity_date.isoformat()
            today_gold_row = connection.execute(
                """
                SELECT COALESCE(SUM(gold), 0) AS gold
                FROM (
                    SELECT ac.gold_reward_snapshot AS gold
                    FROM activity_completions ac
                    JOIN daily_activity_entries dae
                      ON dae.id = ac.daily_activity_entry_id AND dae.deleted_at IS NULL
                    WHERE ac.workspace_id = ? AND ac.deleted_at IS NULL
                      AND dae.activity_date = ?
                    UNION ALL
                    SELECT fs.gold_earned AS gold
                    FROM farm_sessions fs
                    WHERE fs.workspace_id = ? AND fs.status = 'completed'
                      AND fs.deleted_at IS NULL AND fs.activity_date = ?
                )
                """,
                (workspace_id, act_date_str, workspace_id, act_date_str),
            ).fetchone()
            earned_gold_today = int(today_gold_row["gold"]) if today_gold_row else 0

            today_sales_row = connection.execute(
                """
                SELECT COALESCE(SUM(real_amount_minor), 0) AS sales_minor
                FROM sales
                WHERE workspace_id = ? AND status = 'completed' AND deleted_at IS NULL
                  AND (sold_at LIKE ? || '%' OR SUBSTR(sold_at, 1, 10) = ?)
                """,
                (workspace_id, act_date_str, act_date_str),
            ).fetchone()
            today_sales_minor = int(today_sales_row["sales_minor"]) if today_sales_row else 0

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
                earned_gold_today=Gold(earned_gold_today),
                today_sales_minor=today_sales_minor,
            )
        finally:
            connection.close()

    def history_overview_for_default_workspace(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        account_id: str | None = None,
        character_id: str | None = None,
    ) -> tuple[HistoryDaySummary, ...] | None:
        connection = self._database.connect(read_only=True)
        try:
            workspace = connection.execute(
                "SELECT id FROM workspaces WHERE deleted_at IS NULL ORDER BY created_at LIMIT 1"
            ).fetchone()
            if workspace is None:
                return None
            workspace_id = workspace["id"]

            date_filter_clauses = []
            params: list[str] = [workspace_id]
            if start_date:
                date_filter_clauses.append("activity_date >= ?")
                params.append(start_date.isoformat())
            if end_date:
                date_filter_clauses.append("activity_date <= ?")
                params.append(end_date.isoformat())

            date_where = f" AND {' AND '.join(date_filter_clauses)}" if date_filter_clauses else ""

            date_rows = connection.execute(
                f"""
                SELECT DISTINCT activity_date FROM (
                    SELECT dae.activity_date
                    FROM daily_activity_entries dae
                    JOIN character_activities ca ON ca.id = dae.character_activity_id
                    JOIN characters c ON c.id = ca.character_id
                    WHERE dae.workspace_id = ? AND dae.deleted_at IS NULL
                      AND (dae.status = 'completed' OR dae.progress_amount > 0)
                      {date_where.replace("activity_date", "dae.activity_date")}
                      {f"AND c.account_id = '{account_id}'" if account_id else ""}
                      {f"AND c.id = '{character_id}'" if character_id else ""}
                    UNION
                    SELECT fs.activity_date
                    FROM farm_sessions fs
                    LEFT JOIN farm_session_participants fsp ON fsp.farm_session_id = fs.id
                    LEFT JOIN characters c
                      ON c.id = fsp.character_id OR c.id = fs.primary_character_id
                    WHERE fs.workspace_id = ? AND fs.deleted_at IS NULL
                      {date_where.replace("activity_date", "fs.activity_date")}
                      {f"AND c.account_id = '{account_id}'" if account_id else ""}
                      {f"AND c.id = '{character_id}'" if character_id else ""}
                )
                ORDER BY activity_date DESC
                """,
                (workspace_id, *params[1:], workspace_id, *params[1:])
                if date_filter_clauses
                else (workspace_id, workspace_id),
            ).fetchall()

            summaries: list[HistoryDaySummary] = []
            for d_row in date_rows:
                act_date_str = d_row["activity_date"]
                act_date = date.fromisoformat(act_date_str)

                runs_query = connection.execute(
                    """
                    SELECT COUNT(ac.id) AS runs,
                           COALESCE(SUM(ac.gold_reward_snapshot), 0) AS gold,
                           COALESCE(SUM(ac.pve_bags_snapshot), 0) AS bags
                    FROM activity_completions ac
                    JOIN daily_activity_entries dae
                      ON dae.id = ac.daily_activity_entry_id AND dae.deleted_at IS NULL
                    JOIN character_activities ca
                      ON ca.id = dae.character_activity_id AND ca.deleted_at IS NULL
                    JOIN characters c ON c.id = ca.character_id AND c.deleted_at IS NULL
                    WHERE ac.workspace_id = ? AND dae.activity_date = ? AND ac.deleted_at IS NULL
                    """
                    + (f" AND c.account_id = '{account_id}'" if account_id else "")
                    + (f" AND c.id = '{character_id}'" if character_id else ""),
                    (workspace_id, act_date_str),
                ).fetchone()

                runs = int(runs_query["runs"]) if runs_query else 0
                dungeon_gold = int(runs_query["gold"]) if runs_query else 0
                dungeon_bags = int(runs_query["bags"]) if runs_query else 0

                char_rows = connection.execute(
                    """
                    SELECT c.id,
                           COUNT(ca.id) AS selected,
                           COALESCE(
                             SUM(CASE WHEN dae.status = 'completed' THEN 1 ELSE 0 END), 0
                           ) AS completed
                    FROM characters c
                    JOIN accounts acc ON acc.id = c.account_id AND acc.deleted_at IS NULL
                    JOIN character_activities ca
                      ON ca.character_id = c.id AND ca.is_active = 1 AND ca.deleted_at IS NULL
                    LEFT JOIN daily_activity_entries dae ON dae.character_activity_id = ca.id
                        AND dae.activity_date = ? AND dae.deleted_at IS NULL
                    WHERE c.workspace_id = ? AND c.is_active = 1 AND c.deleted_at IS NULL
                    """
                    + (f" AND c.account_id = '{account_id}'" if account_id else "")
                    + (f" AND c.id = '{character_id}'" if character_id else "")
                    + " GROUP BY c.id",
                    (act_date_str, workspace_id),
                ).fetchall()
                total_chars = len(char_rows)
                completed_chars = sum(
                    1
                    for r in char_rows
                    if int(r["completed"]) > 0 and int(r["completed"]) >= int(r["selected"])
                )

                tower_query = connection.execute(
                    """
                    SELECT COUNT(fs.id) AS total,
                           COALESCE(
                             SUM(CASE WHEN tsd.completed = 1 THEN 1 ELSE 0 END), 0
                           ) AS completed,
                           COALESCE(SUM(fs.gold_earned), 0) AS tower_gold,
                           COALESCE(SUM(fs.pve_bags_earned), 0) AS tower_bags
                    FROM farm_sessions fs
                    JOIN tower_session_details tsd
                      ON tsd.farm_session_id = fs.id AND tsd.deleted_at IS NULL
                    LEFT JOIN farm_session_participants fsp
                      ON fsp.farm_session_id = fs.id AND fsp.deleted_at IS NULL
                    LEFT JOIN characters c ON c.id = fsp.character_id
                    WHERE fs.workspace_id = ? AND fs.activity_date = ? AND fs.deleted_at IS NULL
                    """
                    + (f" AND c.account_id = '{account_id}'" if account_id else "")
                    + (f" AND c.id = '{character_id}'" if character_id else ""),
                    (workspace_id, act_date_str),
                ).fetchone()

                tower_total = int(tower_query["total"]) if tower_query else 0
                tower_completed = int(tower_query["completed"]) if tower_query else 0
                tower_gold = int(tower_query["tower_gold"]) if tower_query else 0
                tower_bags = int(tower_query["tower_bags"]) if tower_query else 0

                drops_query = connection.execute(
                    """
                    SELECT COALESCE(SUM(fsi.quantity), 0) AS total_drops
                    FROM farm_session_items fsi
                    JOIN farm_sessions fs ON fs.id = fsi.farm_session_id AND fs.deleted_at IS NULL
                    LEFT JOIN farm_session_participants fsp ON fsp.farm_session_id = fs.id
                    LEFT JOIN characters c ON c.id = fsp.character_id
                    WHERE fsi.workspace_id = ? AND fs.activity_date = ? AND fsi.deleted_at IS NULL
                    """
                    + (f" AND c.account_id = '{account_id}'" if account_id else "")
                    + (f" AND c.id = '{character_id}'" if character_id else ""),
                    (workspace_id, act_date_str),
                ).fetchone()
                drops_count = int(drops_query["total_drops"]) if drops_query else 0

                summaries.append(
                    HistoryDaySummary(
                        activity_date=act_date,
                        runs_completed=runs,
                        characters_completed=completed_chars,
                        characters_total=total_chars,
                        gold_earned=Gold(dungeon_gold + tower_gold),
                        pve_bags_earned=dungeon_bags + tower_bags,
                        tower_completed=tower_completed,
                        tower_total=tower_total,
                        drops_count=drops_count,
                    )
                )
            return tuple(summaries)
        finally:
            connection.close()

    def history_day_detail_for_default_workspace(
        self,
        activity_date: date,
        account_id: str | None = None,
        character_id: str | None = None,
    ) -> HistoryDayDetail | None:
        connection = self._database.connect(read_only=True)
        try:
            workspace = connection.execute(
                "SELECT id FROM workspaces WHERE deleted_at IS NULL ORDER BY created_at LIMIT 1"
            ).fetchone()
            if workspace is None:
                return None
            workspace_id = workspace["id"]
            act_date_str = activity_date.isoformat()

            runs_query = connection.execute(
                """
                SELECT COUNT(ac.id) AS runs,
                       COALESCE(SUM(ac.gold_reward_snapshot), 0) AS gold,
                       COALESCE(SUM(ac.pve_bags_snapshot), 0) AS bags
                FROM activity_completions ac
                JOIN daily_activity_entries dae
                  ON dae.id = ac.daily_activity_entry_id AND dae.deleted_at IS NULL
                JOIN character_activities ca
                  ON ca.id = dae.character_activity_id AND ca.deleted_at IS NULL
                JOIN characters c ON c.id = ca.character_id AND c.deleted_at IS NULL
                WHERE ac.workspace_id = ? AND dae.activity_date = ? AND ac.deleted_at IS NULL
                """
                + (f" AND c.account_id = '{account_id}'" if account_id else "")
                + (f" AND c.id = '{character_id}'" if character_id else ""),
                (workspace_id, act_date_str),
            ).fetchone()
            runs = int(runs_query["runs"]) if runs_query else 0
            gold = int(runs_query["gold"]) if runs_query else 0
            bags = int(runs_query["bags"]) if runs_query else 0

            char_rows = connection.execute(
                """
                SELECT c.id, c.name, c.class_name, acc.name AS account_name
                FROM characters c
                JOIN accounts acc ON acc.id = c.account_id AND acc.deleted_at IS NULL
                WHERE c.workspace_id = ? AND c.is_active = 1 AND c.deleted_at IS NULL
                """
                + (f" AND c.account_id = '{account_id}'" if account_id else "")
                + (f" AND c.id = '{character_id}'" if character_id else "")
                + " ORDER BY c.sort_order, c.name",
                (workspace_id,),
            ).fetchall()

            char_details: list[HistoryCharacterDetail] = []
            for ch in char_rows:
                c_id = ch["id"]
                dung_rows = connection.execute(
                    """
                    SELECT a.id AS activity_id, a.name, ca.target_amount,
                           CASE WHEN dae.status = 'completed' THEN 1 ELSE 0 END AS completed,
                           COALESCE(SUM(ac.gold_reward_snapshot), 0) AS gold,
                           COALESCE(SUM(ac.pve_bags_snapshot), 0) AS pve_bags
                    FROM character_activities ca
                    JOIN activities a
                      ON a.id = ca.activity_id AND a.is_active = 1 AND a.deleted_at IS NULL
                    LEFT JOIN daily_activity_entries dae ON dae.character_activity_id = ca.id
                        AND dae.activity_date = ? AND dae.deleted_at IS NULL
                    LEFT JOIN activity_completions ac ON ac.daily_activity_entry_id = dae.id
                        AND ac.deleted_at IS NULL
                    WHERE ca.workspace_id = ? AND ca.character_id = ?
                      AND ca.is_active = 1 AND ca.deleted_at IS NULL
                    GROUP BY a.id, a.name, ca.target_amount, dae.status
                    ORDER BY ca.sort_order, a.name
                    """,
                    (act_date_str, workspace_id, c_id),
                ).fetchall()

                dungeons = tuple(
                    HistoryDungeonEntry(
                        activity_id=dr["activity_id"],
                        name=dr["name"],
                        completed=bool(dr["completed"]),
                        target_amount=int(dr["target_amount"]),
                        gold=Gold(int(dr["gold"])),
                        pve_bags=int(dr["pve_bags"]),
                    )
                    for dr in dung_rows
                )
                completed_count = sum(1 for d in dungeons if d.completed)
                char_details.append(
                    HistoryCharacterDetail(
                        character_id=c_id,
                        name=ch["name"],
                        class_name=ch["class_name"],
                        account_name=ch["account_name"],
                        completed_dungeons=completed_count,
                        selected_dungeons=len(dungeons),
                        dungeons=dungeons,
                    )
                )

            tower_rows = connection.execute(
                """
                SELECT fs.id, tsd.completed, tsd.entry_cost_gold_snapshot
                FROM farm_sessions fs
                JOIN tower_session_details tsd
                  ON tsd.farm_session_id = fs.id AND tsd.deleted_at IS NULL
                WHERE fs.workspace_id = ? AND fs.activity_date = ? AND fs.deleted_at IS NULL
                ORDER BY fs.started_at, fs.rowid
                """,
                (workspace_id, act_date_str),
            ).fetchall()

            tower_sessions: list[HistoryTowerSession] = []
            for tr in tower_rows:
                ts_id = tr["id"]
                part_rows = connection.execute(
                    """
                    SELECT c.name FROM farm_session_participants fsp
                    JOIN characters c ON c.id = fsp.character_id AND c.deleted_at IS NULL
                    WHERE fsp.farm_session_id = ? AND fsp.deleted_at IS NULL
                    ORDER BY fsp.joined_at, c.name
                    """,
                    (ts_id,),
                ).fetchall()
                part_names = tuple(pr["name"] for pr in part_rows)

                t_drop_rows = connection.execute(
                    """
                    SELECT i.name, fsi.quantity, fsi.obtained_at
                    FROM farm_session_items fsi
                    JOIN items i ON i.id = fsi.item_id AND i.deleted_at IS NULL
                    WHERE fsi.farm_session_id = ? AND fsi.deleted_at IS NULL
                    ORDER BY fsi.obtained_at, fsi.rowid
                    """,
                    (ts_id,),
                ).fetchall()
                t_drops = tuple(
                    RecentDrop(
                        tdr["name"],
                        int(tdr["quantity"]),
                        datetime.fromisoformat(tdr["obtained_at"]),
                    )
                    for tdr in t_drop_rows
                )

                tower_sessions.append(
                    HistoryTowerSession(
                        session_id=ts_id,
                        completed=bool(tr["completed"]),
                        cost_gold=Gold(int(tr["entry_cost_gold_snapshot"])),
                        participant_names=part_names,
                        drops=t_drops,
                    )
                )

            all_drops_rows = connection.execute(
                """
                SELECT i.name, fsi.quantity, fsi.obtained_at
                FROM farm_session_items fsi
                JOIN farm_sessions fs ON fs.id = fsi.farm_session_id AND fs.deleted_at IS NULL
                JOIN items i ON i.id = fsi.item_id AND i.deleted_at IS NULL
                WHERE fsi.workspace_id = ? AND fs.activity_date = ? AND fsi.deleted_at IS NULL
                ORDER BY fsi.obtained_at DESC, fsi.rowid DESC
                """,
                (workspace_id, act_date_str),
            ).fetchall()

            all_drops = tuple(
                RecentDrop(
                    adr["name"],
                    int(adr["quantity"]),
                    datetime.fromisoformat(adr["obtained_at"]),
                )
                for adr in all_drops_rows
            )

            return HistoryDayDetail(
                activity_date=activity_date,
                runs_completed=runs,
                gold_earned=Gold(gold),
                pve_bags_earned=bags,
                characters=tuple(char_details),
                tower_sessions=tuple(tower_sessions),
                drops=all_drops,
            )
        finally:
            connection.close()

    def reports_overview_for_default_workspace(
        self, reference_date: date | None = None
    ) -> ReportsOverview | None:
        connection = self._database.connect(read_only=True)
        try:
            workspace = connection.execute(
                "SELECT id FROM workspaces WHERE deleted_at IS NULL ORDER BY created_at LIMIT 1"
            ).fetchone()
            if workspace is None:
                return None
            workspace_id = workspace["id"]

            if reference_date is None:
                # Find latest activity date or today
                latest_row = connection.execute(
                    """
                    SELECT MAX(activity_date) AS latest_date
                    FROM (
                        SELECT activity_date FROM daily_activity_entries
                        WHERE workspace_id = ? AND deleted_at IS NULL
                        UNION ALL
                        SELECT activity_date FROM farm_sessions
                        WHERE workspace_id = ? AND deleted_at IS NULL
                    )
                    """,
                    (workspace_id, workspace_id),
                ).fetchone()
                if latest_row and latest_row["latest_date"]:
                    reference_date = date.fromisoformat(latest_row["latest_date"])
                else:
                    reference_date = date.today()

            # Date boundaries
            month_start = reference_date.replace(day=1)
            if month_start.month == 12:
                next_month_start = month_start.replace(year=month_start.year + 1, month=1)
            else:
                next_month_start = month_start.replace(month=month_start.month + 1)

            if month_start.month == 1:
                prev_month_start = month_start.replace(year=month_start.year - 1, month=12)
            else:
                prev_month_start = month_start.replace(month=month_start.month - 1)

            month_start_str = month_start.isoformat()
            next_month_start_str = next_month_start.isoformat()
            prev_month_start_str = prev_month_start.isoformat()

            # 1. Current Month Gold & Bags
            cur_facts = connection.execute(
                """
                SELECT COALESCE(SUM(gold), 0) AS gold, COALESCE(SUM(bags), 0) AS bags
                FROM (
                    SELECT ac.gold_reward_snapshot AS gold, ac.pve_bags_snapshot AS bags
                    FROM activity_completions ac
                    JOIN daily_activity_entries dae
                      ON dae.id = ac.daily_activity_entry_id AND dae.deleted_at IS NULL
                    WHERE ac.workspace_id = ? AND ac.deleted_at IS NULL
                      AND dae.activity_date >= ? AND dae.activity_date < ?
                    UNION ALL
                    SELECT fs.gold_earned AS gold, fs.pve_bags_earned AS bags
                    FROM farm_sessions fs
                    WHERE fs.workspace_id = ? AND fs.status = 'completed' AND fs.deleted_at IS NULL
                      AND fs.activity_date >= ? AND fs.activity_date < ?
                )
                """,
                (
                    workspace_id,
                    month_start_str,
                    next_month_start_str,
                    workspace_id,
                    month_start_str,
                    next_month_start_str,
                ),
            ).fetchone()
            cur_month_gold = int(cur_facts["gold"]) if cur_facts else 0
            cur_month_bags = int(cur_facts["bags"]) if cur_facts else 0

            # 2. Previous Month Gold & Bags
            prev_facts = connection.execute(
                """
                SELECT COALESCE(SUM(gold), 0) AS gold, COALESCE(SUM(bags), 0) AS bags
                FROM (
                    SELECT ac.gold_reward_snapshot AS gold, ac.pve_bags_snapshot AS bags
                    FROM activity_completions ac
                    JOIN daily_activity_entries dae
                      ON dae.id = ac.daily_activity_entry_id AND dae.deleted_at IS NULL
                    WHERE ac.workspace_id = ? AND ac.deleted_at IS NULL
                      AND dae.activity_date >= ? AND dae.activity_date < ?
                    UNION ALL
                    SELECT fs.gold_earned AS gold, fs.pve_bags_earned AS bags
                    FROM farm_sessions fs
                    WHERE fs.workspace_id = ? AND fs.status = 'completed' AND fs.deleted_at IS NULL
                      AND fs.activity_date >= ? AND fs.activity_date < ?
                )
                """,
                (
                    workspace_id,
                    prev_month_start_str,
                    month_start_str,
                    workspace_id,
                    prev_month_start_str,
                    month_start_str,
                ),
            ).fetchone()
            prev_month_gold = int(prev_facts["gold"]) if prev_facts else 0
            prev_month_bags = int(prev_facts["bags"]) if prev_facts else 0

            # 3. All Time Farm Gold
            all_time_row = connection.execute(
                """
                SELECT COALESCE(SUM(gold), 0) AS gold
                FROM (
                    SELECT ac.gold_reward_snapshot AS gold
                    FROM activity_completions ac
                    WHERE ac.workspace_id = ? AND ac.deleted_at IS NULL
                    UNION ALL
                    SELECT fs.gold_earned AS gold
                    FROM farm_sessions fs
                    WHERE fs.workspace_id = ? AND fs.status = 'completed' AND fs.deleted_at IS NULL
                )
                """,
                (workspace_id, workspace_id),
            ).fetchone()
            all_time_gold = int(all_time_row["gold"]) if all_time_row else 0

            # 4. Sales & Financials
            cur_sales_row = connection.execute(
                """
                SELECT COALESCE(SUM(real_amount_minor), 0) AS sales_minor,
                       COALESCE(SUM(gold_quantity), 0) AS gold_converted,
                       COUNT(id) AS sales_count
                FROM sales
                WHERE workspace_id = ? AND status = 'completed' AND deleted_at IS NULL
                  AND sold_at >= ? AND sold_at < ?
                """,
                (workspace_id, month_start_str, next_month_start_str),
            ).fetchone()
            monthly_sales_minor = int(cur_sales_row["sales_minor"]) if cur_sales_row else 0
            monthly_gold_converted = int(cur_sales_row["gold_converted"]) if cur_sales_row else 0
            monthly_sales_count = int(cur_sales_row["sales_count"]) if cur_sales_row else 0

            prev_sales_row = connection.execute(
                """
                SELECT COALESCE(SUM(real_amount_minor), 0) AS sales_minor
                FROM sales
                WHERE workspace_id = ? AND status = 'completed' AND deleted_at IS NULL
                  AND sold_at >= ? AND sold_at < ?
                """,
                (workspace_id, prev_month_start_str, month_start_str),
            ).fetchone()
            prev_sales_minor = int(prev_sales_row["sales_minor"]) if prev_sales_row else 0

            all_sales_row = connection.execute(
                """
                SELECT COALESCE(SUM(real_amount_minor), 0) AS total_sales_minor,
                       COALESCE(SUM(gold_quantity), 0) AS total_gold_converted,
                       COUNT(id) AS total_sales_count
                FROM sales
                WHERE workspace_id = ? AND status = 'completed' AND deleted_at IS NULL
                """,
                (workspace_id,),
            ).fetchone()
            total_sales_minor = int(all_sales_row["total_sales_minor"]) if all_sales_row else 0
            total_gold_converted = (
                int(all_sales_row["total_gold_converted"]) if all_sales_row else 0
            )
            total_sales_count = int(all_sales_row["total_sales_count"]) if all_sales_row else 0

            # Items sold count (from inventory movements or sales)
            items_sold_row = connection.execute(
                """
                SELECT COALESCE(SUM(ABS(quantity_delta)), 0) AS items_sold
                FROM inventory_movements
                WHERE workspace_id = ? AND movement_type = 'sale' AND deleted_at IS NULL
                """,
                (workspace_id,),
            ).fetchone()
            items_sold_count = (
                int(items_sold_row["items_sold"])
                if items_sold_row and items_sold_row["items_sold"] > 0
                else total_sales_count
            )

            # Growth / Change percentages
            farm_gold_change_percent = (
                round(((cur_month_gold - prev_month_gold) / prev_month_gold) * 100)
                if prev_month_gold > 0
                else (100 if cur_month_gold > 0 else 0)
            )
            sales_change_percent = (
                round(((monthly_sales_minor - prev_sales_minor) / prev_sales_minor) * 100)
                if prev_sales_minor > 0
                else (100 if monthly_sales_minor > 0 else 0)
            )
            pve_bags_change_percent = (
                round(((cur_month_bags - prev_month_bags) / prev_month_bags) * 100)
                if prev_month_bags > 0
                else (100 if cur_month_bags > 0 else 0)
            )

            days_passed = max(1, reference_date.day)
            daily_avg_gold = cur_month_gold // days_passed

            kpis = ReportKpis(
                monthly_sales_minor=monthly_sales_minor,
                sales_change_percent=sales_change_percent,
                monthly_farm_gold=Gold(cur_month_gold),
                farm_gold_change_percent=farm_gold_change_percent,
                all_time_farm_gold=Gold(all_time_gold),
                daily_average_gold=Gold(daily_avg_gold),
                monthly_pve_bags_sold=cur_month_bags,
                pve_bags_change_percent=pve_bags_change_percent,
            )

            # 5. Daily Evolution (Evolução do Mês)
            daily_rows = connection.execute(
                """
                SELECT activity_date, SUM(gold) AS gold, SUM(runs) AS runs
                FROM (
                    SELECT dae.activity_date, ac.gold_reward_snapshot AS gold, 1 AS runs
                    FROM activity_completions ac
                    JOIN daily_activity_entries dae
                      ON dae.id = ac.daily_activity_entry_id AND dae.deleted_at IS NULL
                    WHERE ac.workspace_id = ? AND ac.deleted_at IS NULL
                      AND dae.activity_date >= ? AND dae.activity_date < ?
                    UNION ALL
                    SELECT fs.activity_date, fs.gold_earned AS gold, fs.runs_count AS runs
                    FROM farm_sessions fs
                    WHERE fs.workspace_id = ? AND fs.status = 'completed' AND fs.deleted_at IS NULL
                      AND fs.activity_date >= ? AND fs.activity_date < ?
                )
                GROUP BY activity_date
                ORDER BY activity_date
                """,
                (
                    workspace_id,
                    month_start_str,
                    next_month_start_str,
                    workspace_id,
                    month_start_str,
                    next_month_start_str,
                ),
            ).fetchall()
            daily_evolution = tuple(
                DailyEvolutionPoint(
                    day=date.fromisoformat(row["activity_date"]).day,
                    activity_date=date.fromisoformat(row["activity_date"]),
                    gold=Gold(int(row["gold"])),
                    runs=int(row["runs"]),
                )
                for row in daily_rows
            )

            # 6. Monthly Comparison (Comparativo Mensal)
            monthly_comparison = MonthlyComparison(
                previous_month_name="Mês passado",
                previous_month_gold=Gold(prev_month_gold),
                current_month_name="Mês atual",
                current_month_gold=Gold(cur_month_gold),
                growth_percent=farm_gold_change_percent,
            )

            # 7. Cumulative History (Acumulado desde o início)
            monthly_history_rows = connection.execute(
                """
                SELECT SUBSTR(activity_date, 1, 7) AS month_key, SUM(gold) AS month_gold
                FROM (
                    SELECT dae.activity_date, ac.gold_reward_snapshot AS gold
                    FROM activity_completions ac
                    JOIN daily_activity_entries dae
                      ON dae.id = ac.daily_activity_entry_id AND dae.deleted_at IS NULL
                    WHERE ac.workspace_id = ? AND ac.deleted_at IS NULL
                    UNION ALL
                    SELECT fs.activity_date, fs.gold_earned AS gold
                    FROM farm_sessions fs
                    WHERE fs.workspace_id = ? AND fs.status = 'completed' AND fs.deleted_at IS NULL
                )
                GROUP BY month_key
                ORDER BY month_key
                """,
                (workspace_id, workspace_id),
            ).fetchall()
            cumulative_list: list[CumulativeMonthPoint] = []
            running_cum = 0
            for r in monthly_history_rows:
                running_cum += int(r["month_gold"])
                # Format label: 2026-08 -> ago/26
                m_key = r["month_key"]
                parts = m_key.split("-")
                m_num = int(parts[1])
                y_short = parts[0][2:]
                month_names = [
                    "jan",
                    "fev",
                    "mar",
                    "abr",
                    "mai",
                    "jun",
                    "jul",
                    "ago",
                    "set",
                    "out",
                    "nov",
                    "dez",
                ]
                label = f"{month_names[m_num - 1]}/{y_short}"
                cumulative_list.append(
                    CumulativeMonthPoint(
                        month_label=label,
                        month_key=m_key,
                        cumulative_gold=Gold(running_cum),
                    )
                )

            # 8. Financial Summary & Recent Sales
            avg_ticket = (
                monthly_sales_minor // monthly_sales_count
                if monthly_sales_count > 0
                else (total_sales_minor // total_sales_count if total_sales_count > 0 else 0)
            )
            financial_summary = FinancialSummary(
                sales_amount_minor=monthly_sales_minor or total_sales_minor,
                items_sold_count=items_sold_count,
                gold_converted_total=Gold(monthly_gold_converted or total_gold_converted),
                average_ticket_minor=avg_ticket,
            )

            recent_sales_rows = connection.execute(
                """
                SELECT id, buyer_reference, real_amount_minor, currency, sold_at
                FROM sales
                WHERE workspace_id = ? AND deleted_at IS NULL
                ORDER BY sold_at DESC, created_at DESC
                LIMIT 5
                """,
                (workspace_id,),
            ).fetchall()
            recent_sales = tuple(
                RecentSaleRow(
                    id=sr["id"],
                    item_name=sr["buyer_reference"] or "Item comercializado",
                    quantity=1,
                    amount_minor=int(sr["real_amount_minor"] or 0),
                    currency=sr["currency"] or "BRL",
                    sold_at=datetime.fromisoformat(sr["sold_at"])
                    if sr["sold_at"]
                    else datetime.now(),
                )
                for sr in recent_sales_rows
            )

            # 9. Monthly Target (Meta do Mês)
            target_gold = Gold(25_000_000)
            target_pct = (
                min(100, round((cur_month_gold / target_gold.amount) * 100))
                if target_gold.amount > 0
                else 0
            )
            rem_gold = max(0, target_gold.amount - cur_month_gold)
            days_left = max(0, (next_month_start - reference_date).days)
            monthly_target = MonthlyTarget(
                target_gold=target_gold,
                current_gold=Gold(cur_month_gold),
                percentage=target_pct,
                remaining_gold=Gold(rem_gold),
                days_remaining=days_left,
            )

            # 10. Top Characters of the Month
            top_char_rows = connection.execute(
                """
                SELECT c.id, c.name, c.class_name, COALESCE(SUM(ac.gold_reward_snapshot), 0) AS gold
                FROM characters c
                JOIN character_activities ca ON ca.character_id = c.id AND ca.deleted_at IS NULL
                JOIN daily_activity_entries dae
                  ON dae.character_activity_id = ca.id AND dae.deleted_at IS NULL
                JOIN activity_completions ac
                  ON ac.daily_activity_entry_id = dae.id AND ac.deleted_at IS NULL
                WHERE c.workspace_id = ? AND c.is_active = 1 AND c.deleted_at IS NULL
                  AND dae.activity_date >= ? AND dae.activity_date < ?
                GROUP BY c.id
                ORDER BY gold DESC, c.name
                LIMIT 5
                """,
                (workspace_id, month_start_str, next_month_start_str),
            ).fetchall()
            top_characters = tuple(
                TopCharacterRow(
                    rank=idx + 1,
                    character_id=tcr["id"],
                    character_name=tcr["name"],
                    class_name=tcr["class_name"],
                    gold_earned=Gold(int(tcr["gold"])),
                )
                for idx, tcr in enumerate(top_char_rows)
            )

            return ReportsOverview(
                kpis=kpis,
                daily_evolution=daily_evolution,
                monthly_comparison=monthly_comparison,
                cumulative_history=tuple(cumulative_list),
                financial_summary=financial_summary,
                recent_sales=recent_sales,
                monthly_target=monthly_target,
                top_characters=top_characters,
            )
        finally:
            connection.close()
