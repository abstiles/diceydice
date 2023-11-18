import pytest

from diceydice.parser import (
    Combat, CritLE, CritGE, Dice, FlatNumber, GE, GT, KeepHighest, KeepLowest,
    LE, LT, Token, tokenize,
)


@pytest.mark.parametrize(
    'input,tokens',
    [
        # Basic addition, grouping
        ('1d20', [Dice(1, 20)]),
        ('1D20', [Dice(1, 20)]),
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

        # Postfix operator testing
        ('2d20h', [Dice(2, 20), KeepHighest(1)]),
        ('2d20kh', [Dice(2, 20), KeepHighest(1)]),
        ('2d20h3', [Dice(2, 20), KeepHighest(3)]),
        ('2d20kh4', [Dice(2, 20), KeepHighest(4)]),
        ('2d20l', [Dice(2, 20), KeepLowest(1)]),
        ('2d20kl', [Dice(2, 20), KeepLowest(1)]),
        ('2d20l3', [Dice(2, 20), KeepLowest(3)]),
        ('2d20kl4', [Dice(2, 20), KeepLowest(4)]),
        (
            '1d20 + (1d2 + 1d4 + 1d6) kh1',
            [
                Dice(1, 20), Token.ADD,
                Token.GROUP_START,
                Dice(1, 2), Token.ADD, Dice(1, 4), Token.ADD, Dice(1, 6),
                Token.GROUP_END,
                KeepHighest(1),
            ],
        ),

        # Threshold dice
        ('5d20<10', [Dice(5, 20), LT(10)]),
        ('5d20<=10', [Dice(5, 20), LE(10)]),
        ('5d20>10', [Dice(5, 20), GT(10)]),
        ('5d20>=10', [Dice(5, 20), GE(10)]),
        ('5d20<-10', [Dice(5, 20), CritLE(10)]),
        ('5d20->10', [Dice(5, 20), CritGE(10)]),

        # Combat dice
        ('c', [Combat(1)]),
        ('2c', [Combat(2)]),

        # Numeric literals
        ('42', [FlatNumber(42)]),
        ('1d20 + 10', [Dice(1, 20), Token.ADD, FlatNumber(10)]),
        ('20 - 1d4', [FlatNumber(20), Token.SUB, Dice(1, 4)]),
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
