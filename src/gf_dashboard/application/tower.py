from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import date
from uuid import UUID

from gf_dashboard.application.ports import Clock, IdGenerator, TowerUnitOfWork
from gf_dashboard.domain.entities import (
    FarmSession,
    FarmSessionItem,
    FarmSessionParticipant,
    Item,
    TowerSessionDetails,
)
from gf_dashboard.domain.enums import SessionStatus, SessionType
from gf_dashboard.domain.errors import ConflictError, NotFoundError, ValidationError
from gf_dashboard.domain.tower_configuration import (
    MAX_SAFE_INTEGER,
    MAX_TOWER_ITEMS,
    MAX_TOWER_NAME_LENGTH,
    MAX_TOWER_PARTICIPANTS,
    validate_tower_gold,
)
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
    entry_cost: Gold


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
                session.id,
                self._uow.tower_sessions.current_entry_cost(workspace_id),
                False,
                now,
                guild_name_snapshot=guild_name,
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
        idempotency_key: UUID | None = None,
    ) -> TowerRegistrationResult:
        """Persist a completed Tower run, participants and relevant drops atomically."""
        if len(participant_ids) != len(set(participant_ids)):
            raise ValidationError("Participantes da Torre não podem se repetir")
        if len(participant_ids) > MAX_TOWER_PARTICIPANTS or len(drops) > MAX_TOWER_ITEMS:
            raise ValidationError("A Torre aceita até 100 personagens e 100 drops")
        guild_name = guild_name.strip() or None if guild_name is not None else None
        if guild_name is not None and len(guild_name) > MAX_TOWER_NAME_LENGTH:
            raise ValidationError("Nome da guilda deve ter até 120 caracteres")
        for candidate in drops:
            if (
                not candidate.item_name.strip()
                or len(candidate.item_name.strip()) > MAX_TOWER_NAME_LENGTH
            ):
                raise ValidationError("Nome do drop deve ter entre 1 e 120 caracteres")
            if (
                isinstance(candidate.quantity, bool)
                or not isinstance(candidate.quantity, int)
                or not 1 <= candidate.quantity <= MAX_SAFE_INTEGER
            ):
                raise ValidationError("Quantidade do drop deve ser um inteiro positivo seguro")
            if candidate.estimated_unit_value is not None:
                validate_tower_gold(candidate.estimated_unit_value.amount)
        fingerprint = hashlib.sha256(
            json.dumps(
                [
                    activity_date.isoformat(),
                    guild_name,
                    [str(value) for value in participant_ids],
                    [
                        [
                            drop.item_name.strip(),
                            drop.quantity,
                            drop.estimated_unit_value.amount
                            if drop.estimated_unit_value is not None
                            else None,
                        ]
                        for drop in drops
                    ],
                ],
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        now = self._clock.now()
        with self._uow:
            if idempotency_key is not None:
                prior = self._uow.tower_sessions.registration_request(
                    workspace_id, str(idempotency_key)
                )
                if prior is not None:
                    if prior[0] != fingerprint:
                        raise ConflictError("Chave de idempotência já usada com outra sessão")
                    existing = self._uow.tower_sessions.get(workspace_id, prior[1])
                    if existing is None:
                        raise NotFoundError("Sessão da Torre não encontrada")
                    prior_session, prior_details, prior_participants = existing
                    return TowerRegistrationResult(
                        prior_session,
                        prior_participants,
                        self._uow.tower_sessions.list_drops(workspace_id, prior_session.id),
                        prior_details.entry_cost,
                    )
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
                self._uow.tower_sessions.current_entry_cost(workspace_id),
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

            if idempotency_key is not None:
                self._uow.tower_sessions.save_registration_request(
                    workspace_id, str(idempotency_key), fingerprint, session.id, now
                )
            return TowerRegistrationResult(
                session, participants, tuple(recorded_drops), details.entry_cost
            )
