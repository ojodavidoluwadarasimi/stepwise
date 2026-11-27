"""
Tests for math_engine.py

Python's built-in Fraction is used here ONLY as an independent referee to
check our engine. The engine itself uses no math libraries.

Run:  python -m unittest -v test_math_engine
"""
import random
import unittest
from fractions import Fraction

from math_engine import Frac, MathError, solve, to_decimal, to_mixed


def ans(text):
    return str(solve(text).answer)


class KnownAnswers(unittest.TestCase):
    def test_order_of_operations(self):
        self.assertEqual(ans("2 + 3 * 4"), "14")
        self.assertEqual(ans("(2 + 3) * 4"), "20")
        self.assertEqual(ans("100 - 10 - 5"), "85")
        self.assertEqual(ans("100 / 10 / 5"), "2")
        self.assertEqual(ans("1 + 2 + 3 * 4"), "15")

    def test_powers(self):
        self.assertEqual(ans("2 ^ 3 ^ 2"), "512")      # right-associative
        self.assertEqual(ans("-2 ^ 2"), "-4")          # minus applies after the power
        self.assertEqual(ans("(-2) ^ 2"), "4")
        self.assertEqual(ans("2 ^ -2"), "1/4")
        self.assertEqual(ans("(2/3) ^ 3"), "8/27")
        self.assertEqual(ans("5 ^ 0"), "1")
        self.assertEqual(ans("2 ** 10"), "1024")

    def test_fractions_and_decimals(self):
        self.assertEqual(ans("1/2 + 1/3"), "5/6")
        self.assertEqual(ans("3/4 - 5/4"), "-1/2")
        self.assertEqual(ans("2/3 * 3/4"), "1/2")
        self.assertEqual(ans("(1/2) / (1/4)"), "2")
        self.assertEqual(ans("7 / 2"), "7/2")
        self.assertEqual(ans("10 / 4"), "5/2")
        self.assertEqual(ans("0.1 + 0.2"), "3/10")   # exact, unlike floating point
        self.assertEqual(ans("1.5 * 4"), "6")

    def test_signs(self):
        self.assertEqual(ans("3 - -2"), "5")
        self.assertEqual(ans("-(3 + 4)"), "-7")
        self.assertEqual(ans("6 / -3"), "-2")
        self.assertEqual(ans("--5"), "5")

    def test_unicode_operators(self):
        self.assertEqual(ans("6 × 7"), "42")
        self.assertEqual(ans("20 ÷ 4"), "5")

    def test_big_numbers_are_exact(self):
        self.assertEqual(ans("2 ^ 100"), "1267650600228229401496703205376")


class Errors(unittest.TestCase):
    def check(self, text):
        with self.assertRaises(MathError):
            solve(text)

    def test_division_by_zero(self):
        self.check("5 / 0")
        self.check("1 / (2 - 2)")
        self.check("0 ^ -1")

    def test_undefined(self):
        self.check("0 ^ 0")

    def test_bad_input(self):
        for text in ["", "   ", "2 +", "(1 + 2", "1 + 2)", "abc", "2 3",
                     "2(3 + 4)", "1..5 + 2", "2 ^ 0.5", "* 3"]:
            with self.subTest(text=text):
                self.check(text)

    def test_limits(self):
        self.check("9 ^ 9 ^ 9")
        self.check("1" * 501)


class Formatting(unittest.TestCase):
    def test_decimal_expansion(self):
        cases = {
            (1, 3): "0.(3)", (1, 6): "0.1(6)", (1, 8): "0.125",
            (22, 7): "3.(142857)", (-1, 4): "-0.25", (5, 1): "5", (7, 2): "3.5",
        }
        for (n, d), expected in cases.items():
            with self.subTest(n=n, d=d):
                self.assertEqual(to_decimal(Frac(n, d)), expected)

    def test_mixed_numbers(self):
        self.assertEqual(to_mixed(Frac(7, 3)), "2 1/3")
        self.assertEqual(to_mixed(Frac(-7, 3)), "-2 1/3")
        self.assertIsNone(to_mixed(Frac(1, 3)))
        self.assertIsNone(to_mixed(Frac(6, 3)))

    def test_fraction_is_always_lowest_terms(self):
        f = Frac(6, -8)
        self.assertEqual((f.n, f.d), (-3, 4))

    def test_explanations_exist(self):
        text = solve("2 + 3 * (4 - 1)").text()
        self.assertIn("Work inside the parentheses first.", text)
        self.assertIn("Answer: 11", text)


# ---- Randomised cross-check against Python's Fraction ----------------------

PREC = {"+": 1, "-": 1, "*": 2, "/": 2}


def gen(rng, depth):
    if depth == 0 or rng.random() < 0.25:
        if rng.random() < 0.2:
            return ("num", rng.choice(["0.5", "1.25", "0.1", "2.5", "0.75"]))
        return ("num", str(rng.randint(0, 12)))
    r = rng.random()
    if r < 0.12:
        return ("neg", gen(rng, depth - 1))
    if r < 0.27:
        exp = ("num", str(rng.randint(0, 3)))
        if rng.random() < 0.3:
            exp = ("neg", exp)
        return ("bin", "^", gen(rng, depth - 1), exp)
    return ("bin", rng.choice("+-*/"), gen(rng, depth - 1), gen(rng, depth - 1))


def prec(t):
    if t[0] == "num":
        return 5
    if t[0] == "neg":
        return 3
    return 4 if t[1] == "^" else PREC[t[1]]


def render(t):
    """Write a tree as text with as few brackets as the rules allow."""
    if t[0] == "num":
        return t[1]
    if t[0] == "neg":
        c = render(t[1])
        return "-" + (f"({c})" if prec(t[1]) < 3 else c)
    _, op, l, r = t
    left, right = render(l), render(r)
    if op == "^":
        if prec(l) <= 4:
            left = f"({left})"
        if r[0] != "neg" and prec(r) < 4:
            right = f"({right})"
    else:
        p = prec(t)
        if prec(l) < p:
            left = f"({left})"
        if prec(r) <= p:
            right = f"({right})"
    return f"{left} {op} {right}"


def oracle(t):
    if t[0] == "num":
        return Fraction(t[1])
    if t[0] == "neg":
        return -oracle(t[1])
    _, op, l, r = t
    a, b = oracle(l), oracle(r)
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if op == "/":
        if b == 0:
            raise ZeroDivisionError
        return a / b
    e = int(b)
    if a == 0 and e <= 0:
        raise ZeroDivisionError
    return a ** e


def same(frac, expected):
    return frac.n == expected.numerator and frac.d == expected.denominator


class RandomCrossCheck(unittest.TestCase):
    def test_against_python_fraction(self):
        rng = random.Random(2026)
        checked = errors = 0
        for _ in range(4000):
            tree = gen(rng, rng.randint(1, 4))
            text = render(tree)
            try:
                expected = oracle(tree)
            except ZeroDivisionError:
                expected = None
            if expected is None:
                with self.assertRaises(MathError, msg=text):
                    solve(text)
                errors += 1
                continue
            sol = solve(text)
            self.assertTrue(same(sol.answer, expected), msg=f"{text} -> {sol.answer}, expected {expected}")
            # Every intermediate line must still be a valid expression with the same value.
            for st in sol.steps:
                self.assertTrue(same(solve(st.after).answer, expected), msg=f"{text} | step: {st.after}")
            checked += 1
        print(f"\n  cross-checked {checked} expressions, {errors} correct error cases")
        self.assertGreater(checked, 2500)


if __name__ == "__main__":
    unittest.main()
