from heapq import nlargest, nsmallest
from itertools import repeat
from random import randrange
from typing import Callable, Iterable, Iterator, SupportsInt, TypeVar, Union

from typing_extensions import TypeAlias

from .parser import (
    Combat, Dice, KeepHighest, KeepLowest, PostfixOperator, Token
)

T = TypeVar('T')
Number: TypeAlias = Union[int, complex]
ParseNode: TypeAlias = Union[Token, 'DiceComputation']
Selector: TypeAlias = Callable[[Iterable['DiceComputation']], list['DiceComputation']]

# U+1F4A5 is the "collision symbol" emoji.
EFFECT_SYMBOL = "\U0001f4a5"


class DiceSelector:
    @staticmethod
    def highest(count: int = 1) -> Selector:
        def selector(rolls: Iterable[DiceComputation]) -> list[DiceComputation]:
            return nlargest(count, rolls)
        return selector

    @staticmethod
    def lowest(count: int = 1) -> Selector:
        def selector(rolls: Iterable[DiceComputation]) -> list[DiceComputation]:
            return nsmallest(count, rolls)
        return selector

    @staticmethod
    def all() -> Selector:
        return list


class DiceComputation:
    def value(self) -> Number:
        return 0

    @property
    def result(self) -> int:
        return int(self)

    @property
    def effects(self) -> int:
        return int(complex(self.value()).imag)

    def __int__(self) -> int:
        # Just get the real component if value is complex.
        return int(complex(self.value()).real)

    def __str__(self) -> str:
        return str(int(self))

    def __repr__(self) -> str:
        return 'DiceComputation()'

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, SupportsInt):
            return NotImplemented
        return int(self) < int(other)

    def __le__(self, other: object) -> bool:
        if not isinstance(other, SupportsInt):
            return NotImplemented
        return int(self) <= int(other)

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, SupportsInt):
            return NotImplemented
        return int(self) > int(other)

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, SupportsInt):
            return NotImplemented
        return int(self) >= int(other)


class DieRoll(DiceComputation):
    def __init__(self, sides: int, result: int):
        self.sides = sides
        self._result = result

    @property
    def is_crit(self) -> bool:
        return self.sides == self._result

    def value(self) -> int:
        return self._result

    def __repr__(self) -> str:
        return f'DieRoll(sides={self.sides}, result={self.result})'

    def __add__(self, other: object) -> int:
        if not isinstance(other, SupportsInt):
            return NotImplemented
        return int(self) + int(other)

    def __radd__(self, other: object) -> int:
        return self + other

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DieRoll):
            return False
        return (self.sides, self.result) == (other.sides, other.result)


class CombatDieRoll(DiceComputation):
    def __init__(self, result: int, effect: bool = False):
        self._result = result
        self.effect = effect

    def value(self) -> complex:
        return self._result + (1j if self.effect else 0)

    def __str__(self) -> str:
        return EFFECT_SYMBOL if self.effect else str(self.result)

    def __repr__(self) -> str:
        return f'CombatDieRoll(result={self.result}, effect={self.effect})'

    @classmethod
    def from_d6(cls, roll: DieRoll) -> 'CombatDieRoll':
        if roll.sides != 6:
            raise ValueError("Can't create combat die from non-d6")
        return (
            CombatDieRoll(1) if roll.result == 1
            else CombatDieRoll(2) if roll.result == 2
            else CombatDieRoll(0) if roll.result in (3, 4)
            else CombatDieRoll(1, effect=True)
        )


class DiceSum(DiceComputation):
    def __init__(self, dice: Iterable[DiceComputation]):
        self.dice = list(dice)

    def highest(self, count: int = 1) -> "DiceSum":
        return HighestDice(self.dice, count)

    def lowest(self, count: int = 1) -> "DiceSum":
        return LowestDice(self.dice, count)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.dice == other.dice

    def __len__(self) -> int:
        return len(self.dice)

    @staticmethod
    def fmt_die(die: DiceComputation) -> str:
        if isinstance(die, DiceSum) and len(die) > 1:
            if not str(die).endswith(')'):
                return f'({die})'
            return str(die)
        return str(die)

    def __str__(self) -> str:
        if len(self.dice) == 1:
            return str(self.dice[0])
        return ' + '.join(map(self.fmt_die, self.dice))

    def __repr__(self) -> str:
        return f'DiceSum({self.dice!r})'

    def __add__(self, other: DiceComputation) -> 'DiceSum':
        if isinstance(other, DiceSum):
            # Don't create a new DiceSum group for trivial (0 or 1 dice)
            # cases.
            if len(self) <= 1 or len(other) <= 1:
                return DiceSum(self.dice + other.dice)
            return DiceSum([self, other])
        return DiceSum(self.dice + [other])

    def __radd__(self, other: DiceComputation) -> 'DiceSum':
        return self + other

    def __iter__(self) -> Iterator[DiceComputation]:
        return iter(self.dice)

    def value(self) -> Number:
        roll_values = (die.value() for die in self.dice)
        return sum(roll_values)


class FilteredDice(DiceSum):
    def __init__(
            self, dice: Iterable[DiceComputation],
            name: str, selector: Selector, count: int):
        super().__init__(dice)
        self.name = name
        self.selector = selector
        self.count = count

    def __iter__(self) -> Iterator[DiceComputation]:
        return iter(self.kept())

    def value(self) -> Number:
        roll_values = (die.value() for die in self.kept())
        return sum(roll_values)

    def kept(self) -> list[DiceComputation]:
        return self.selector(self.dice)

    def kept_indexes(self) -> Iterable[int]:
        kept_dice = self.kept()
        for idx, die in enumerate(self.dice):
            if die in kept_dice:
                yield idx
                kept_dice.remove(die)

    def __str__(self) -> str:
        dice_str = ''
        kept_indexes = set(self.kept_indexes())
        for idx, die in enumerate(self.dice):
            dice_str += ', ' if idx else ''
            dice_str += f"[{die}]" if idx in kept_indexes else str(die)
        if self.count == 1:
            return f'{self.name}({dice_str})'
        return f'{self.name}[{self.count}]({dice_str})'

    def __add__(self, other: DiceComputation) -> DiceSum:
        if isinstance(other, DiceSum):
            if len(other) == 0:
                return self
            if len(self) == 0:
                return other
        return DiceSum([self, other])

    def __radd__(self, other: DiceComputation) -> DiceSum:
        if isinstance(other, DiceSum):
            if len(other) == 0:
                return self
            if len(self) == 0:
                return other
        return DiceSum([other, self])


class HighestDice(FilteredDice):
    def __init__(self, dice: Iterable[DiceComputation], count: int):
        super().__init__(dice, "high", DiceSelector.highest(count), count)

    def __repr__(self) -> str:
        return f'HighestDice({self.dice!r}, count={self.count})'


class LowestDice(FilteredDice):
    def __init__(self, dice: Iterable[DiceComputation], count: int):
        super().__init__(dice, "low", DiceSelector.lowest(count), count)

    def __repr__(self) -> str:
        return f'LowestDice({self.dice!r}, count={self.count})'


class DiceRoller:
    def __init__(self, rng: Callable[[int], int]):
        self.rng = rng

    def roll(self, sides: int) -> DieRoll:
        return DieRoll(sides=sides, result=self.rng(sides))

    def evaluate(self, tokens: Iterable[Token]) -> DiceComputation:
        return self.eval_summation(tokens)

    def eval_summation(self, tokens: Iterable[Token]) -> DiceSum:
        context: list[ParseNode] = []
        for token in tokens:
            if token is Token.GROUP_START:
                context.append(token)
            elif token is Token.GROUP_END:
                current_group: list[ParseNode] = []
                while (last_token := context.pop()) is not Token.GROUP_START:
                    current_group.append(last_token)
                context.append(self.evaluate_group(reversed(current_group)))
            elif isinstance(token, Dice):
                context.append(self.evaluate_dice(token))
            elif isinstance(token, Combat):
                context.append(self.evaluate_combat(token))
            elif isinstance(token, PostfixOperator):
                context.append(self.apply_postfix(context.pop(), token))

        return self.evaluate_group(context)

    def apply_postfix(
            self, node: ParseNode, postfix: PostfixOperator
    ) -> DiceSum:
        if not isinstance(node, DiceSum):
            raise ValueError(
                f'{postfix} operator must follow dice roll or group'
            )
        last_result: DiceSum = node
        if isinstance(postfix, KeepHighest):
            return last_result.highest(postfix.count)
        if isinstance(postfix, KeepLowest):
            return last_result.lowest(postfix.count)
        raise ValueError(f'Unhandled postfix operator {postfix!r}')

    def evaluate_group(self, nodes: Iterable[ParseNode]) -> DiceSum:
        result = DiceSum([])
        for node in nodes:
            if isinstance(node, Dice):
                result += self.evaluate_dice(node)
            elif isinstance(node, DiceComputation):
                result += node
            elif node is Token.ADD:
                continue
            else:
                raise ValueError(f'Illegal token "{node}" in group')
        return result

    def evaluate_dice(self, dice: Dice) -> DiceComputation:
        rolls = repeat(dice.sides, dice.count)
        return DiceSum(map(self.roll, rolls))

    def evaluate_combat(self, dice: Combat) -> DiceComputation:
        rolls = repeat(6, dice.count)
        d6_rolls = map(self.roll, rolls)
        return DiceSum(map(CombatDieRoll.from_d6, d6_rolls))


def random_roll(sides: int) -> int:
    return randrange(sides) + 1


evaluate = DiceRoller(random_roll).evaluate
