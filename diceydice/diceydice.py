from .evaluate import DiceResult, evaluate
from .parser import tokenize


def eval_expr(dice_expr: str) -> str:
    result = evaluate(tokenize(dice_expr))
    return format_result(result)


def format_result(roll: DiceResult) -> str:
    return f'{roll.value()} <= {roll}'
