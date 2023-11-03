import re
import readline
import sys
from typing import Optional

from .diceydice import eval_expr, ANSI

def completion(text: str, state: int) -> Optional[str]:
    if state > 0:
        return None

    dice_re = re.compile(r'(\d+)(?:d(\d*))?')
    line = readline.get_line_buffer().strip()

    result = ''
    if not text:
        if not line:
            return '1d20'
        if line[-1] == ')':
            return 'h'
        if not line[-1] in '+(':
            result += '+ '
        dice_specs: list[tuple[str, str]] = dice_re.findall(line)
        text = "{}d{}".format(*dice_specs[-1])

    if match := dice_re.match(text.lower()):
        dice = [2, 4, 6, 8, 10, 12, 20]
        count: str = match.group(1)
        sides: str = match.group(2)
        if not sides:
            result += f'{count}d2'
        else:
            next_idx = (dice.index(int(sides)) + 1) % len(dice)
            result += f'{count}d{dice[next_idx]}'
        return result

    return None


def repr() -> None:
    readline.parse_and_bind('tab: complete')
    readline.parse_and_bind('complete -o nosort')
    readline.set_completer(completion)
    try:
        while 'exit' not in (line := input().lower()):
            print(eval_expr(line, ANSI))
    except (KeyboardInterrupt, EOFError):
        pass


def main() -> None:
    if arg_expression := ' '.join(sys.argv[1:]).strip():
        eval_expr(arg_expression)
    else:
        repr()


main()
