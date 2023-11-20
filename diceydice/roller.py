from dataclasses import dataclass
from random import randrange
from typing import Callable, Protocol, TypeAlias

Number: TypeAlias = int | complex
DieRng: TypeAlias = Callable[[int], int]

# U+1F4A5 is the "collision symbol" emoji.
EFFECT_SYMBOL = "\U0001f4a5"


@dataclass(frozen=True)
class DieRoll:
    value: int
    sides: int

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class CombatDieRoll:
    result: int
    effect: bool = False

    @property
    def value(self) -> complex:
        return self.result + (1j if self.effect else 0)

    def __str__(self) -> str:
        return EFFECT_SYMBOL if self.effect else str(self.result)


@dataclass(frozen=True)
class Constant:
    value: int

    def __str__(self) -> str:
        return str(self.value)


class DiceRoller:
    def __init__(self, roller: DieRng):
        self.roller = roller

    def roll_die(self, sides: int) -> DieRoll:
        return DieRoll(self.roller(sides), sides)

    def roll_combat_die(self) -> CombatDieRoll:
        roll = self.roller(6)
        return (
            CombatDieRoll(1) if roll == 1
            else CombatDieRoll(2) if roll == 2
            else CombatDieRoll(0) if roll in (3, 4)
            else CombatDieRoll(1, effect=True)
        )

    @classmethod
    def random(cls) -> 'DiceRoller':
        def _roll(sides: int) -> int:
            return randrange(sides) + 1
        return cls(_roll)


class Valued(Protocol):
    @property
    def value(self) -> Number: ...


def value(num: Valued) -> Number:
    return num.value
