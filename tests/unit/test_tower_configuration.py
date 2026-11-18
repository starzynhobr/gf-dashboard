from __future__ import annotations

from dataclasses import replace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from gf_dashboard.application.tower_configuration import (
    SaveTowerConfiguration,
    TowerConfigurationService,
    TowerItemSetting,
)
from gf_dashboard.domain.errors import ValidationError
from gf_dashboard.domain.tower_configuration import MAX_SAFE_INTEGER, validate_tower_gold
from gf_dashboard.domain.value_objects import EntityId, WorkspaceId


def command() -> SaveTowerConfiguration:
    return SaveTowerConfiguration(
        WorkspaceId(uuid4()),
        uuid4(),
        " Guilda ",
        25_000,
        (EntityId(uuid4()),),
        (TowerItemSetting(" Astúcia ", 200_000),),
    )


def test_configuration_normalizes_input_and_delegates_one_valid_command() -> None:
    store = Mock()
    service = TowerConfigurationService(store)
    initial = command()

    result = service.save(initial)

    normalized, fingerprint = store.save.call_args.args
    assert normalized.guild_name == "Guilda"
    assert normalized.items == (TowerItemSetting("Astúcia", 200_000),)
    assert normalized.participant_ids == initial.participant_ids
    assert len(fingerprint) == 64
    assert result is store.save.return_value


@pytest.mark.parametrize("value", [-1, True, 1.5, MAX_SAFE_INTEGER + 1])
def test_tower_gold_rejects_invalid_or_unsafe_integers(value: int) -> None:
    with pytest.raises(ValidationError):
        validate_tower_gold(value)


def test_zero_and_largest_safe_gold_are_allowed() -> None:
    assert validate_tower_gold(0).amount == 0
    assert validate_tower_gold(MAX_SAFE_INTEGER).amount == MAX_SAFE_INTEGER


@pytest.mark.parametrize(
    "change",
    [
        {"guild_name": "a" * 121},
        {"entry_cost_gold": -1},
        {"items": (TowerItemSetting(" ", None),)},
        {"items": (TowerItemSetting("a" * 121, 1),)},
        {"items": (TowerItemSetting("Astúcia", 1), TowerItemSetting("ASTÚCIA", 2))},
        {"items": (TowerItemSetting("Astúcia", True),)},
        {"items": (TowerItemSetting("Astúcia", MAX_SAFE_INTEGER + 1),)},
        {"items": tuple(TowerItemSetting(str(index), None) for index in range(101))},
    ],
)
def test_invalid_configuration_never_reaches_persistence(change: dict[str, object]) -> None:
    store = Mock()

    with pytest.raises(ValidationError):
        TowerConfigurationService(store).save(replace(command(), **change))

    store.save.assert_not_called()


def test_duplicate_participants_are_rejected() -> None:
    participant = EntityId(uuid4())
    store = Mock()

    with pytest.raises(ValidationError, match="repetir"):
        TowerConfigurationService(store).save(
            replace(command(), participant_ids=(participant, participant))
        )

    store.save.assert_not_called()
