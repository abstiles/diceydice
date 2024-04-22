import pytest

from diceydice.diceydice import eval_expr, PLAIN
from diceydice.evaluate import DiceRoller


def high_roller() -> DiceRoller:
    def predictable_rng(sides: int) -> int:
        return sides
    return DiceRoller(predictable_rng)


def mid_roller() -> DiceRoller:
    def predictable_rng(sides: int) -> int:
        return sides // 2
    return DiceRoller(predictable_rng)


def low_roller() -> DiceRoller:
    def predictable_rng(sides: int) -> int:
        return 1
    return DiceRoller(predictable_rng)


@pytest.mark.parametrize(
    'input,output',
    [
        ('2d20', '40 <= 20 + 20'),
        ('2d20h', '20 <= high([20], 20)'),
        ('1d20 + (1d2 + 1d4 + 1d6)h', '26 <= 20 + high(2, 4, [6])'),
        ('3d20<-10', '0{3} <= ≤10(20, 20, 20)'),
        ('3d20->10', '6 <= ≥10([20], [20], [20])'),

        ('1d20 + (1d2 + 2d6)h', '26 <= 20 + high(2, [6], 6)'),
        ('1d20 + (1d2 + 1d4 + 2d6)h', '26 <= 20 + high(2, 4, [6], 6)'),
        ('1d20 + (1d2 + (2d6))h', '32 <= 20 + high(2, (6 + 6))'),
        ('1d20 + (1d2 + 1d4 + (2d6))h', '32 <= 20 + high(2, 4, (6 + 6))'),
    ],
)
def test_eval_expr_high_rolls(input, output):
    result = eval_expr(input, formatter=PLAIN, dice_roller=high_roller())
    assert result == output


@pytest.mark.parametrize(
    'input,output',
    [
        ('2d20', '20 <= 10 + 10'),
        ('2d20h', '10 <= high([10], 10)'),
        ('1d20 + (1d2 + 1d4 + 1d6)h', '13 <= 10 + high(1, 2, [3])'),
        ('3d20<-10', '3 <= ≤10([10], [10], [10])'),
        ('3d20->10', '3 <= ≥10([10], [10], [10])'),
    ],
)
def test_eval_expr_mid_rolls(input, output):
    result = eval_expr(input, formatter=PLAIN, dice_roller=mid_roller())
    assert result == output


@pytest.mark.parametrize(
    'input,output',
    [
        ('2d20', '2 <= 1 + 1'),
        ('2d20h', '1 <= high([1], 1)'),
        ('1d20 + (1d2 + 1d4 + 1d6)h', '2 <= 1 + high([1], 1, 1)'),
        ('3d20<-10', '6 <= ≤10([1], [1], [1])'),
        ('3d20->10', '0{3} <= ≥10(1, 1, 1)'),
    ],
)
def test_eval_expr_low_rolls(input, output):
    result = eval_expr(input, formatter=PLAIN, dice_roller=low_roller())
    assert result == output
