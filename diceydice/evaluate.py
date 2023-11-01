from heapq import nlargest, nsmallest
from itertools import repeat
from random import randrange
from typing import Callable, Iterable, Iterator, Union

from typing_extensions import TypeAlias

from .parser import Dice, KeepHighest, KeepLowest, PostfixOperator, Token

ParseNode: TypeAlias = Union[Token, 'DiceResult']
Selector: TypeAlias = Callable[[Iterable['DieResult']], list['DieResult']]


class DiceSelector:
    @staticmethod
    def highest(count: int = 1) -> Selector:
        def selector(rolls: Iterable[DieResult]) -> list[DieResult]:
            return nlargest(count, rolls, key=DieResult.value)
        return selector

    @staticmethod
    def lowest(count: int = 1) -> Selector:
        def selector(rolls: Iterable[DieResult]) -> list[DieResult]:
            return nsmallest(count, rolls, key=DieResult.value)
        return selector

    @staticmethod
    def all() -> Selector:
        return list


class DieResult:
    def __init__(self, result: int, sides: int):
        self.result = result
        self.sides = sides

    def __str__(self) -> str:
        return f'd{self.sides}({self.result})'

    def __repr__(self) -> str:
        return f'DieResult({self.result}, {self.sides})'

    @staticmethod
    def value(die_result: "DieResult") -> int:
        return die_result.result


class DiceResult:
    def __init__(
            self, dice: Iterable[DieResult],
            selector: Selector = DiceSelector.all()
    ):
        self.dice = list(dice)
        self.selector = selector

    def highest(self, count: int) -> "DiceResult":
        return self.select(DiceSelector.highest(count))

    def lowest(self, count: int) -> "DiceResult":
        return self.select(DiceSelector.lowest(count))

    def select(self, selector: Selector) -> "DiceResult":
        return DiceResult(self.dice, selector)

    def __len__(self) -> int:
        return len(self.dice)

    def __str__(self) -> str:
        return ' + '.join(map(str, self.dice))

    def __repr__(self) -> str:
        return f'DiceResult({self.dice!r})({self.selector(self.dice)})'

    def __add__(self, other: 'DiceResult') -> 'DiceResult':
        if len(self) == 0:
            return other
        if len(other) == 0:
            return self
        return DiceResult(list(self) + list(other))

    def __iter__(self) -> Iterator[DieResult]:
        return iter(self.selector(self.dice))

    def value(self) -> int:
        return sum(die.result for die in self.selector(self.dice))


class DiceRoller:
    def __init__(self, rng: Callable[[int], int]):
        self.rng = rng

    def roll(self, sides: int) -> DieResult:
        result = self.rng(sides)
        return DieResult(result, sides)

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
