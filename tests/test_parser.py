import pytest

from diceydice import lexer, parser
from diceydice.parser import AddExpr, ConstantExpr, DiceExpr


@pytest.mark.parametrize(
    'expr,expected',
    [
        ('2d20 + 1d6', AddExpr(DiceExpr(2, 20), DiceExpr(1, 6))),
        ('2d20 + 1d6', DiceExpr(2, 20) + DiceExpr(1, 6)),
        ('1d20 + 1d2 + 1d4', DiceExpr(1, 20) + DiceExpr(1, 2) + DiceExpr(1, 4)),
        ('1d20 + (1d2 + 1d4)', DiceExpr(1, 20) + (DiceExpr(1, 2) + DiceExpr(1, 4))),
        ('20 - 1d4', ConstantExpr(20) - DiceExpr(1, 4)),
    ],
)
def test_parse_tokens(expr, expected):
    tokens = lexer.tokenize(expr)
    result = parser.parse_tokens(tokens)
    assert result == expected


def test_parse_tokens_distinct_associativity():
    no_parens = lexer.tokenize('1d20 + 1d2 + 1d4')
    with_parens = lexer.tokenize('1d20 + (1d2 + 1d4)')
    assert parser.parse_tokens(no_parens) != parser.parse_tokens(with_parens)


@pytest.mark.parametrize(
    'expr',
    [
        '2d20 + 1d6',
        '1d20 + 1d2 + 1d4',
        '1d20 + (1d2 + 1d4)',
        '20 - 1d4',
    ],
)
def test_expression_str(expr):
    tokens = lexer.tokenize(expr)
    result = parser.parse_tokens(tokens)
    assert str(result) == expr
