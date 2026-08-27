from __future__ import annotations

from dataclasses import dataclass

from gf_dashboard.application.catalog import DungeonCatalogService
from gf_dashboard.application.ports import Clock, FarmUnitOfWork, IdGenerator
from gf_dashboard.application.services import WorkspaceService
from gf_dashboard.domain.value_objects import WorkspaceId


@dataclass(frozen=True, slots=True)
class GoldenFixture:
    workspace_id: WorkspaceId
    accounts_count: int
    characters_count: int
    selected_dungeons_per_character: int


def create_golden_fixture(uow: FarmUnitOfWork, ids: IdGenerator, clock: Clock) -> GoldenFixture:
    workspace_service = WorkspaceService(uow, ids, clock)
    workspace = workspace_service.create_workspace("Fixture dourada")
    DungeonCatalogService(uow, ids, clock).seed_confirmed_dungeons(workspace.id)
    with uow:
        activities = uow.activities.list_active(workspace.id)
    for account_number in range(1, 3):
        account = workspace_service.create_account(
            workspace.id, f"Conta {account_number}", "Valhalla"
        )
        for character_number in range(1, 6):
            character = workspace_service.create_character(
                workspace.id,
                account.id,
                f"Star{account_number}{character_number}",
                "Classe",
                91,
                character_number,
            )
            for activity_order, activity in enumerate(activities, start=1):
                workspace_service.configure_character_activity(
                    workspace.id, character.id, activity.id, 5, activity_order
                )
    return GoldenFixture(workspace.id, 2, 10, len(activities))
