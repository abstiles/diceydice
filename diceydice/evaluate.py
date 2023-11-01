from dataclasses import dataclass
from itertools import repeat
from random import randrange
from typing import Callable, Iterable, Union

from typing_extensions import TypeAlias

from .parser import Dice, Token

ParseNode: TypeAlias = Union[Token, 'DiceResult']


@dataclass(frozen=True)
class DieResult:
    sides: int
    result: int

    def __str__(self) -> str:
        return f'1d{self.sides}({self.result})'


class DiceResult:
    def __init__(self, dice: Iterable[DieResult]):
        self.dice = list(dice)

    def __len__(self) -> int:
        return len(self.dice)

    def __str__(self) -> str:
        return ' + '.join(map(str, self.dice))

    def __repr__(self) -> str:
        return f'DiceResult({self.dice!r})'

    def __add__(self, other: 'DiceResult') -> 'DiceResult':
        return DiceResult(self.dice + other.dice)

    def value(self) -> int:
        return sum(die.result for die in self.dice)


class DiceRoller:
    def __init__(self, rng: Callable[[int], int]):
        self.rng = rng

    def roll(self, sides: int) -> DieResult:
        result = self.rng(sides)
        return DieResult(sides, result)

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

        return self.evaluate_group(context)

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
