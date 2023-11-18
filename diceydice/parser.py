import re
from typing import Optional

# This is getting stupid.
TOKENIZER = re.compile(r'\d+d\d+|k?[hl]\d*|[<>]=?\d+|<-\d+|->\d+|\d*c|\d+|\S')


class Token:
    ADD: 'Token'
    SUB: 'Token'
    GROUP_START: 'Token'
    GROUP_END: 'Token'

    def __init__(self, token_str: str):
        self.token_str = token_str

    def __str__(self) -> str:
        return self.token_str

    def __repr__(self) -> str:
        return f'{self.__class__}({self.token_str!r})'

    @classmethod
    def from_str(cls, token_str: str) -> 'Token':
        token = token_str.lower()
        if token == '+':
            return Token.ADD
        elif token == '-':
            return Token.SUB
        elif token == '(':
            return Token.GROUP_START
        elif token == ')':
            return Token.GROUP_END
        elif Dice.parse(token):
            return Dice.from_str(token)
        elif PostfixOperator.parse(token):
            return PostfixOperator.from_str(token)
        elif Combat.parse(token):
            return Combat.from_str(token)
        elif FlatNumber.parse(token):
            return FlatNumber.from_str(token)
        raise ValueError(f'Unknown token {token_str}')


Token.GROUP_START = Token('(')
Token.GROUP_END = Token(')')
Token.ADD = Token('+')
Token.SUB = Token('-')


class Dice(Token):
    DICE_RE = re.compile(r'^(\d+)d(\d+)$')

    def __init__(self, count: int, sides: int):
        super().__init__(f'{count}d{sides}')
        self.count = count
        self.sides = sides

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Dice):
            return False
        return self.count == other.count and self.sides == other.sides

    def __repr__(self) -> str:
        return f'Dice({self.count}, {self.sides})'

    @classmethod
    def parse(cls, token_str: str) -> Optional[re.Match[str]]:
        return cls.DICE_RE.match(token_str)

    @classmethod
    def from_str(cls, token_str: str) -> 'Dice':
        if match := cls.parse(token_str):
            count: str = match.group(1)
            sides: str = match.group(2)
            return Dice(int(count), int(sides))
        raise ValueError(f'Invalid dice syntax {token_str!r}')


class PostfixOperator(Token):
    OPER_RE = re.compile(r'((?:k?[hl])|<-|->|(?:[<>]=?))(\d*)')

    @classmethod
    def parse(cls, token_str: str) -> Optional[re.Match[str]]:
        return cls.OPER_RE.match(token_str)

    @classmethod
    def from_str(cls, token_str: str) -> 'PostfixOperator':
        try:
            if match := cls.parse(token_str):
                keep_type: str = match.group(1)
                count: str = match.group(2)
                return {
                    'h': KeepHighest,
                    'kh': KeepHighest,
                    'l': KeepLowest,
                    'kl': KeepLowest,
                    '>=': GE,
                    '>': GT,
                    '<=': LE,
                    '<': LT,
                    '<-': CritLE,
                    '->': CritGE,
                }[keep_type](int(count or '1'))
        except KeyError:
            pass
        raise ValueError(f'Invalid Operator syntax {token_str!r}')


class KeepHighest(PostfixOperator):
    def __init__(self, count: int):
        super().__init__(f'kh{count}')
        self.count = count

    def __repr__(self) -> str:
        return f'KeepHighest({self.count})'

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, KeepHighest):
            return False
        return self.count == other.count


class KeepLowest(PostfixOperator):
    def __init__(self, count: int):
        super().__init__(f'kl{count}')
        self.count = count

    def __repr__(self) -> str:
        return f'KeepLowest({self.count})'

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, KeepLowest):
            return False
        return self.count == other.count


class ThresholdOperator(PostfixOperator):
    def __init__(self, oper: str, threshold: int):
        super().__init__(f'{oper}{threshold}')
        self.oper = oper
        self.threshold = threshold

    def __repr__(self) -> str:
        return f'{self.__class__})({self.threshold})'

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ThresholdOperator):
            return False
        return (
            self.threshold == other.threshold
            and self.oper == other.oper
        )


class CritGE(ThresholdOperator):
    def __init__(self, threshold: int):
        super().__init__('->', threshold)


class CritLE(ThresholdOperator):
    def __init__(self, threshold: int):
        super().__init__('<-', threshold)


class GE(ThresholdOperator):
    def __init__(self, threshold: int):
        super().__init__('>=', threshold)


class GT(ThresholdOperator):
    def __init__(self, threshold: int):
        super().__init__('>', threshold)


class LE(ThresholdOperator):
    def __init__(self, threshold: int):
        super().__init__('<=', threshold)


class LT(ThresholdOperator):
    def __init__(self, threshold: int):
        super().__init__('<', threshold)


class Combat(Token):
    COMBAT_RE = re.compile(r'(\d*)c')

    def __init__(self, count: int):
        super().__init__(f'{count}c')
        self.count = count

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Combat):
            return False
        return self.count == other.count

    @classmethod
    def parse(cls, token_str: str) -> Optional[re.Match[str]]:
        return cls.COMBAT_RE.match(token_str)

    @classmethod
    def from_str(cls, token_str: str) -> 'Combat':
        if match := cls.parse(token_str):
            count: str = match.group(1)
            return Combat(int(count or '1'))
        raise ValueError(f'Invalid combat dice syntax {token_str!r}')


class FlatNumber(Token):
    NUMBER_RE = re.compile(r'^(\d+)$')

    def __init__(self, value: int):
        super().__init__(str(value))
        self.value = value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FlatNumber):
            return False
        return self.value == other.value

    @classmethod
    def parse(cls, token_str: str) -> Optional[re.Match[str]]:
        return cls.NUMBER_RE.match(token_str)

    @classmethod
    def from_str(cls, token_str: str) -> 'FlatNumber':
        if match := cls.parse(token_str):
            value: str = match.group(1)
            return FlatNumber(int(value))
        raise ValueError(f'Invalid number literal {token_str!r}')


def tokenize(expression: str) -> list[Token]:
    token_strings: list[str] = TOKENIZER.findall(expression.lower())
    try:
        return list(map(Token.from_str, token_strings))
    except ValueError:
        print("Tokens:", repr(token_strings))
        raise
