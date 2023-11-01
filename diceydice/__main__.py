import sys

from .evaluate import evaluate
from .parser import tokenize

result = evaluate(tokenize(' '.join(sys.argv[1:])))
print(f'{result.value()} => [{result}]')
