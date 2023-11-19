from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, Iterable, Protocol, TypeAlias

from . import lexer
from .lexer import Token

Number: TypeAlias = int | complex
BinaryOperator: TypeAlias = Callable[['Expression', 'Expression'], 'Expression']

PRECEDENCE = {
    '+': 1,
    '-': 1,
    '()': 10,
}

class Expression:
    def __add__(self, other: 'Expression') -> 'AddExpr':
        return AddExpr(self, other)

    def __sub__(self, other: 'Expression') -> 'SubExpr':
        return SubExpr(self, other)

    @property
    def precedence(self) -> int:
        return PRECEDENCE['()']


class InfixOperator(Protocol):
    @property
    def symbol(self) -> str: ...
    def __call__(self, lhs: Expression, rhs: Expression) -> Expression: ...


class Add:
    symbol = '+'
    def __call__(self, lhs: Expression, rhs: Expression) -> Expression:
        return lhs + rhs


class Sub:
    symbol = '-'
    def __call__(self, lhs: Expression, rhs: Expression) -> Expression:
        return lhs - rhs


@dataclass(frozen=True)
class AddExpr(Expression):
    lhs: Expression
    rhs: Expression

    def __str__(self) -> str:
        result = str(self.lhs) if self.lhs.precedence >= self.precedence else f'({self.lhs})'
        result += ' + '
        result += str(self.rhs) if self.rhs.precedence > self.precedence else  f'({self.rhs})'
        return result

    @property
    def precedence(self) -> int:
        return PRECEDENCE['+']


@dataclass(frozen=True)
class SubExpr(Expression):
    lhs: Expression
    rhs: Expression

    def __str__(self) -> str:
        result = str(self.lhs) if self.lhs.precedence >= self.precedence else f'({self.lhs})'
        result += ' - '
        result += str(self.rhs) if self.rhs.precedence > self.precedence else  f'({self.rhs})'
        return result

    @property
    def precedence(self) -> int:
        return PRECEDENCE['-']


@dataclass
class DiceExpr(Expression):
    count: int
    sides: int

    def __str__(self) -> str:
        return f'{self.count}d{self.sides}'


@dataclass
class ConstantExpr(Expression):
    value: int

    def __str__(self) -> str:
        return str(self.value)


class ParseState(Enum):
    OPERATOR_PENDING = auto()
    EXPRESSION_PENDING = auto()


class ParseStateMachine:
    def __init__(self, start: ParseState):
        self._state = start

    @property
    def state(self) -> ParseState:
        return self._state

    def expect_operator(self) -> None:
        self.to(ParseState.OPERATOR_PENDING)

    def expect_expression(self) -> None:
        self.to(ParseState.EXPRESSION_PENDING)

    def to(self, new_state: ParseState) -> 'ParseStateMachine':
        allowed_transitions = {
            ParseState.OPERATOR_PENDING: {ParseState.EXPRESSION_PENDING},
            ParseState.EXPRESSION_PENDING: {ParseState.OPERATOR_PENDING},
        }
        if new_state not in allowed_transitions[self.state]:
            raise Exception(f'Cannot transition from {self.state} to {new_state}')
        self._state = new_state
        return self


def parse_tokens(tokens: Iterable[Token]) -> Expression:
    return _consume_token_list([*tokens])


def _consume_token_list(tokens: list[Token]) -> Expression:
    state = ParseStateMachine(start=ParseState.EXPRESSION_PENDING)
    operator: InfixOperator | None = None
    exprs = []

    while tokens:
        match tokens.pop(0):
            case Token.GROUP_START:
                exprs.append(_consume_token_list(tokens))
                state.expect_operator()
            case Token.GROUP_END:
                state.expect_expression()
                break
            case lexer.Dice(count=count, sides=sides):
                exprs.append(DiceExpr(count, sides))
                state.expect_operator()
            case lexer.Literal(value=value):
                exprs.append(ConstantExpr(value))
                state.expect_operator()
            case Token.ADD:
                operator = Add()
                state.expect_expression()
            case Token.SUB:
                operator = Sub()
                state.expect_expression()
            case _:
                raise Exception("ohno")

        if operator is not None and len(exprs) > 1:
            rhs, lhs = exprs.pop(), exprs.pop()
            exprs.append(operator(lhs, rhs))

    result = exprs.pop()
    if exprs:
        raise Exception(f'Parsing error {exprs!r}, {result}')
    return result
