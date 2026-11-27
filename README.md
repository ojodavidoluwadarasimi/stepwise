# stepwise

An exact math engine, written from scratch, that explains every step.

**Status: In Development (v1).** Arithmetic and fractions work and are tested. Everything under "Not built yet" is planned, not done.

## What it does today

- Exact arithmetic with whole numbers, decimals and fractions. No rounding errors: `0.1 + 0.2` is exactly `3/10`.
- Operators `+ - * / ^` and parentheses, with the correct order of operations.
- Explains each step in plain words, with a "Why" line when the order of operations matters.
- Gives the answer as a fraction, a mixed number, and an exact decimal. Repeating digits appear in brackets, so `1/3` is `0.(3)`.
- Refuses bad input with a clear message instead of a wrong answer (division by zero, `0^0`, unmatched brackets, numbers that are too large).

## Example

```
$ python math_engine.py "2 + 3 * (4 - 1) ^ 2"

Problem: 2 + 3 * (4 - 1) ^ 2

Step 1: Subtract: 4 - 1 = 3
  Why: Work inside the parentheses first.
  Now: 2 + 3 * 3 ^ 2
Step 2: Power: 3^2 = 3 * 3 = 9
  Why: Powers come before multiplication, division, addition and subtraction.
  Now: 2 + 3 * 9
Step 3: Multiply: 3 * 9 = 27
  Why: Multiplication and division come before addition and subtraction.
  Now: 2 + 27
Step 4: Add: 2 + 27 = 29
  Now: 29

Answer: 29
```

## Run it

No installs needed. Any Python 3 works (tested on 3.13).

```
python math_engine.py "1/2 + 2/3 * (3 - 0.5)"
python math_engine.py          # interactive mode
```

## Tests

```
python -m unittest -v test_math_engine
```

The suite has 15 tests: known answers, error cases, formatting, and a randomized check. The randomized check builds about 4,000 random expressions, solves each one, and compares the answer with Python's built-in `Fraction`. It also confirms every intermediate step still evaluates to the same final answer. `Fraction` is used only as a referee inside the tests. The engine itself uses no math libraries.

## Not built yet

- Algebra and equations (solving for x)
- Calculus (derivatives and integrals)
- Matrices
- Probability and statistics
- Fractional exponents
- A library of fast-calculation tricks
- Implicit multiplication such as `2(3 + 4)`. For now, write `2 * (3 + 4)`.

## Why this exists

This is one building block of a larger project: a math-reasoning AI built entirely from scratch. The neural network is not meant to do exact arithmetic on its own. It will hand calculations to an engine like this one and check its answers against it.
