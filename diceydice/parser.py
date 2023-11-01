import re

TOKENIZER = re.compile(r'\w+|\S')


class Token:
    ADD: 'Token'
    GROUP_START: 'Token'
    GROUP_END: 'Token'

    def __init__(self, token_str: str):
        self.token_str = token_str

    def __str__(self) -> str:
        return self.token_str

    def __repr__(self) -> str:
        return f'Token({self.token_str!r})'

    @classmethod
    def from_str(cls, token_str: str) -> 'Token':
        if token_str == '+':
            return Token.ADD
        elif token_str == '(':
            return Token.GROUP_START
        elif token_str == ')':
            return Token.GROUP_END
        return Dice.from_str(token_str)


Token.GROUP_START = Token('(')
Token.GROUP_END = Token(')')
Token.ADD = Token('+')


class Dice(Token):
    DICE_RE = re.compile(r'^(\d+)[dD](\d+)$')

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
    def from_str(cls, token_str: str) -> 'Dice':
        if match := cls.DICE_RE.match(token_str):
            count: str = match.group(1)
            sides: str = match.group(2)
            return Dice(int(count), int(sides))
        raise ValueError(f'Invalid dice syntax {token_str!r}')


def tokenize(expression: str) -> list[Token]:
    token_strings: list[str] = TOKENIZER.findall(expression)
    return list(map(Token.from_str, token_strings))
