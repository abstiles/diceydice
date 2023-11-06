from .evaluate import DiceComputation, DiceGroup, DieRoll, evaluate
from .parser import tokenize

# Leftwards double arrow symbol
ARROW = '\u21d0'


class Formatter:
    def bold(self, text: object) -> str:
        return str(text)

    def arrow(self) -> str:
        return '<='


class MarkdownFormatter(Formatter):
    def bold(self, text: object) -> str:
        return f'**{text}**'

    def arrow(self) -> str:
        # Leftwards double arrow symbol.
        return '\u21d0'


class AnsiFormatter(Formatter):
    def bold(self, text: object) -> str:
        return f"\033[1m{text}\033[0m"

    def arrow(self) -> str:
        # Left arrow symbol.
        return '\u2b05 '


PLAIN = Formatter()
MARKDOWN = MarkdownFormatter()
ANSI = AnsiFormatter()


def eval_expr(dice_expr: str, formatter: Formatter = MARKDOWN) -> str:
    result = evaluate(tokenize(dice_expr))
    return format_computation(result, formatter)


def format_computation(roll: DiceGroup, fmt: Formatter) -> str:
    return ' '.join([
        format_result(roll, fmt),
        fmt.arrow(),
        format_roll(roll, fmt),
    ])


def format_result(roll: DiceGroup, fmt: Formatter) -> str:
    result = str(roll.result) + (f'{{{roll.effects}}}' if roll.effects else '')
    return fmt.bold(result)


def format_roll(roll: DiceComputation, fmt: Formatter, inner: bool = False) -> str:
    if not isinstance(roll, DiceGroup):
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

    separator = ', ' if roll.transformer else ' + '
    dice = []
    for die, transformed_value in zip(roll.dice, roll.transformer(roll.dice)):
        if isinstance(die, DiceGroup) and len(die) > 1:
            dice += [format_roll(die, fmt, inner=True)]
            continue
        is_selected = bool(roll.transformer) and _real_int(transformed_value)
        if is_selected and should_bold(die):
            dice += [fmt.bold(f'[{die}]')]
        elif is_selected:
            dice += [fmt.bold('[') + str(die) + fmt.bold(']')]
        elif should_bold(die):
            dice += [fmt.bold(die)]
        else:
            dice += [str(die)]
    dice_str = separator.join(dice)
    if inner or roll.transformer:
        return f'{roll.transformer}({dice_str})'
    return dice_str


def _real_int(value: complex) -> int:
    return int(complex(value).real)
