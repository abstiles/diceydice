import re
from typing import Optional

TOKENIZER = re.compile(r'(?:\d+d\d+)|(?:k?[hl]\d*)|\S')


class Token:
    ADD: 'Token'
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
        elif token == '(':
            return Token.GROUP_START
        elif token == ')':
            return Token.GROUP_END
        elif Dice.parse(token):
            return Dice.from_str(token)
        elif PostfixOperator.parse(token):
            return PostfixOperator.from_str(token)
        raise ValueError(f'Unknown token {token_str}')


Token.GROUP_START = Token('(')
Token.GROUP_END = Token(')')
Token.ADD = Token('+')


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
    OPER_RE = re.compile(r'k?([hl])(\d*)')

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
                    'l': KeepLowest,
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


def tokenize(expression: str) -> list[Token]:
    token_strings: list[str] = TOKENIZER.findall(expression)
    try:
        return list(map(Token.from_str, token_strings))
    except ValueError:
        print("Tokens:", repr(token_strings))
        raise
