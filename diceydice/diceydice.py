from typing import Optional

from .evaluate import DiceComputation, DiceGroup, DiceRoller, DieRoll, Modifier, Negative, evaluate
from .parser import tokenize

# Leftwards double arrow symbol.
DOUBLE_ARROW = '\u21d0'

# Left arrow symbol. (Reads better on my terminal.)
ARROW = '\u2b05'

# Triangle symbol.
TRIANGLE = '\u25b2'
INFINITY = '\u221e'

inf = float("inf")


class Formatter:
    def bold(self, text: object) -> str:
        return str(text)

    def underline(self, text: object) -> str:
        return f'[{text}]'

    def arrow(self) -> str:
        return '<='

    def num(self, n: int) -> str:
        return str(int(n))


class MarkdownFormatter(Formatter):
    def bold(self, text: object) -> str:
        return f'**{text}**'

    def underline(self, text: object) -> str:
        return f'__{text}__'

    def arrow(self) -> str:
        return DOUBLE_ARROW

    def num(self, n: int) -> str:
        if n == inf:
            return INFINITY
        elif n == -inf:
            return '-' + INFINITY
        return str(int(n))


class AnsiFormatter(Formatter):
    def bold(self, text: object) -> str:
        return f"\033[1m{text}\033[22m"

    def underline(self, text: object) -> str:
        return f"\033[4m{text}\033[24m"

    def arrow(self) -> str:
        # Gets an extra space because it's wide in a monospace setting.
        return ARROW + ' '

    def num(self, n: int) -> str:
        if n == inf:
            return INFINITY
        elif n == -inf:
            return '-' + INFINITY
        return str(int(n))


PLAIN = Formatter()
MARKDOWN = MarkdownFormatter()
ANSI = AnsiFormatter()


def eval_expr(
        dice_expr: str, formatter: Formatter = MARKDOWN,
        dice_roller: Optional[DiceRoller] = None,
) -> str:
    roll = dice_roller.evaluate if dice_roller else evaluate
    result = roll(tokenize(dice_expr))
    return format_computation(result, formatter)


def format_computation(roll: DiceGroup, fmt: Formatter) -> str:
    return ' '.join([
        format_result(roll, fmt),
        fmt.arrow(),
        format_roll(roll, fmt),
    ])


def format_result(roll: DiceGroup, fmt: Formatter) -> str:
    result = fmt.num(roll.result) + (f'{{{roll.effects}}}' if roll.effects else '')
    return fmt.bold(result)


def format_roll(roll: DiceComputation, fmt: Formatter, inner: bool = False) -> str:
    if not isinstance(roll, DiceGroup) or len(roll) <= 1:
        return str(roll)

    def should_bold(die: DiceComputation) -> bool:
        if isinstance(die, DieRoll):
            return die.is_crit and die.sides > 2
        return False

    def format_die(die: DiceComputation) -> str:
        if isinstance(die, DiceGroup) and len(die) > 1:
            if not str(die).endswith(')'):
                return f'({die})'
            return str(die)
        return str(die)

    def is_negative(die: DiceComputation) -> bool:
        if isinstance(die, Negative):
            return True
        return int(die) < 0

    str_unit = []
    for die, transformed_value in zip(roll.dice, roll.transformer(roll.dice)):
        roll_str = format_roll(die, fmt, inner=True)

        if not str_unit:
            pass
        elif roll.transformer:
            str_unit.append(', ')
        elif is_negative(die):
            str_unit.append(' - ')
            roll_str = roll_str.lstrip('-')
        else:
            str_unit.append(' + ')

        is_selected = bool(roll.transformer) and _real_int(transformed_value)
        if is_selected and should_bold(die):
            str_unit += [fmt.underline(fmt.bold(roll_str))]
        elif is_selected:
            str_unit += [fmt.underline(roll_str)]
        elif should_bold(die):
            str_unit += [fmt.bold(roll_str)]
        else:
            str_unit += [roll_str]
    dice_str = ''.join(str_unit)
    if inner or roll.transformer:
        return f'{roll.transformer}({dice_str})'
    return dice_str


def _real_int(value: complex) -> int:
    return int(complex(value).real)
