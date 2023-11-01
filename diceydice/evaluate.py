from heapq import nlargest, nsmallest
from itertools import repeat
from random import randrange
from typing import Callable, Iterable, Iterator, Union

from typing_extensions import TypeAlias

from .parser import Dice, KeepHighest, KeepLowest, PostfixOperator, Token

ParseNode: TypeAlias = Union[Token, 'DiceResult']
Selector: TypeAlias = Callable[[Iterable[int]], list[int]]


class DiceSelector:
    @staticmethod
    def highest(count: int = 1) -> Selector:
        def selector(rolls: Iterable[int]) -> list[int]:
            return nlargest(count, rolls)
        return selector

    @staticmethod
    def lowest(count: int = 1) -> Selector:
        def selector(rolls: Iterable[int]) -> list[int]:
            return nsmallest(count, rolls)
        return selector

    @staticmethod
    def all() -> Selector:
        return list


class DiceResult:
    def __init__(
            self, dice: Iterable[int],
            selector: Selector = DiceSelector.all()
    ):
        self.dice = list(dice)
        self.selector = selector

    def highest(self, count: int = 1) -> "DiceResult":
        return HighestDice(self.dice, count)

    def lowest(self, count: int = 1) -> "DiceResult":
        return LowestDice(self.dice, count)

    def __len__(self) -> int:
        return len(self.dice)

    def __str__(self) -> str:
        return '(' + ' + '.join(map(str, self.dice)) + ')'

    def __repr__(self) -> str:
        return f'DiceResult({self.dice!r})({self.selector(self.dice)})'

    def __add__(self, other: 'DiceResult') -> 'DiceResult':
        if len(self) == 0:
            return other
        if len(other) == 0:
            return self
        return DiceResult(list(self) + list(other))

    def __iter__(self) -> Iterator[int]:
        return iter(self.selector(self.dice))

    def value(self) -> int:
        return sum(self.selector(self.dice))


class HighestDice(DiceResult):
    def __init__(self, dice: Iterable[int], count: int):
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
        return f'HighestDice({self.dice!r}, {self.count})'


class LowestDice(DiceResult):
    def __init__(self, dice: Iterable[int], count: int):
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
        return f'LowestDice({self.dice!r}, {self.count})'


class DiceRoller:
    def __init__(self, rng: Callable[[int], int]):
        self.rng = rng

    def roll(self, sides: int) -> int:
        return self.rng(sides)

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
            elif isinstance(node, DiceResult):
                result += node
            elif node is Token.ADD:
                continue
            else:
                raise ValueError(f'Illegal token "{node}" in group')
        return result

    def evaluate_dice(self, dice: Dice) -> DiceResult:
        rolls = repeat(dice.sides, dice.count)
        return DiceResult(map(self.roll, rolls))


def random_roll(sides: int) -> int:
    return randrange(sides) + 1


evaluate = DiceRoller(random_roll).evaluate
