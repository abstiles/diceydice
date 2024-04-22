import pytest

from diceydice.evaluate import CombatDieRoll, DiceSum, DiceRoller, DieRoll
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

        # Funny groupings
        ('1d20 + (1d2 + 2d6)kh1', 26),
        ('1d20 + (1d2 + 1d4 + 2d6)kh1', 26),
        ('1d20 + (1d2 + (2d6))kh1', 32),
        ('1d20 + (1d2 + 1d4 + (2d6))kh1', 32),

        # Constant modifiers
        ('2d20 + 2', 42),
        ('3d20 - 42', 18),
        ('(1d6 + 10) + 2', 18),
        ('(1d9 + (1d8 + 2))h', 10),
    ],
    indirect=['dice_result'],
)
def test_dice_result_value(dice_result, expected_value):
    result = dice_result.value()
    assert result == expected_value


@pytest.mark.parametrize(
    'dice_result,expected',
    [
        ('2d20 h1', [0]),
        ('(1d2 + 1d4 + 1d6 + 1d8)kh2', [2, 3]),
        ('(1d2 + 1d8 + 1d4 + 1d6 + 1d6)kh2', [1, 3]),
    ],
    indirect=['dice_result'],
)
def test_filtered_dice_kept_indexes(dice_result, expected):
    assert list(dice_result.kept_indexes()) == expected


def test_dice_result():
    result = roller().evaluate(
        tokenize('2d20 + (1d2 + 1d4) kh1')
    )
    expected = DiceSum(
        [
            DiceSum([DieRoll(20, 20), DieRoll(20, 20)]),
            DiceSum([DieRoll(2, 2), DieRoll(4, 4)]).highest(),
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
    rolls = [DieRoll(x, x) for x in roll_results]
    results = DiceSum(rolls).highest(count)
    assert results.value() == expected_value


@pytest.mark.parametrize(
    'roll_results,count,expected_value',
    [
        ([2, 1, 5], 1, 1),
        ([2, 1, 5], 2, 3),
    ],
)
def test_dice_result_lowest(roll_results, count, expected_value):
    rolls = [DieRoll(x, x) for x in roll_results]
    results = DiceSum(rolls).lowest(count)
    assert results.value() == expected_value


def test_dice_sum_combat_dice():
    total = DiceSum([
        CombatDieRoll(2), CombatDieRoll(1, True),
        CombatDieRoll(0), CombatDieRoll(1, True),
    ])
    assert total.result == 4
    assert total.effects == 2


def test_dice_sum_threshold():
    total = DiceSum([
        DieRoll(20, 5), DieRoll(20, 15), DieRoll(20, 10), DieRoll(20, 20),
        DieRoll(20, 1),
    ]).le(10)
    assert total.result == 3


def test_dice_sum_threshold_with_crits():
    total = DiceSum([
        DieRoll(20, 5), DieRoll(20, 15), DieRoll(20, 10), DieRoll(20, 20),
        DieRoll(20, 1),
    ]).crit_le(10)
    assert (total.result, total.effects) == (4, 1)
