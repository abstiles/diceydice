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


def format_roll(roll: DiceGroup, fmt: Formatter) -> str:
    def should_bold(die: DiceComputation) -> bool:
        if not isinstance(die, DieRoll):
            return False
        return bool(transformed_value) and die.is_crit

    def format_die(die: DiceComputation) -> str:
        if isinstance(die, DiceGroup) and len(die) > 1:
            if not str(die).endswith(')'):
                return f'({die})'
            return str(die)
        return str(die)

    separator = ' + '
    if not roll.transformer:
        return separator.join(map(str, roll.dice))

    dice = []
    for die, transformed_value in zip(roll.dice, roll.transformer(roll.dice)):
        is_selected = _real_int(transformed_value)
        die_str = f"[{die}]" if is_selected else str(die)
        dice += [
            fmt.bold(die_str) if should_bold(die) else die_str
        ]
    dice_str = separator.join(dice)
    return f'{roll.transformer}({dice_str})'


def _real_int(value: complex) -> int:
    return int(complex(value).real)
