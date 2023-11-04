from .evaluate import DiceComputation, evaluate
from .parser import tokenize


class Formatter:
    def bold(self, text: object) -> str:
        return str(text)


class MarkdownFormatter(Formatter):
    def bold(self, text: object) -> str:
        return f'**{text}**'


class AnsiFormatter(Formatter):
    def bold(self, text: object) -> str:
        return(f"\033[1m{text}\033[0m")


PLAIN = Formatter()
MARKDOWN = MarkdownFormatter()
ANSI = AnsiFormatter()


def eval_expr(dice_expr: str, formatter: Formatter=MARKDOWN) -> str:
    result = evaluate(tokenize(dice_expr))
    return format_result(result, formatter)


def format_result(roll: DiceComputation, fmt: Formatter) -> str:
    return fmt.bold(roll.result) + f' <= {roll}'
