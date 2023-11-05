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
DiceAggregator: TypeAlias = Callable[[Iterable['DiceComputation']], Number]

# U+1F4A5 is the "collision symbol" emoji.
EFFECT_SYMBOL = "\U0001f4a5"


class Selector:
    ALL: 'Selector'
    name = 'all'
    count = 0

    # Select all.
    def __call__(self, rolls: Iterable['DiceComputation']) -> list['DiceComputation']:
        return list(rolls)

    def __bool__(self) -> bool:
        return self.count != 0

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Selector)
            and self.name == other.name
            and self.count == other.count
        )


class Highest(Selector):
    name = 'high'

    def __init__(self, count: int = 1):
        if count < 1:
            raise ValueError("Can't keep less than one die")
        self.count = count

    def __call__(self, rolls: Iterable['DiceComputation']) -> list['DiceComputation']:
        return nlargest(self.count, rolls)


class Lowest(Selector):
    name = 'low'

    def __init__(self, count: int = 1):
        if count < 1:
            raise ValueError("Can't keep less than one die")
        self.count = count

    def __call__(self, rolls: Iterable['DiceComputation']) -> list['DiceComputation']:
        return nsmallest(self.count, rolls)


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


class DiceGroup(DiceComputation):
    def __init__(
            self, dice: Iterable[DiceComputation],
            selector: Selector,
            aggregator: DiceAggregator,
    ):
        self.dice = list(dice)
        self.selector = selector
        self.aggregator = aggregator

    def kept(self) -> list[DiceComputation]:
        return self.selector(self.dice)

    def kept_indexes(self) -> Iterable[int]:
        kept_dice = self.kept()
        for idx, die in enumerate(self.dice):
            if die in kept_dice:
                yield idx
                kept_dice.remove(die)

    def __bool__(self) -> bool:
        return len(self) != 0

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DiceGroup):
            return False
        return self.dice == other.dice and self.value() == other.value()

    def __len__(self) -> int:
        return len(self.dice)

    def __iter__(self) -> Iterator[DiceComputation]:
        return iter(self.kept())

    def __str__(self) -> str:
        return self.fmt_str(', ')

    def __repr__(self) -> str:
        return f'DiceGroup({self.dice!r})'

    def value(self) -> Number:
        return self.aggregator(self.kept())

    @staticmethod
    def add_computation(left: DiceComputation, right: DiceComputation) -> 'DiceGroup':
        # No-ops.
        if not left or not right:
            actual = left or right
            if isinstance(actual, DiceGroup):
                return actual
            return DiceSum([actual])

        # If there's a selector, we cannot generally combine the group with
        # anything. We must create a new group containing both.
        has_selector = (
            isinstance(left, DiceGroup) and left.selector
            or isinstance(right, DiceGroup) and right.selector
        )
        if has_selector:
            return DiceSum([left, right])

        # If both are groups...
        if isinstance(left, DiceGroup) and isinstance(right, DiceGroup):
            # Trivial groups can just be merged.
            if len(left) <= 1 or len(right) <= 1:
                return DiceSum(left.dice + right.dice)
            # Otherwise create a new group to hold both.
            return DiceSum([left, right])

        # If either isn't a group, it's a single computation, which can just be
        # added to the other's list.
        if isinstance(left, DiceGroup):
            return DiceSum(left.dice + [right])
        if isinstance(right, DiceGroup):
            return DiceSum([left] + right.dice)

        raise TypeError(f'Unable to add {type(left)} and {type(right)}')

    def __add__(self, other: DiceComputation) -> 'DiceGroup':
        return self.add_computation(self, other)

    def __radd__(self, other: DiceComputation) -> 'DiceGroup':
        return self.add_computation(other, self)

    @staticmethod
    def fmt_die(die: DiceComputation) -> str:
        if isinstance(die, DiceGroup) and len(die) > 1:
            if not str(die).endswith(')'):
                return f'({die})'
            return str(die)
        return str(die)

    def fmt_str(self, separator: str) -> str:
        if not self.selector:
            return separator.join(map(str, self.dice))

        formatted = ''
        kept_indexes = set(self.kept_indexes())
        for idx, die in enumerate(map(self.fmt_die, self.dice)):
            formatted += separator if idx else ''
            formatted += f"[{die}]" if idx in kept_indexes else die
        if self.selector.count == 1:
            return f'{self.selector.name}({formatted})'
        return f'{self.selector.name}[{self.selector.count}]({formatted})'


class DiceSum(DiceGroup):
    def __init__(
            self, dice: Iterable[DiceComputation],
            selector: Selector = Selector()
    ):
        super().__init__(dice, selector, self.sum_values)

    @staticmethod
    def sum_values(dice: Iterable[DiceComputation]) -> Number:
        roll_values = (die.value() for die in dice)
        return sum(roll_values)

    def highest(self, count: int = 1) -> "DiceSum":
        return HighestDice(self.dice, count)

    def lowest(self, count: int = 1) -> "DiceSum":
        return LowestDice(self.dice, count)

    def __str__(self) -> str:
        return self.fmt_str(' + ')

    def __repr__(self) -> str:
        return f'DiceSum({self.dice!r})'


class HighestDice(DiceSum):
    def __init__(self, dice: Iterable[DiceComputation], count: int):
        super().__init__(dice, Highest(count))

    def __repr__(self) -> str:
        return f'HighestDice({self.dice!r}, count={self.selector.count})'


class LowestDice(DiceSum):
    def __init__(self, dice: Iterable[DiceComputation], count: int):
        super().__init__(dice, Lowest(count))

    def __repr__(self) -> str:
        return f'LowestDice({self.dice!r}, count={self.selector.count})'


class DiceRoller:
    def __init__(self, rng: Callable[[int], int]):
        self.rng = rng

    def roll(self, sides: int) -> DieRoll:
        return DieRoll(sides=sides, result=self.rng(sides))

    def evaluate(self, tokens: Iterable[Token]) -> DiceComputation:
        return self.eval_summation(tokens)

    def eval_summation(self, tokens: Iterable[Token]) -> DiceGroup:
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

    def evaluate_group(self, nodes: Iterable[ParseNode]) -> DiceGroup:
        result: DiceGroup = DiceSum([])
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

    def evaluate_dice(self, dice: Dice) -> DiceSum:
        rolls = repeat(dice.sides, dice.count)
        return DiceSum(map(self.roll, rolls))

    def evaluate_combat(self, dice: Combat) -> DiceSum:
        rolls = repeat(6, dice.count)
        d6_rolls = map(self.roll, rolls)
        return DiceSum(map(CombatDieRoll.from_d6, d6_rolls))


def random_roll(sides: int) -> int:
    return randrange(sides) + 1


evaluate = DiceRoller(random_roll).evaluate
