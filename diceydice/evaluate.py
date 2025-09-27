import operator
from enum import Enum
from heapq import nlargest, nsmallest
from itertools import compress, repeat
from random import randrange
from typing import (
    Callable,
    cast,
    Iterable,
    Iterator,
    Optional,
    Protocol,
    SupportsInt,
    TypeVar,
    Union,
)

from typing_extensions import TypeAlias

from .exceptions import DiceSyntaxError
from .parser import (
    Combat,
    Constant,
    CritGE,
    CritLE,
    Dice,
    EQ,
    GE,
    GT,
    KeepHighest,
    KeepLowest,
    LE,
    LT,
    PostfixOperator,
    Token,
)

T = TypeVar('T')
Comparator: TypeAlias = Callable[[object, object], bool]
Number: TypeAlias = Union[int, complex]
ParseNode: TypeAlias = Union[Token, 'DiceComputation']

# U+1F4A5 is the "collision symbol" emoji.
EFFECT_SYMBOL = "\U0001f4a5"


class DiceTransformer(Protocol):
    def __call__(self, dice: Iterable['DiceComputation']) -> Iterable[Number]: ...
    def __bool__(self) -> bool: ...


class Selector:
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
            raise DiceSyntaxError("Can't keep less than one die")
        self.count = count

    def __call__(self, rolls: Iterable['DiceComputation']) -> list['DiceComputation']:
        return nlargest(self.count, rolls)


class Lowest(Selector):
    name = 'low'

    def __init__(self, count: int = 1):
        if count < 1:
            raise DiceSyntaxError("Can't keep less than one die")
        self.count = count

    def __call__(self, rolls: Iterable['DiceComputation']) -> list['DiceComputation']:
        return nsmallest(self.count, rolls)


class Operator(Enum):
    GE = ">="
    GT = ">"
    LE = "<="
    LT = "<"
    EQ = "=="

    def __call__(self, left: int, right: int) -> bool:
        map = {
            Operator.EQ: cast(Comparator, operator.eq),
            Operator.GE: cast(Comparator, operator.ge),
            Operator.GT: cast(Comparator, operator.gt),
            Operator.LE: cast(Comparator, operator.le),
            Operator.LT: cast(Comparator, operator.lt),
        }
        return map[self](left, right)


class Threshold(Selector):
    OPER_MAP = {
        Operator.EQ: '=',
        Operator.GE: '≥',
        Operator.GT: '>',
        Operator.LE: '≤',
        Operator.LT: '<',
    }

    def __init__(self, oper: Operator, threshold: int):
        self.name = f'{self.OPER_MAP[oper]}{threshold}'
        self.oper = oper
        self.count = threshold

    def __call__(self, rolls: Iterable['DiceComputation']) -> list['DiceComputation']:
        def test(roll: DiceComputation) -> bool:
            return self.oper(roll.result, self.count)
        return list(filter(test, rolls))


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
        return self._result in (1, self.sides)

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


class Modifier(DiceComputation):
    def __init__(self, value: int):
        self._value = value

    def value(self) -> int:
        return self._value


class DiceGroup(DiceComputation):
    def __init__(
            self, dice: Iterable[DiceComputation],
            transformer: DiceTransformer,
            is_closed: bool = False,
    ):
        self.dice = list(dice)
        self.transformer = transformer
        self.is_closed = is_closed

    def close(self) -> 'DiceGroup':
        return DiceGroup(self.dice, self.transformer, True)

    def kept(self) -> Iterable[DiceComputation]:
        return compress(self.dice, self.transformer(self.dice))

    def kept_indexes(self) -> Iterable[int]:
        for idx, value in enumerate(self.transformer(self.dice)):
            if _real_int(value):
                yield idx

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
        return sum(self.transformer(self.dice))

    @staticmethod
    def add_computation(left: DiceComputation, right: DiceComputation) -> 'DiceGroup':
        # No-ops.
        if not left or not right:
            actual = left or right
            if isinstance(actual, DiceGroup):
                return actual
            return DiceSum([actual])

        def is_closed_group(dc: DiceComputation) -> bool:
            return isinstance(dc, DiceGroup) and dc.is_closed

        def dice_list(dc: DiceComputation) -> list[DiceComputation]:
            if isinstance(dc, DiceGroup):
                return dc.dice
            return [dc]

        # When a group is closed, it doesn't merge with another. We only create
        # a new group containing it and whatever else.
        if is_closed_group(left) and is_closed_group(right):
            return DiceSum([left, right])
        elif is_closed_group(left):
            return DiceSum([left] + dice_list(right))
        elif is_closed_group(right):
            return DiceSum(dice_list(left) + [right])

        # If there's a nontrivial transformer, we cannot generally combine the
        # group with anything. We must create a new group containing both.
        has_transformer = (
            isinstance(left, DiceGroup) and left.transformer
            or isinstance(right, DiceGroup) and right.transformer
        )
        if has_transformer:
            return DiceSum([left, right])

        # If both are groups, merge them.
        if isinstance(left, DiceGroup) and isinstance(right, DiceGroup):
            return DiceSum(left.dice + right.dice)

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
        if not self.transformer:
            return separator.join(map(str, self.dice))

        formatted = ''
        kept_indexes = set(self.kept_indexes())
        for idx, die in enumerate(map(self.fmt_die, self.dice)):
            formatted += separator if idx else ''
            formatted += f"[{die}]" if idx in kept_indexes else die
        return f'{self.transformer}({formatted})'


class DiceSum(DiceGroup):
    def __init__(
            self, dice: Iterable[DiceComputation],
            transformer: Optional[DiceTransformer] = None,
            is_closed: bool = False,
    ):
        super().__init__(dice, transformer or IdentityTransformer(), is_closed)

    def close(self) -> 'DiceSum':
        return DiceSum(self.dice, self.transformer, True)

    def keep(self, selector: Selector) -> 'DiceSum':
        transformer = KeepSelected(selector)
        return DiceSum(self.dice, transformer)

    def count(
            self, selector: Selector,
            force_min: Optional[Number] = None,
            force_max: Optional[Number] = None
    ) -> 'DiceSum':
        transformer = CountSelected(selector, force_min, force_max)
        return DiceSum(self.dice, transformer)

    def highest(self, count: int = 1) -> "DiceSum":
        return self.keep(Highest(count))

    def lowest(self, count: int = 1) -> "DiceSum":
        return self.keep(Lowest(count))

    def eq(self, threshold: int) -> 'DiceSum':
        return self.count(Threshold(Operator.EQ, threshold))

    def le(self, threshold: int) -> 'DiceSum':
        return self.count(Threshold(Operator.LE, threshold))

    def crit_le(self, threshold: int) -> 'DiceSum':
        return self.count(Threshold(Operator.LE, threshold), 2, 1j)

    def lt(self, threshold: int) -> 'DiceSum':
        return self.count(Threshold(Operator.LT, threshold))

    def ge(self, threshold: int) -> 'DiceSum':
        return self.count(Threshold(Operator.GE, threshold))

    def crit_ge(self, threshold: int) -> 'DiceSum':
        return self.count(Threshold(Operator.GE, threshold), 1j, 2)

    def gt(self, threshold: int) -> 'DiceSum':
        return self.count(Threshold(Operator.GT, threshold))

    def __str__(self) -> str:
        return self.fmt_str(' + ')

    def __repr__(self) -> str:
        return f'DiceSum(dice={self.dice!r}, transformer={self.transformer!r})'


class KeepSelected:
    def __init__(self, selector: Selector):
        self.selector = selector

    def __bool__(self) -> bool:
        return bool(self.selector)

    def __str__(self) -> str:
        return self.selector.name + (
            f'[{self.selector.count}]' if self.selector.count > 1 else ''
        )

    def __repr__(self) -> str:
        return f'KeepSelected({self.selector!r})'

    def __call__(self, dice: Iterable[DiceComputation]) -> Iterable[Number]:
        kept_dice = self.selector(dice)
        for die in dice:
            if die in kept_dice:
                kept_dice.remove(die)
                yield die.value()
            else:
                yield 0


class IdentityTransformer(KeepSelected):
    def __init__(self) -> None:
        self.selector = Selector()

    def __str__(self) -> str:
        return ''

    def __repr__(self) -> str:
        return 'IdentityTransformer()'


class CountSelected:
    def __init__(
            self, selector: Selector, force_min: Optional[Number] = None,
            force_max: Optional[Number] = None):
        self.selector = selector
        self.force_min = force_min
        self.force_max = force_max

    def __bool__(self) -> bool:
        return bool(self.selector)

    def __str__(self) -> str:
        return self.selector.name

    def __repr__(self) -> str:
        return f'CountSelected({self.selector!r})'

    def override(self, die: DiceComputation) -> Optional[Number]:
        if isinstance(die, DieRoll) and die.is_crit:
            if die.value() == 1:
                return self.force_min
            return self.force_max
        return None

    def __call__(self, dice: Iterable[DiceComputation]) -> Iterable[Number]:
        kept_dice = self.selector(dice)
        for die in dice:
            if die in kept_dice:
                kept_dice.remove(die)
                yield 1 if not (new_value := self.override(die)) else new_value
            else:
                yield 0 if not (new_value := self.override(die)) else new_value


class DiceRoller:
    def __init__(self, rng: Callable[[int], int]):
        self.rng = rng

    def roll(self, sides: int) -> DieRoll:
        return DieRoll(sides=sides, result=self.rng(sides))

    def evaluate(self, tokens: Iterable[Token]) -> DiceGroup:
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
            elif isinstance(token, Constant):
                context.append(Modifier(token.value))

        return self.evaluate_group(context)

    def apply_postfix(
            self, node: ParseNode, postfix: PostfixOperator
    ) -> DiceGroup:
        if not isinstance(node, DiceSum):
            raise DiceSyntaxError(
                f'{postfix} operator must follow dice roll or group'
            )
        last_result: DiceSum = node
        if isinstance(postfix, KeepHighest):
            return last_result.highest(postfix.count)
        if isinstance(postfix, KeepLowest):
            return last_result.lowest(postfix.count)
        if isinstance(postfix, EQ):
            return last_result.eq(postfix.threshold)
        if isinstance(postfix, LE):
            return last_result.le(postfix.threshold)
        if isinstance(postfix, CritLE):
            return last_result.crit_le(postfix.threshold)
        if isinstance(postfix, LT):
            return last_result.lt(postfix.threshold)
        if isinstance(postfix, GE):
            return last_result.ge(postfix.threshold)
        if isinstance(postfix, CritGE):
            return last_result.crit_ge(postfix.threshold)
        if isinstance(postfix, GT):
            return last_result.gt(postfix.threshold)
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
                raise DiceSyntaxError(f'Illegal token "{node}" in group')
        return result.close()

    def evaluate_dice(self, dice: Dice) -> DiceSum:
        rolls = repeat(dice.sides, dice.count)
        return DiceSum(map(self.roll, rolls))

    def evaluate_combat(self, dice: Combat) -> DiceSum:
        rolls = repeat(6, dice.count)
        d6_rolls = map(self.roll, rolls)
        return DiceSum(map(CombatDieRoll.from_d6, d6_rolls))


def random_roll(sides: int) -> int:
    return randrange(sides) + 1


def _real_int(value: Number) -> int:
    return int(complex(value).real)


evaluate = DiceRoller(random_roll).evaluate
