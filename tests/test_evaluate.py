import pytest

from diceydice.evaluate import DiceResult, DiceRoller, DieRoll
from diceydice.parser import Dice, tokenize


def roller():
    # Always rolls the highest value.
    def predictable_rng(sides):
        return sides
    return DiceRoller(predictable_rng)


@pytest.fixture
def dice(request):
    return Dice.from_str(request.param)


@pytest.mark.parametrize(
    'dice,expected_len',
    [
        ('1d6', 1),
        ('2d20', 2),
        ('3d4', 3),
    ],
    indirect=['dice'],
)
def test_evaluate_dice(dice, expected_len):
    result = roller().evaluate_dice(dice)
    assert len(result) == expected_len


@pytest.fixture
def expression(request):
    return tokenize(request.param)


@pytest.mark.parametrize(
    'expression,expected_len',
    [
        ('1d6', 1),
        ('2d20', 2),
        ('1d20 + 2d4', 3),
    ],
    indirect=['expression'],
)
def test_evaluate_group(expression, expected_len):
    result = roller().evaluate_group(expression)
    assert len(result) == expected_len


def test_evaluate_group_illegal_nested_group():
    with pytest.raises(ValueError):
        roller().evaluate_group(tokenize('1d20 + (1d4 + 1d2)'))


@pytest.fixture
def dice_result(request):
    tokens = tokenize(request.param)
    return roller().evaluate(tokens)


@pytest.mark.parametrize(
    'dice_result,expected_value',
    [
        ('1d6', 6),
        ('2d20', 40),
        ('1d20 + 2d4', 28),
        ('1d20 + (1d2 + 1d4 + 1d6)', 32),

        # Postfix operators
        ('2d20 h1', 20),
        ('1d20 + (1d2 + 1d4 + 1d6)kh1', 26),
    ],
    indirect=['dice_result'],
)
def test_dice_result_value(dice_result, expected_value):
    result = dice_result.value()
    assert result == expected_value


def test_dice_result():
    result = roller().evaluate(
        tokenize('2d20 + (1d2 + 1d4) kh1')
    )
    expected = DiceResult(
        [
            DiceResult([DieRoll(20, 20), DieRoll(20, 20)]),
            DiceResult([DieRoll(2, 2), DieRoll(4, 4)]).highest(),
        ]
    )
    assert result == expected


@pytest.mark.parametrize(
    'roll_results,count,expected_value',
    [
        ([2, 1, 1], 1, 2),
        ([2, 3, 1], 2, 5),
    ],
)
def test_dice_result_highest(roll_results, count, expected_value):
    results = DiceResult(roll_results).highest(count)
    assert results.value() == expected_value


@pytest.mark.parametrize(
    'roll_results,count,expected_value',
    [
        ([2, 1, 5], 1, 1),
        ([2, 1, 5], 2, 3),
    ],
)
def test_dice_result_lowest(roll_results, count, expected_value):
    results = DiceResult(roll_results).lowest(count)
    assert results.value() == expected_value
