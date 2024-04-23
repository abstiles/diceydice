import inspect
import re
from abc import ABCMeta, abstractmethod
from typing import ClassVar, Optional
from typing_extensions import Self

from .exceptions import TokenizeError


class TokenMeta(ABCMeta):
    match_regexes: list[str] = []

    def __new__(
            metacls, name: str, bases: tuple[type, ...], namespace: dict[str, object],
            **kwargs: object
    ) -> type:
        return super().__new__(metacls, name, bases, namespace)

    def __init__(
            cls, name: str, bases: tuple[type, ...], namespace: dict[str, object],
            match: Optional[str] = None, **kwargs: object
    ) -> None:
        super().__init__(name, bases, namespace)
        if match is None and not (
            inspect.isabstract(cls)
            or cls.has_regex()
        ):
            raise Exception("Token classes must have a regex matcher.")
        elif match is not None:
            TokenMeta.match_regexes.append(match)
            cls._regex = re.compile(f"^{match}$")
        for name, arg in kwargs.items():
            instance: object = cls(arg)
            setattr(cls, name, instance)

    def has_regex(cls) -> bool:
        try:
            cls._regex
            return True
        except AttributeError:
            return False


class BaseToken(metaclass=TokenMeta):
    @classmethod
    def match(cls, token_str: str) -> Optional[Self]:
        try:
            return cls.from_str(token_str)
        except Exception:
            return None

    @classmethod
    def parse(cls, token_str: str) -> Optional[re.Match[str]]:
        return cls._regex.match(token_str)

    @classmethod
    @abstractmethod
    def from_str(cls, token_str: str) -> Self:
        ...


class Token(BaseToken, match=r"\S"):
    ADD: ClassVar[Self]
    GROUP_START: ClassVar[Self]
    GROUP_END: ClassVar[Self]

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

        for token_type in cls.__subclasses__():
            if match := token_type.match(token):
                return match

        raise ValueError(f'Unknown token {token_str}')


Token.GROUP_START = Token('(')
Token.GROUP_END = Token(')')
Token.ADD = Token('+')


class Constant(Token, match=r'(-?)\s*(\d+)\b'):
    def __init__(self, value: int):
        super().__init__(str(value))
        self.value = value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Constant):
            return False
        return self.value == other.value

    def __repr__(self) -> str:
        return f'Constant({self.value})'

    @classmethod
    def from_str(cls, token_str: str) -> 'Constant':
        if match := cls.parse(token_str):
            minus: str = match.group(1)
            value: str = match.group(2)
            sign = -1 if minus else 1
            return Constant(sign * int(value))
        raise ValueError(f'Invalid numeric syntax {token_str!r}')


class Dice(Token, match=r'(\d+)d(\d+)'):
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
        if match := cls.parse(token_str):
            count: str = match.group(1)
            sides: str = match.group(2)
            return Dice(int(count), int(sides))
        raise ValueError(f'Invalid dice syntax {token_str!r}')


class PostfixOperator(Token, match=r'((?:k?[hl])|<-|->|(?:[<>]=?))(\d*)'):
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


class Combat(Token, match=r'(\d*)c'):
    def __init__(self, count: int):
        self.count = count

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Combat):
            return False
        return self.count == other.count

    @classmethod
    def from_str(cls, token_str: str) -> 'Combat':
        if match := cls.parse(token_str):
            count: str = match.group(1)
            return Combat(int(count or '1'))
        raise ValueError(f'Invalid combat dice syntax {token_str!r}')


def tokenize(expression: str) -> list[Token]:
    # Reversing because more specific regexes follow less specific ones. This
    # ensures we test from most to least specific. Yes, this introduces an
    # unpleasant dependency on the ordering of the class definitions here.
    all_tokens = re.compile('|'.join(reversed(TokenMeta.match_regexes)))
    token_strings = list(all_tokens.finditer(expression.lower()))
    matches = (match.group(0) for match in token_strings)
    try:
        return list(map(Token.from_str, matches))
    except ValueError as exc:
        raise TokenizeError(str(exc)) from exc
