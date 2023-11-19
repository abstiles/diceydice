from dataclasses import dataclass
from operator import add, sub
from typing import Iterable, TypeAlias

from . import lexer
from .lexer import Token

Number: TypeAlias = int | complex

PRECEDENCE = {
    '+': 1,
    '-': 1,
    '()': 10,
}

class Expression:
    def __add__(self, other: 'Expression') -> 'Expression':
        if not self:
            return other
        if not other:
            return self
        return AddExpr(self, other)


@dataclass(frozen=True)
class AddExpr(Expression):
    lhs: Expression
    rhs: Expression

    def __repr__(self) -> str:
        return f'AddExpr({self.lhs!r}, {self.rhs!r})'

    def __str__(self) -> str:
        return f'{self.lhs} + {self.rhs}'


@dataclass(frozen=True)
class SubExpr(Expression):
    lhs: Expression
    rhs: Expression

    def __repr__(self) -> str:
        return f'SubExpr({self.lhs!r}, {self.rhs!r})'

    def __str__(self) -> str:
        return f'{self.lhs} - {self.rhs}'


@dataclass
class DiceExpr(Expression):
    count: int
    sides: int


def parse_tokens(tokens: Iterable[Token]) -> Expression:
    return _consume_token_list([*tokens])

def _consume_token_list(tokens: list[Token]) -> Expression:
    expression_pending = None
    operator_pending = None
    while tokens:
        expression = None
        match tokens.pop(0):
            case Token.GROUP_START:
                expression = _consume_token_list(tokens)
            case Token.GROUP_END:
                if operator_pending:
                    raise Exception(
                        f'Unterminated expression {expression_pending} {operator_pending}'
                    )
                return expression_pending
            case lexer.Dice(count=count, sides=sides):
                expression = DiceExpr(count, sides)
            case Token.ADD:
                operator_pending = add
            case Token.SUB:
                operator_pending = sub
            case _:
                raise Exception("ohno")

        if operator_pending and expression_pending and expression:
            expression = operator_pending(expression_pending, expression)
        if expression is not None:
            expression_pending = expression

    return expression_pending
