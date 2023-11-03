from heapq import nlargest, nsmallest
from itertools import repeat
from random import randrange
from typing import Callable, Iterable, Iterator, SupportsInt, Union

from typing_extensions import TypeAlias

from .parser import Dice, KeepHighest, KeepLowest, PostfixOperator, Token

ParseNode: TypeAlias = Union[Token, 'DiceComputation']
Selector: TypeAlias = Callable[[Iterable['DiceComputation']], list['DiceComputation']]


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
    def value(self) -> int:
        return NotImplemented

    def __int__(self) -> int:
        return self.value()

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
        self.result = result

    @property
    def is_crit(self) -> bool:
        return self.sides == self.result

    def value(self) -> int:
        return self.result

    def __str__(self) -> str:
        return str(int(self))

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


class DiceResult(DiceComputation):
    def __init__(
            self, dice: Iterable[DiceComputation],
            selector: Selector = DiceSelector.all()
    ):
        self.dice = list(dice)
        self.selector = selector

    def highest(self, count: int = 1) -> "DiceResult":
        return HighestDice(self.dice, count)

    def lowest(self, count: int = 1) -> "DiceResult":
        return LowestDice(self.dice, count)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.dice == other.dice

    def __len__(self) -> int:
        return len(self.dice)

    def __str__(self) -> str:
        if len(self.dice) == 1:
            return str(self.dice[0])
        return '(' + ' + '.join(map(str, self.dice)) + ')'

    def __repr__(self) -> str:
        return f'DiceResult({self.dice!r})'

    def __add__(self, other: DiceComputation) -> 'DiceResult':
        if isinstance(other, DiceResult):
            # Don't create a new DiceResult group for trivial (0 or 1 dice)
            # cases.
            if len(self) <= 1 or len(other) <= 1:
                return DiceResult(self.dice + other.dice)
            return DiceResult([self, other])
        return DiceResult(self.dice + [other])

    def __radd__(self, other: DiceComputation) -> 'DiceResult':
        return self + other

    def __iter__(self) -> Iterator[DiceComputation]:
        return iter(self.selector(self.dice))

    def value(self) -> int:
        roll_values = map(int, self.selector(self.dice))
        return sum(roll_values)


class HighestDice(DiceResult):
    def __init__(self, dice: Iterable[DiceComputation], count: int):
        super().__init__(dice)
        self.count = count
        self.selector = DiceSelector.highest(count)

    def __str__(self) -> str:
        dice = ', '.join(map(str, self.dice))
        if self.count == 1:
            return f'highest({dice})'
        kept = ' + '.join(map(str, self))
        return f'({kept}) <= high[{self.count}]({dice})'

    def __repr__(self) -> str:
        return f'HighestDice({self.dice!r}, count={self.count})'

    def __add__(self, other: DiceComputation) -> DiceResult:
        if isinstance(other, DiceResult):
            if len(other) == 0:
                return self
            if len(self) == 0:
                return other
        return DiceResult([self, other])

    def __radd__(self, other: DiceComputation) -> DiceResult:
        if isinstance(other, DiceResult):
            if len(other) == 0:
                return self
            if len(self) == 0:
                return other
        return DiceResult([other, self])



class LowestDice(DiceResult):
    def __init__(self, dice: Iterable[DiceComputation], count: int):
        super().__init__(dice)
        self.count = count
        self.selector = DiceSelector.lowest(count)

    def __str__(self) -> str:
        dice = ', '.join(map(str, self.dice))
        if self.count == 1:
            return f'lowest({dice})'
        kept = ' + '.join(map(str, self))
        return f'({kept}) <= low[{self.count}]({dice})'

    def __repr__(self) -> str:
        return f'LowestDice({self.dice!r}, count={self.count})'

    def __add__(self, other: DiceComputation) -> DiceResult:
        if isinstance(other, DiceResult):
            if len(other) == 0:
                return self
            if len(self) == 0:
                return other
        return DiceResult([self, other])

    def __radd__(self, other: DiceComputation) -> DiceResult:
        if isinstance(other, DiceResult):
            if len(other) == 0:
                return self
            if len(self) == 0:
                return other
        return DiceResult([other, self])


class DiceRoller:
    def __init__(self, rng: Callable[[int], int]):
        self.rng = rng

    def roll(self, sides: int) -> DieRoll:
        return DieRoll(sides=sides, result=self.rng(sides))

    def evaluate(self, tokens: Iterable[Token]) -> DiceResult:
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
            elif isinstance(token, PostfixOperator):
                context.append(self.apply_postfix(context.pop(), token))

        return self.evaluate_group(context)

    def apply_postfix(
            self, node: ParseNode, postfix: PostfixOperator
    ) -> DiceResult:
        if not isinstance(node, DiceResult):
            raise ValueError(
                f'{postfix} operator must follow dice roll or group'
            )
        last_result: DiceResult = node
        if isinstance(postfix, KeepHighest):
            return last_result.highest(postfix.count)
        if isinstance(postfix, KeepLowest):
            return last_result.lowest(postfix.count)
        raise ValueError(f'Unhandled postfix operator {postfix!r}')

    def evaluate_group(self, nodes: Iterable[ParseNode]) -> DiceResult:
        result = DiceResult([])
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
        return DiceResult(map(self.roll, rolls))


def random_roll(sides: int) -> int:
    return randrange(sides) + 1


evaluate = DiceRoller(random_roll).evaluate
