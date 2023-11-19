from dataclasses import dataclass
from enum import auto, Enum
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
        result = (
            str(self.lhs) if self.lhs.precedence >= self.precedence
            else f'({self.lhs})'
        )
        result += ' + '
        result += (
            str(self.rhs) if self.rhs.precedence > self.precedence
            else f'({self.rhs})'
        )
        return result

    @property
    def precedence(self) -> int:
        return PRECEDENCE['+']


@dataclass(frozen=True)
class SubExpr(Expression):
    lhs: Expression
    rhs: Expression

    def __str__(self) -> str:
        result = (
            str(self.lhs) if self.lhs.precedence >= self.precedence
            else f'({self.lhs})'
        )
        result += ' - '
        result += (
            str(self.rhs) if self.rhs.precedence > self.precedence
            else f'({self.rhs})'
        )
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
class CombatDiceExpr(Expression):
    count: int

    def __str__(self) -> str:
        return f'{self.count}c'


@dataclass
class ConstantExpr(Expression):
    value: int

    def __str__(self) -> str:
        return str(self.value)


@dataclass
class KeepHighestExpr(Expression):
    count: int
    operand: Expression

    def __str__(self) -> str:
        if self.count == 1:
            return f'{self.operand}h'
        return f'{self.operand}h{self.count}'


@dataclass
class KeepLowestExpr(Expression):
    count: int
    operand: Expression

    def __str__(self) -> str:
        if self.count == 1:
            return f'{self.operand}l'
        return f'{self.operand}l{self.count}'


@dataclass
class ThresholdExpr(Expression):
    operator: str
    threshold: int
    crit_threshold: int
    operand: Expression

    def __str__(self) -> str:
        result = f'{self.operand}{self.operator}{self.threshold}'
        if self.crit_threshold > 1:
            result += f'!{self.crit_threshold}'
        return result


class ParseState(Enum):
    START = auto()
    OPERATOR = auto()
    EXPRESSION = auto()
    POSTFIX = auto()


class ParseStateMachine:
    def __init__(self) -> None:
        self._state = ParseState.START

    @property
    def state(self) -> ParseState:
        return self._state

    def expression(self) -> None:
        self.to(ParseState.EXPRESSION)

    def operator(self) -> None:
        self.to(ParseState.OPERATOR)

    def postfix(self) -> None:
        self.to(ParseState.POSTFIX)

    def to(self, new_state: ParseState) -> 'ParseStateMachine':
        allowed_transitions = {
            ParseState.START: {ParseState.EXPRESSION},
            ParseState.EXPRESSION: {
                ParseState.OPERATOR,
                ParseState.POSTFIX,
            },
            ParseState.OPERATOR: {ParseState.EXPRESSION},
            ParseState.POSTFIX: {ParseState.OPERATOR},
        }
        if new_state not in allowed_transitions[self.state]:
            raise Exception(f'Cannot transition from {self.state} to {new_state}')
        self._state = new_state
        return self


def parse_tokens(tokens: Iterable[Token]) -> Expression:
    return _consume_token_list([*tokens])


def _consume_token_list(tokens: list[Token]) -> Expression:
    state = ParseStateMachine()
    operator: InfixOperator | None = None
    exprs = []

    while tokens:
        match tokens.pop(0):
            case Token.GROUP_START:
                state.expression()
                exprs.append(_consume_token_list(tokens))
            case Token.GROUP_END:
                state.operator()
                break
            case lexer.Dice(count=count, sides=sides):
                state.expression()
                exprs.append(DiceExpr(count, sides))
            case lexer.Combat(count=count):
                state.expression()
                exprs.append(CombatDiceExpr(count))
            case lexer.Literal(value=value):
                state.expression()
                exprs.append(ConstantExpr(value))
            case lexer.KeepHighest(count=count):
                state.postfix()
                exprs.append(KeepHighestExpr(count, exprs.pop()))
            case lexer.KeepLowest(count=count):
                state.postfix()
                exprs.append(KeepLowestExpr(count, exprs.pop()))
            case (lexer.CritGE() | lexer.CritLE()) as mod:
                state.postfix()
                exprs.append(ThresholdExpr(mod.oper, mod.threshold, 1, exprs.pop()))
            case (lexer.GE() | lexer.GT() | lexer.LE() | lexer.LT()) as mod:
                state.postfix()
                exprs.append(ThresholdExpr(mod.oper, mod.threshold, 0, exprs.pop()))
            case Token.ADD:
                state.operator()
                operator = Add()
            case Token.SUB:
                state.operator()
                operator = Sub()
            case token:
                raise Exception(f'Unknown token {token}')

        if operator is not None and len(exprs) > 1:
            rhs, lhs = exprs.pop(), exprs.pop()
            exprs.append(operator(lhs, rhs))

    result = exprs.pop()
    if exprs:
        raise Exception(f'Parsing error {exprs!r}, {result}')
    return result
