from dataclasses import dataclass
from typing import Callable, Iterable, TypeAlias

from . import lexer
from .lexer import Token

BinaryOperator: TypeAlias = Callable[['Expression', 'Expression'], 'Expression']

PRECEDENCE = {
    '+': 1,
    '-': 1,
    'k': 9,
    '<=': 9,
    '<-': 9,
    '<': 9,
    '>=': 9,
    '->': 9,
    '>': 9,
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


def parse_tokens(tokens: Iterable[Token]) -> Expression:
    return TdopParser(tokens).evaluate()


class TdopParser:
    """Top-down operator precedence parsing"""
    # https://eli.thegreenplace.net/2010/01/02/top-down-operator-precedence-parsing/

    def __init__(self, tokens: Iterable[Token]):
        # Copy the tokens and create an iterator over them
        self._tokens = iter(list(tokens))
        self.next_token = next(self._tokens, None)

    def advance(self) -> Token | None:
        current_token = self.next_token
        self.next_token = next(self._tokens, None)
        return current_token

    def evaluate(self, expression_bind_power: int = 0) -> Expression:
        if expression_bind_power < 0:
            raise ValueError('Bind power cannot be less than 0')
        token = self.advance()
        left = self.parse_atom(token)
        while expression_bind_power < self.bind_power(self.next_token):
            # Due to the while loop's check, we can be sure the next token
            # is non-Null. The assertion is safe and informs the type checker.
            token = self.advance()
            assert token is not None
            left = self.apply_operator(left, token)

        return left

    def parse_atom(self, token: Token | None) -> Expression:
        match token:
            case Token.GROUP_START:
                expr = self.evaluate()
                # Consume end paren and advance before returning expr.
                if self.next_token is not Token.GROUP_END:
                    raise Exception('Unclosed parentheses')
                self.advance()
                return expr
            case lexer.Dice(count=count, sides=sides):
                return DiceExpr(count, sides)
            case lexer.Combat(count=count):
                return CombatDiceExpr(count)
            case lexer.Literal(value=value):
                return ConstantExpr(value)
            case None:
                raise Exception('Unexpected end of input')
            case other:
                raise Exception(f'Unknown atom {other}')

    def apply_operator(self, left: Expression, oper: Token) -> Expression:
        bind_power = self.bind_power(oper)
        match oper:
            case Token.ADD:
                right = self.evaluate(bind_power)
                return left + right
            case Token.SUB:
                right = self.evaluate(bind_power)
                return left - right
            case lexer.KeepHighest(count=count):
                return KeepHighestExpr(count, left)
            case lexer.KeepLowest(count=count):
                return KeepLowestExpr(count, left)
            case (lexer.CritGE() | lexer.CritLE()) as mod:
                return ThresholdExpr(mod.oper, mod.threshold, 1, left)
            case (lexer.GE() | lexer.GT() | lexer.LE() | lexer.LT()) as mod:
                return ThresholdExpr(mod.oper, mod.threshold, 0, left)
            case other:
                raise Exception(f'Unknown operator {other}')

    @staticmethod
    def bind_power(token: Token | None) -> int:
        match token:
            case None:
                return 0
            case Token.GROUP_START:
                return 0
            case Token.GROUP_END:
                return 0
            case Token.ADD:
                return PRECEDENCE['+']
            case Token.SUB:
                return PRECEDENCE['-']
            case lexer.KeepHighest() | lexer.KeepLowest():
                return PRECEDENCE['k']
            case lexer.ThresholdOperator(oper=operator):
                return PRECEDENCE[operator]
            case other:
                raise Exception(f'Unknown operator {other}')
