import pytest

from diceydice.parser import Dice, Token, tokenize


@pytest.mark.parametrize(
    'input,tokens',
    [
        ('1d20', [Dice(1, 20)]),
        ('1d20 + 1d2', [Dice(1, 20), Token.ADD, Dice(1, 2)]),
        ('1d20+1d2', [Dice(1, 20), Token.ADD, Dice(1, 2)]),
        (
            '(1d20 + 1d2)',
            [
                Token.GROUP_START,
                Dice(1, 20), Token.ADD, Dice(1, 2),
                Token.GROUP_END,
            ]
        ),
    ],
)
def test_tokenize(input, tokens):
    result = list(tokenize(input))
    assert result == tokens


@pytest.mark.parametrize(
    'token,dice',
    [
        ('1d20', Dice(1, 20)),
        ('2d6', Dice(2, 6)),
    ],
)
def test_dice_from_str(token, dice):
    result = Dice.from_str(token)
    assert result == dice
