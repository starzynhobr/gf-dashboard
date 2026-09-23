from __future__ import annotations

import calendar
from datetime import UTC, date, datetime, timedelta
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
    MonthlySalesHistoryPoint,
    MonthlyTarget,
    RecentDrop,
    RecentMovement,
    RecentSaleRow,
    ReportKpis,
    ReportsOverview,
    RoutineDungeon,
    TodayActivityOverview,
    TodayCharacter,
    TodayEstimate,
    TopCharacterRow,
    WorkRoutineHistory,
    WorkRoutineSessionRow,
)
from gf_dashboard.application.work_routines import MIN_RECORDED_ROUTINE_SECONDS
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
                           AS completed_dungeons,
                       MAX(CASE WHEN cdm.completed_at IS NOT NULL THEN 1 ELSE 0 END)
                           AS daily_mission_completed,
                       COALESCE(vip.expires_at, vip.expires_on || 'T00:00:00+00:00')
                           AS vip_expires_at
                FROM characters c
                JOIN accounts acc ON acc.id = c.account_id AND acc.is_active = 1
                    AND acc.deleted_at IS NULL
                LEFT JOIN character_activities ca ON ca.character_id = c.id AND ca.is_active = 1
                    AND ca.deleted_at IS NULL
                LEFT JOIN activities a ON a.id = ca.activity_id AND a.is_active = 1
                    AND a.deleted_at IS NULL AND a.category = 'dungeon'
                LEFT JOIN daily_activity_entries dae ON dae.character_activity_id = ca.id
                    AND dae.activity_date = ? AND dae.deleted_at IS NULL AND a.id IS NOT NULL
                LEFT JOIN character_daily_missions cdm ON cdm.character_id = c.id
                    AND cdm.workspace_id = c.workspace_id AND cdm.activity_date = ?
                    AND cdm.deleted_at IS NULL
                LEFT JOIN character_vip_subscriptions vip ON vip.character_id = c.id
                    AND vip.workspace_id = c.workspace_id
                    AND COALESCE(vip.expires_at, vip.expires_on || 'T00:00:00+00:00') > ?
                    AND vip.deleted_at IS NULL
                WHERE c.workspace_id = ? AND c.is_active = 1 AND c.deleted_at IS NULL
                GROUP BY c.id ORDER BY c.sort_order, c.name
                """,
                (
                    activity_date.isoformat(),
                    activity_date.isoformat(),
                    datetime.now(UTC).isoformat(),
                    workspace["id"],
                ),
            ).fetchall()
            return tuple(
                TodayCharacter(
                    row["id"],
                    row["name"],
                    row["class_name"],
                    row["account_name"],
                    int(row["completed_dungeons"]),
                    int(row["selected_dungeons"]),
                    bool(row["daily_mission_completed"]),
                    datetime.fromisoformat(row["vip_expires_at"])
                    if row["vip_expires_at"]
                    else None,
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
                SELECT activity_date, SUM(gold) AS gold, SUM(pve_bags) AS pve_bags
                FROM (
                    SELECT dae.activity_date, ac.gold_reward_snapshot AS gold,
                           ac.pve_bags_snapshot AS pve_bags
                    FROM activity_completions ac
                    JOIN daily_activity_entries dae ON dae.id = ac.daily_activity_entry_id
                        AND dae.deleted_at IS NULL
                    WHERE ac.workspace_id = ? AND ac.deleted_at IS NULL
                        AND dae.activity_date >= ? AND dae.activity_date < ?
                    UNION ALL
                    SELECT fs.activity_date, fs.gold_earned AS gold,
                           fs.pve_bags_earned AS pve_bags
                    FROM farm_sessions fs
                    WHERE fs.workspace_id = ? AND fs.status = 'completed'
                        AND fs.deleted_at IS NULL AND fs.activity_date >= ?
                        AND fs.activity_date < ?
                        AND (fs.gold_earned > 0 OR fs.pve_bags_earned > 0)
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
            bag_quote_row = connection.execute(
                """SELECT mpq.unit_value_gold FROM market_price_quotes mpq
                JOIN items i ON i.id = mpq.item_id AND i.name = 'Saco PvE'
                WHERE mpq.workspace_id = ? AND mpq.deleted_at IS NULL AND i.deleted_at IS NULL
                ORDER BY mpq.observed_at DESC, mpq.rowid DESC LIMIT 1""",
                (workspace_id,),
            ).fetchone()
            bag_unit_value = int(bag_quote_row["unit_value_gold"]) if bag_quote_row else 0
            monthly_gold = tuple(
                MonthlyGoldPoint(
                    date.fromisoformat(row["activity_date"]),
                    Gold(int(row["gold"])),
                    int(row["pve_bags"]),
                )
                for row in month_rows
            )
            monthly_gold_equivalent_total = sum(
                point.gold.amount + point.pve_bags * bag_unit_value for point in monthly_gold
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

            today_bags_row = connection.execute(
                """
                SELECT COALESCE(SUM(bags), 0) AS bags
                FROM (
                    SELECT ac.pve_bags_snapshot AS bags
                    FROM activity_completions ac
                    JOIN daily_activity_entries dae
                      ON dae.id = ac.daily_activity_entry_id AND dae.deleted_at IS NULL
                    WHERE ac.workspace_id = ? AND ac.deleted_at IS NULL
                      AND dae.activity_date = ?
                    UNION ALL
                    SELECT fs.pve_bags_earned AS bags
                    FROM farm_sessions fs
                    WHERE fs.workspace_id = ? AND fs.status = 'completed'
                      AND fs.deleted_at IS NULL AND fs.activity_date = ?
                )
                """,
                (workspace_id, act_date_str, workspace_id, act_date_str),
            ).fetchone()
            pve_bags_earned_today = int(today_bags_row["bags"]) if today_bags_row else 0

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
                monthly_gold_total=Gold(monthly_gold_equivalent_total),
                earned_gold_today=Gold(earned_gold_today),
                pve_bags_earned_today=pve_bags_earned_today,
                today_sales_minor=today_sales_minor,
                pve_bag_unit_value_gold=Gold(bag_unit_value) if bag_quote_row else None,
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

            routine_union = (
                f"""UNION
                    SELECT substr(finished_at, 1, 10) AS activity_date
                    FROM work_routine_sessions
                    WHERE workspace_id = ? AND status = 'completed' AND deleted_at IS NULL
                      AND accumulated_seconds >= {MIN_RECORDED_ROUTINE_SECONDS}
                      AND finished_at IS NOT NULL
                      {date_where.replace("activity_date", "substr(finished_at, 1, 10)")}"""
                if not account_id and not character_id
                else ""
            )

            if not account_id and not character_id:
                if date_filter_clauses:
                    full_params = (
                        workspace_id,
                        *params[1:],
                        workspace_id,
                        *params[1:],
                        workspace_id,
                        *params[1:],
                    )
                else:
                    full_params = (workspace_id, workspace_id, workspace_id)
            elif date_filter_clauses:
                full_params = (workspace_id, *params[1:], workspace_id, *params[1:])
            else:
                full_params = (workspace_id, workspace_id)

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
                    {routine_union}
                )
                ORDER BY activity_date DESC
                """,
                full_params,
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
                           COUNT(a.id) AS selected,
                           COALESCE(
                             SUM(CASE WHEN a.id IS NOT NULL AND dae.status = 'completed'
                                 THEN 1 ELSE 0 END), 0
                           ) AS completed
                    FROM characters c
                    JOIN accounts acc ON acc.id = c.account_id AND acc.deleted_at IS NULL
                    LEFT JOIN character_activities ca
                      ON ca.character_id = c.id AND ca.workspace_id = c.workspace_id
                        AND ca.is_active = 1 AND ca.deleted_at IS NULL
                    LEFT JOIN activities a ON a.id = ca.activity_id
                        AND a.is_active = 1 AND a.deleted_at IS NULL
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
                    1 for r in char_rows if int(r["completed"]) >= int(r["selected"])
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

                routine_query = connection.execute(
                    f"""
                    SELECT COALESCE(SUM(accumulated_seconds), 0) AS total_seconds
                    FROM work_routine_sessions
                    WHERE workspace_id = ? AND status = 'completed' AND deleted_at IS NULL
                      AND accumulated_seconds >= {MIN_RECORDED_ROUTINE_SECONDS}
                      AND (
                        substr(finished_at, 1, 10) = ?
                        OR (finished_at IS NULL AND substr(started_at, 1, 10) = ?)
                      )
                    """,
                    (workspace_id, act_date_str, act_date_str),
                ).fetchone()
                routine_seconds = int(routine_query["total_seconds"]) if routine_query else 0

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
                        routine_duration_seconds=routine_seconds,
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

            routine_query = connection.execute(
                f"""
                SELECT COALESCE(SUM(accumulated_seconds), 0) AS total_seconds
                FROM work_routine_sessions
                WHERE workspace_id = ? AND status = 'completed' AND deleted_at IS NULL
                  AND accumulated_seconds >= {MIN_RECORDED_ROUTINE_SECONDS}
                  AND (
                    substr(finished_at, 1, 10) = ?
                    OR (finished_at IS NULL AND substr(started_at, 1, 10) = ?)
                  )
                """,
                (workspace_id, act_date_str, act_date_str),
            ).fetchone()
            routine_seconds = int(routine_query["total_seconds"]) if routine_query else 0

            return HistoryDayDetail(
                activity_date=activity_date,
                runs_completed=runs,
                gold_earned=Gold(gold),
                pve_bags_earned=bags,
                characters=tuple(char_details),
                tower_sessions=tuple(tower_sessions),
                drops=all_drops,
                routine_duration_seconds=routine_seconds,
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
                        UNION ALL
                        SELECT SUBSTR(sold_at, 1, 10) AS activity_date FROM sales
                        WHERE workspace_id = ? AND deleted_at IS NULL
                    )
                    """,
                    (workspace_id, workspace_id, workspace_id),
                ).fetchone()
                if latest_row and latest_row["latest_date"]:
                    reference_date = date.fromisoformat(latest_row["latest_date"])
                else:
                    reference_date = date.today()

            ref_year = reference_date.year
            ref_month = reference_date.month
            ref_day = reference_date.day
            _, days_in_cur_month = calendar.monthrange(ref_year, ref_month)
            is_partial = ref_day < days_in_cur_month

            # Date boundaries for current month
            month_start = date(ref_year, ref_month, 1)
            if ref_month == 12:
                next_month_start = date(ref_year + 1, 1, 1)
            else:
                next_month_start = date(ref_year, ref_month + 1, 1)

            # Date boundaries for previous month
            if ref_month == 1:
                prev_year = ref_year - 1
                prev_month = 12
            else:
                prev_year = ref_year
                prev_month = ref_month - 1

            prev_month_start = date(prev_year, prev_month, 1)

            # Compare month-to-date with the previous full calendar month.
            if is_partial:
                cur_cutoff_date = reference_date
            else:
                cur_cutoff_date = date(ref_year, ref_month, days_in_cur_month)

            cur_cutoff_exclusive = cur_cutoff_date + timedelta(days=1)
            prev_cutoff_exclusive = month_start

            month_start_str = month_start.isoformat()
            next_month_start_str = next_month_start.isoformat()
            cur_cutoff_exclusive_str = cur_cutoff_exclusive.isoformat()
            prev_month_start_str = prev_month_start.isoformat()
            prev_cutoff_exclusive_str = prev_cutoff_exclusive.isoformat()

            # 1. Current Month Gold & Bags (up to current cutoff)
            cur_facts = connection.execute(
                """
                SELECT COALESCE(SUM(gold), 0) AS gold,
                       COALESCE(SUM(bags), 0) AS bags,
                       COUNT(DISTINCT activity_date) AS active_days
                FROM (
                    SELECT dae.activity_date AS activity_date,
                           ac.gold_reward_snapshot AS gold,
                           ac.pve_bags_snapshot AS bags
                    FROM activity_completions ac
                    JOIN daily_activity_entries dae
                      ON dae.id = ac.daily_activity_entry_id AND dae.deleted_at IS NULL
                    WHERE ac.workspace_id = ? AND ac.deleted_at IS NULL
                      AND dae.activity_date >= ? AND dae.activity_date < ?
                    UNION ALL
                    SELECT fs.activity_date AS activity_date,
                           fs.gold_earned AS gold,
                           fs.pve_bags_earned AS bags
                    FROM farm_sessions fs
                    WHERE fs.workspace_id = ? AND fs.status = 'completed' AND fs.deleted_at IS NULL
                      AND fs.activity_date >= ? AND fs.activity_date < ?
                )
                """,
                (
                    workspace_id,
                    month_start_str,
                    cur_cutoff_exclusive_str,
                    workspace_id,
                    month_start_str,
                    cur_cutoff_exclusive_str,
                ),
            ).fetchone()
            cur_month_gold = int(cur_facts["gold"]) if cur_facts else 0
            cur_month_bags = int(cur_facts["bags"]) if cur_facts else 0
            active_farm_days = int(cur_facts["active_days"]) if cur_facts else 0

            # 2. Previous Month Gold & Bags (full calendar month)
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
                    prev_cutoff_exclusive_str,
                    workspace_id,
                    prev_month_start_str,
                    prev_cutoff_exclusive_str,
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
                (workspace_id, month_start_str, cur_cutoff_exclusive_str),
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
                (workspace_id, prev_month_start_str, prev_cutoff_exclusive_str),
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

            sold_items_row = connection.execute(
                """
                SELECT COALESCE(SUM(item_quantity), 0) AS items_sold
                FROM sales
                WHERE workspace_id = ? AND status = 'completed' AND deleted_at IS NULL
                  AND sale_type IN ('pve_bag', 'item')
                  AND sold_at >= ? AND sold_at < ?
                """,
                (workspace_id, month_start_str, cur_cutoff_exclusive_str),
            ).fetchone()
            items_sold_count = int(sold_items_row["items_sold"]) if sold_items_row else 0

            # Growth / Change percentages using helper
            def _calc_change(cur_val: int, prev_val: int) -> tuple[int | None, str]:
                if prev_val > 0:
                    return (round(((cur_val - prev_val) / prev_val) * 100), "valid")
                if prev_val == 0 and cur_val == 0:
                    return (0, "no_activity")
                return (None, "no_baseline")

            sales_change_percent, sales_change_status = _calc_change(
                monthly_sales_minor, prev_sales_minor
            )
            farm_gold_change_percent, farm_gold_change_status = _calc_change(
                cur_month_gold, prev_month_gold
            )
            pve_bags_earned_change_percent, pve_bags_change_status = _calc_change(
                cur_month_bags, prev_month_bags
            )
            growth_percent, growth_status = farm_gold_change_percent, farm_gold_change_status

            daily_avg_gold = cur_month_gold // max(1, active_farm_days)

            kpis = ReportKpis(
                monthly_sales_minor=monthly_sales_minor,
                sales_change_percent=sales_change_percent,
                monthly_farm_gold=Gold(cur_month_gold),
                farm_gold_change_percent=farm_gold_change_percent,
                all_time_farm_gold=Gold(all_time_gold),
                daily_average_gold=Gold(daily_avg_gold),
                monthly_pve_bags_earned=cur_month_bags,
                pve_bags_earned_change_percent=pve_bags_earned_change_percent,
                previous_sales_minor=prev_sales_minor,
                previous_farm_gold=Gold(prev_month_gold),
                previous_pve_bags_earned=prev_month_bags,
                is_partial_month=is_partial,
                comparison_period_days=ref_day if is_partial else days_in_cur_month,
                sales_change_status=sales_change_status,
                farm_gold_change_status=farm_gold_change_status,
                pve_bags_change_status=pve_bags_change_status,
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

            # 6. Monthly Comparison (month-to-date vs previous full month)
            month_names_pt = (
                "janeiro",
                "fevereiro",
                "março",
                "abril",
                "maio",
                "junho",
                "julho",
                "agosto",
                "setembro",
                "outubro",
                "novembro",
                "dezembro",
            )
            month_abbr_pt = (
                "Jan",
                "Fev",
                "Mar",
                "Abr",
                "Mai",
                "Jun",
                "Jul",
                "Ago",
                "Set",
                "Out",
                "Nov",
                "Dez",
            )
            if is_partial:
                current_period_label = f"1 - {ref_day} de {month_names_pt[ref_month - 1]}"
                current_month_name = f"{month_abbr_pt[ref_month - 1]} (1-{ref_day})"
            else:
                current_period_label = (
                    f"{month_names_pt[ref_month - 1].capitalize()} de {ref_year} (mês completo)"
                )
                current_month_name = f"{month_abbr_pt[ref_month - 1]}/{str(ref_year)[2:]}"
            previous_period_label = (
                f"{month_names_pt[prev_month - 1].capitalize()} de {prev_year} (mês completo)"
            )
            previous_month_name = f"{month_abbr_pt[prev_month - 1]}/{str(prev_year)[2:]}"

            monthly_comparison = MonthlyComparison(
                previous_month_name=previous_month_name,
                previous_month_gold=Gold(prev_month_gold),
                current_month_name=current_month_name,
                current_month_gold=Gold(cur_month_gold),
                growth_percent=growth_percent,
                is_partial=is_partial,
                growth_status=growth_status,
                previous_period_label=previous_period_label,
                current_period_label=current_period_label,
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

            # 8. Monthly Sales History (Histórico mensal de faturamento em R$)
            cur_month_key = f"{ref_year:04d}-{ref_month:02d}"
            sales_by_month_rows = connection.execute(
                """
                SELECT SUBSTR(sold_at, 1, 7) AS month_key,
                       COALESCE(SUM(real_amount_minor), 0) AS sales_amount_minor,
                       COUNT(id) AS sales_count
                FROM sales
                WHERE workspace_id = ? AND status = 'completed' AND deleted_at IS NULL
                  AND sold_at IS NOT NULL
                GROUP BY month_key
                ORDER BY month_key ASC
                """,
                (workspace_id,),
            ).fetchall()

            sales_by_month: dict[str, tuple[int, int]] = {
                str(r["month_key"]): (int(r["sales_amount_minor"]), int(r["sales_count"]))
                for r in sales_by_month_rows
            }
            if cur_month_key not in sales_by_month:
                sales_by_month[cur_month_key] = (monthly_sales_minor, monthly_sales_count)

            all_month_keys = sorted(sales_by_month.keys())
            selected_month_keys = all_month_keys[-12:]
            monthly_sales_history: list[MonthlySalesHistoryPoint] = []
            for m_key in selected_month_keys:
                parts = m_key.split("-")
                m_y = int(parts[0])
                m_m = int(parts[1])
                label = f"{month_abbr_pt[m_m - 1]}/{str(m_y)[2:]}"
                amt, cnt = sales_by_month[m_key]
                is_part = m_key == cur_month_key and is_partial
                monthly_sales_history.append(
                    MonthlySalesHistoryPoint(
                        month_key=m_key,
                        month_label=label,
                        sales_amount_minor=amt,
                        sales_count=cnt,
                        is_partial=is_part,
                    )
                )

            # 9. Financial Summary & Recent Sales
            avg_ticket = (
                monthly_sales_minor // monthly_sales_count
                if monthly_sales_count > 0
                else (total_sales_minor // total_sales_count if total_sales_count > 0 else 0)
            )
            vip_expense_row = connection.execute(
                """SELECT COALESCE(SUM(amount_gold), 0) AS gold FROM transactions
                WHERE workspace_id = ? AND type = 'expense' AND category = 'vip'
                  AND deleted_at IS NULL AND occurred_at >= ? AND occurred_at < ?""",
                (workspace_id, month_start_str, next_month_start_str),
            ).fetchone()
            tower_expense_row = connection.execute(
                """SELECT COALESCE(SUM(td.entry_cost_gold_snapshot), 0) AS gold
                FROM tower_session_details td JOIN farm_sessions fs ON fs.id = td.farm_session_id
                WHERE td.workspace_id = ? AND td.deleted_at IS NULL AND fs.deleted_at IS NULL
                  AND fs.activity_date >= ? AND fs.activity_date < ?""",
                (workspace_id, month_start_str, next_month_start_str),
            ).fetchone()
            manual_expense_row = connection.execute(
                """SELECT COALESCE(SUM(amount_gold), 0) AS gold FROM transactions
                WHERE workspace_id = ? AND type = 'expense' AND category NOT IN ('vip')
                  AND deleted_at IS NULL AND occurred_at >= ? AND occurred_at < ?""",
                (workspace_id, month_start_str, next_month_start_str),
            ).fetchone()
            vip_expenses_gold = int(vip_expense_row["gold"]) if vip_expense_row else 0
            tower_expenses_gold = int(tower_expense_row["gold"]) if tower_expense_row else 0
            manual_expenses_gold = int(manual_expense_row["gold"]) if manual_expense_row else 0
            financial_summary = FinancialSummary(
                sales_amount_minor=monthly_sales_minor or total_sales_minor,
                items_sold_count=items_sold_count,
                gold_converted_total=Gold(monthly_gold_converted or total_gold_converted),
                average_ticket_minor=avg_ticket,
                expenses_gold=Gold(vip_expenses_gold + tower_expenses_gold + manual_expenses_gold),
                vip_expenses_gold=Gold(vip_expenses_gold),
                tower_expenses_gold=Gold(tower_expenses_gold),
                manual_expenses_gold=Gold(manual_expenses_gold),
            )

            recent_sales_rows = connection.execute(
                """
                SELECT id, item_description, buyer_reference, item_quantity,
                       real_amount_minor, converted_currency, sold_at
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
                    item_name=sr["item_description"]
                    or sr["buyer_reference"]
                    or "Item comercializado",
                    quantity=int(sr["item_quantity"] or 1),
                    amount_minor=int(sr["real_amount_minor"] or 0),
                    currency=sr["converted_currency"] or "BRL",
                    sold_at=datetime.fromisoformat(sr["sold_at"])
                    if sr["sold_at"]
                    else datetime.now(),
                )
                for sr in recent_sales_rows
            )

            recent_movement_rows = connection.execute(
                """
                SELECT * FROM (
                    SELECT
                        'dungeon:' || dae.id AS id,
                        'dungeon' AS kind,
                        a.name AS title,
                        c.name AS detail,
                        MAX(ac.completed_at) AS occurred_at,
                        SUM(ac.gold_reward_snapshot) AS gold_amount,
                        SUM(ac.pve_bags_snapshot) AS pve_bags,
                        NULL AS amount_minor
                    FROM daily_activity_entries dae
                    JOIN character_activities ca ON ca.id = dae.character_activity_id
                    JOIN characters c ON c.id = ca.character_id
                    JOIN activities a ON a.id = ca.activity_id
                    JOIN activity_completions ac ON ac.daily_activity_entry_id = dae.id
                    WHERE dae.workspace_id = ? AND dae.deleted_at IS NULL
                      AND ca.deleted_at IS NULL AND c.deleted_at IS NULL
                      AND a.deleted_at IS NULL AND ac.deleted_at IS NULL
                    GROUP BY dae.id, a.name, c.name

                    UNION ALL

                    SELECT
                        'tower:' || fs.id AS id,
                        'tower' AS kind,
                        'Torre concluída' AS title,
                        td.guild_name_snapshot AS detail,
                        td.completed_at AS occurred_at,
                        td.entry_cost_gold_snapshot AS gold_amount,
                        NULL AS pve_bags,
                        NULL AS amount_minor
                    FROM farm_sessions fs
                    JOIN tower_session_details td ON td.farm_session_id = fs.id
                    WHERE fs.workspace_id = ? AND fs.deleted_at IS NULL
                      AND td.deleted_at IS NULL AND td.completed = 1

                    UNION ALL

                    SELECT
                        'sale:' || s.id AS id,
                        'sale_' || s.sale_type AS kind,
                        CASE s.sale_type
                            WHEN 'gold' THEN 'Venda de gold'
                            WHEN 'pve_bag' THEN 'Venda de Saco PvE'
                            ELSE 'Venda de item'
                        END AS title,
                        COALESCE(s.item_description, s.buyer_reference) AS detail,
                        s.sold_at AS occurred_at,
                        s.gold_quantity AS gold_amount,
                        CASE WHEN s.sale_type = 'pve_bag' THEN s.item_quantity ELSE NULL END
                            AS pve_bags,
                        s.real_amount_minor AS amount_minor
                    FROM sales s
                    WHERE s.workspace_id = ? AND s.deleted_at IS NULL

                    UNION ALL

                    SELECT
                        'expense:' || t.id AS id,
                        'expense' AS kind,
                        CASE t.category
                            WHEN 'upgrade' THEN 'Despesa · Melhoria'
                            WHEN 'consumable' THEN 'Despesa · Consumível'
                            WHEN 'service' THEN 'Despesa · Serviço'
                            ELSE 'Despesa · Outro'
                        END AS title,
                        t.description AS detail,
                        t.occurred_at AS occurred_at,
                        t.amount_gold AS gold_amount,
                        NULL AS pve_bags,
                        NULL AS amount_minor
                    FROM transactions t
                    WHERE t.workspace_id = ? AND t.type = 'expense'
                      AND t.category IN ('upgrade', 'consumable', 'service', 'other')
                      AND t.deleted_at IS NULL
                ) movements
                WHERE occurred_at IS NOT NULL
                ORDER BY occurred_at DESC
                LIMIT 12
                """,
                (workspace_id, workspace_id, workspace_id, workspace_id),
            ).fetchall()
            recent_movements = tuple(
                RecentMovement(
                    id=str(row["id"]),
                    kind=str(row["kind"]),
                    title=str(row["title"]),
                    detail=str(row["detail"]) if row["detail"] is not None else None,
                    occurred_at=datetime.fromisoformat(str(row["occurred_at"])),
                    gold_amount=Gold(int(row["gold_amount"]))
                    if row["gold_amount"] is not None
                    else None,
                    pve_bags=int(row["pve_bags"]) if row["pve_bags"] is not None else None,
                    amount_minor=(
                        int(row["amount_minor"]) if row["amount_minor"] is not None else None
                    ),
                )
                for row in recent_movement_rows
            )

            week_start = reference_date - timedelta(days=reference_date.weekday())
            next_week_start = week_start + timedelta(days=7)
            previous_week_start = week_start - timedelta(days=7)
            routine_summary_row = connection.execute(
                f"""SELECT
                    COALESCE(SUM(CASE WHEN finished_at >= ? AND finished_at < ?
                        THEN accumulated_seconds ELSE 0 END), 0) AS month_seconds,
                    COALESCE(SUM(CASE WHEN finished_at >= ? AND finished_at < ?
                        THEN accumulated_seconds ELSE 0 END), 0) AS week_seconds,
                    COALESCE(SUM(CASE WHEN finished_at >= ? AND finished_at < ?
                        THEN accumulated_seconds ELSE 0 END), 0) AS previous_week_seconds,
                    COALESCE(SUM(CASE WHEN finished_at >= ? AND finished_at < ?
                        THEN 1 ELSE 0 END), 0) AS month_session_count,
                    COUNT(DISTINCT CASE WHEN finished_at >= ? AND finished_at < ?
                        THEN substr(finished_at, 1, 10) END) AS active_days
                FROM work_routine_sessions
                WHERE workspace_id = ? AND status = 'completed' AND deleted_at IS NULL
                  AND accumulated_seconds >= {MIN_RECORDED_ROUTINE_SECONDS}""",
                (
                    month_start_str,
                    next_month_start_str,
                    week_start.isoformat(),
                    next_week_start.isoformat(),
                    previous_week_start.isoformat(),
                    week_start.isoformat(),
                    month_start_str,
                    next_month_start_str,
                    month_start_str,
                    next_month_start_str,
                    workspace_id,
                ),
            ).fetchone()
            routine_session_rows = connection.execute(
                f"""SELECT id, created_at, finished_at, accumulated_seconds
                FROM work_routine_sessions
                WHERE workspace_id = ? AND status = 'completed'
                  AND finished_at IS NOT NULL AND deleted_at IS NULL
                  AND accumulated_seconds >= {MIN_RECORDED_ROUTINE_SECONDS}
                ORDER BY finished_at DESC
                LIMIT 10""",
                (workspace_id,),
            ).fetchall()
            work_routine_history = WorkRoutineHistory(
                month_seconds=int(routine_summary_row["month_seconds"]),
                week_seconds=int(routine_summary_row["week_seconds"]),
                previous_week_seconds=int(routine_summary_row["previous_week_seconds"]),
                month_session_count=int(routine_summary_row["month_session_count"]),
                active_days_in_month=int(routine_summary_row["active_days"]),
                recent_sessions=tuple(
                    WorkRoutineSessionRow(
                        id=str(row["id"]),
                        started_at=datetime.fromisoformat(str(row["created_at"])),
                        finished_at=datetime.fromisoformat(str(row["finished_at"])),
                        elapsed_seconds=int(row["accumulated_seconds"]),
                    )
                    for row in routine_session_rows
                ),
            )

            # 9. Monthly Target (Meta do Mês)
            target_month = reference_date.strftime("%Y-%m")
            target_row = connection.execute(
                "SELECT target_gold FROM monthly_gold_targets "
                "WHERE workspace_id = ? AND target_month = ? AND deleted_at IS NULL",
                (workspace_id, target_month),
            ).fetchone()
            target_gold = Gold(int(target_row["target_gold"]) if target_row else 25_000_000)
            latest_bag_quote = connection.execute(
                """SELECT mpq.unit_value_gold
                FROM market_price_quotes mpq
                JOIN items i ON i.id = mpq.item_id AND i.name = 'Saco PvE'
                WHERE mpq.workspace_id = ? AND mpq.deleted_at IS NULL AND i.deleted_at IS NULL
                ORDER BY mpq.observed_at DESC, mpq.rowid DESC LIMIT 1""",
                (workspace_id,),
            ).fetchone()
            pve_bag_unit_value = (
                Gold(int(latest_bag_quote["unit_value_gold"])) if latest_bag_quote else None
            )
            pve_bag_value = cur_month_bags * (
                pve_bag_unit_value.amount if pve_bag_unit_value else 0
            )
            current_total_value = cur_month_gold + pve_bag_value
            target_pct = (
                min(100, round((current_total_value / target_gold.amount) * 100))
                if target_gold.amount > 0
                else 0
            )
            rem_gold = max(0, target_gold.amount - current_total_value)
            days_left = max(0, (next_month_start - reference_date).days)
            monthly_target = MonthlyTarget(
                target_month=target_month,
                target_gold=target_gold,
                current_gold=Gold(cur_month_gold),
                current_pve_bags=cur_month_bags,
                pve_bag_unit_value=pve_bag_unit_value,
                current_total_value_gold=Gold(current_total_value),
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
                recent_movements=recent_movements,
                work_routine_history=work_routine_history,
                monthly_target=monthly_target,
                top_characters=top_characters,
                monthly_sales_history=tuple(monthly_sales_history),
            )
        finally:
            connection.close()
