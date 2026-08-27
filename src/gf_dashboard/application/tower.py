from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date

from gf_dashboard.application.ports import Clock, IdGenerator, TowerUnitOfWork
from gf_dashboard.domain.entities import (
    FarmSession,
    FarmSessionItem,
    FarmSessionParticipant,
    Item,
    TowerSessionDetails,
)
from gf_dashboard.domain.enums import SessionStatus, SessionType
from gf_dashboard.domain.errors import NotFoundError, ValidationError
from gf_dashboard.domain.value_objects import EntityId, Gold, WorkspaceId

TOWER_ENTRY_COST = Gold(25_000)


@dataclass(frozen=True, slots=True)
class TowerSessionResult:
    session: FarmSession
    details: TowerSessionDetails
    participants: tuple[FarmSessionParticipant, ...]
    already_completed: bool


@dataclass(frozen=True, slots=True)
class TowerDropInput:
    item_name: str
    quantity: int = 1
    estimated_unit_value: Gold | None = None


@dataclass(frozen=True, slots=True)
class TowerRegistrationResult:
    session: FarmSession
    participants: tuple[FarmSessionParticipant, ...]
    drops: tuple[FarmSessionItem, ...]


class TowerSessionService:
    def __init__(self, uow: TowerUnitOfWork, ids: IdGenerator, clock: Clock) -> None:
        self._uow = uow
        self._ids = ids
        self._clock = clock

    def create(
        self,
        workspace_id: WorkspaceId,
        activity_date: date,
        participant_ids: tuple[EntityId, ...] = (),
        guild_name: str | None = None,
    ) -> TowerSessionResult:
        if len(participant_ids) != len(set(participant_ids)):
            raise ValidationError("Participantes da Torre não podem se repetir")
        now = self._clock.now()
        with self._uow:
            for character_id in participant_ids:
                if self._uow.characters.get(character_id, workspace_id) is None:
                    raise NotFoundError("Participante da Torre não encontrado no workspace")
            session = FarmSession(
                self._ids.new(),
                workspace_id,
                SessionType.TOWER,
                activity_date,
                SessionStatus.PLANNED,
                now,
            )
            details = TowerSessionDetails(
                session.id, TOWER_ENTRY_COST, False, now, guild_name_snapshot=guild_name
            )
            participants = tuple(
                FarmSessionParticipant(session.id, character_id, joined_at=now)
                for character_id in participant_ids
            )
            self._uow.tower_sessions.save(session, details, participants)
            return TowerSessionResult(session, details, participants, False)

    def complete(self, workspace_id: WorkspaceId, session_id: EntityId) -> TowerSessionResult:
        with self._uow:
            current = self._uow.tower_sessions.get(workspace_id, session_id)
            if current is None:
                raise NotFoundError("Sessão da Torre não encontrada")
            session, details, participants = current
            if details.completed:
                return TowerSessionResult(session, details, participants, True)
            now = self._clock.now()
            completed_session = replace(session, status=SessionStatus.COMPLETED, finished_at=now)
            completed_details = replace(details, completed=True, completed_at=now)
            self._uow.tower_sessions.save(completed_session, completed_details, participants)
            return TowerSessionResult(completed_session, completed_details, participants, False)

    def record_drop(
        self,
        workspace_id: WorkspaceId,
        session_id: EntityId,
        item_id: EntityId,
        quantity: int,
        estimated_unit_value: Gold | None = None,
    ) -> FarmSessionItem:
        now = self._clock.now()
        with self._uow:
            if self._uow.tower_sessions.get(workspace_id, session_id) is None:
                raise NotFoundError("Sessão da Torre não encontrada")
            if self._uow.items.get(item_id, workspace_id) is None:
                raise NotFoundError("Item do drop não encontrado no workspace")
            drop = FarmSessionItem(
                self._ids.new(),
                workspace_id,
                session_id,
                item_id,
                quantity,
                now,
                estimated_unit_value,
            )
            self._uow.tower_sessions.add_drop(drop)
            return drop

    def register_completed(
        self,
        workspace_id: WorkspaceId,
        activity_date: date,
        participant_ids: tuple[EntityId, ...] = (),
        guild_name: str | None = None,
        drops: tuple[TowerDropInput, ...] = (),
    ) -> TowerRegistrationResult:
        """Persist a completed Tower run, participants and relevant drops atomically."""
        if len(participant_ids) != len(set(participant_ids)):
            raise ValidationError("Participantes da Torre não podem se repetir")
        now = self._clock.now()
        with self._uow:
            for character_id in participant_ids:
                if self._uow.characters.get(character_id, workspace_id) is None:
                    raise NotFoundError("Participante da Torre não encontrado no workspace")

            session = FarmSession(
                self._ids.new(),
                workspace_id,
                SessionType.TOWER,
                activity_date,
                SessionStatus.COMPLETED,
                now,
                started_at=now,
                finished_at=now,
            )
            details = TowerSessionDetails(
                session.id,
                TOWER_ENTRY_COST,
                True,
                now,
                completed_at=now,
                guild_name_snapshot=guild_name,
            )
            participants = tuple(
                FarmSessionParticipant(session.id, character_id, joined_at=now)
                for character_id in participant_ids
            )
            self._uow.tower_sessions.save(session, details, participants)

            recorded_drops: list[FarmSessionItem] = []
            for raw_drop in drops:
                item_name = raw_drop.item_name.strip()
                if not item_name:
                    raise ValidationError("Nome do drop é obrigatório")
                if raw_drop.quantity <= 0:
                    raise ValidationError("Quantidade do drop deve ser maior que zero")
                item = self._uow.items.get_by_name(workspace_id, item_name)
                if item is None:
                    item = Item(self._ids.new(), workspace_id, item_name, "tower_drop", now)
                    self._uow.items.save(item)
                drop = FarmSessionItem(
                    self._ids.new(),
                    workspace_id,
                    session.id,
                    item.id,
                    raw_drop.quantity,
                    now,
                    raw_drop.estimated_unit_value,
                )
                self._uow.tower_sessions.add_drop(drop)
                recorded_drops.append(drop)

            return TowerRegistrationResult(session, participants, tuple(recorded_drops))
