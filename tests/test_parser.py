import pytest

from diceydice import lexer, parser
from diceydice.parser import AddExpr, DiceExpr


@pytest.mark.parametrize(
    'expr,expected',
    [
        ('2d20 + 1d6', AddExpr(DiceExpr(2, 20), DiceExpr(1, 6))),
        ('2d20 + 1d6', DiceExpr(2, 20) + DiceExpr(1, 6)),
    ],
)
def test_parse_tokens(expr, expected):
    tokens = lexer.tokenize(expr)
    result = parser.parse_tokens(tokens)
    assert result == expected
