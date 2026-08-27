from __future__ import annotations

from dataclasses import dataclass

from gf_dashboard.domain.entities import ActivityRuleVersion
from gf_dashboard.domain.value_objects import Gold


@dataclass(frozen=True, slots=True)
class DungeonEstimate:
    gold: Gold
    pve_bags: int
    pve_bag_market_value: Gold | None


def estimate_selected_dungeons(
    rules: tuple[ActivityRuleVersion, ...], pve_bag_unit_value: Gold | None = None
) -> DungeonEstimate:
    """Project predictable dungeon gold and, separately, optional PvE-bag market value."""
    total_gold = Gold(0)
    total_bags = 0
    for rule in rules:
        reward = rule.reward_for_runs(rule.target_amount)
        total_gold += reward.gold
        total_bags += reward.pve_bags
    bag_market_value = pve_bag_unit_value.times(total_bags) if pve_bag_unit_value else None
    return DungeonEstimate(total_gold, total_bags, bag_market_value)
