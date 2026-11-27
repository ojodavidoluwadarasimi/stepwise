"""
math_engine.py: our own exact math engine, version 1 (built from scratch).

What it does today:
  - Exact arithmetic with whole numbers, decimals and fractions (no rounding errors)
  - Operators: + - * / ^ and parentheses, with correct order of operations
  - Explains every step in plain words, then gives the answer as a fraction,
    a mixed number, and an exact decimal (repeating parts shown in brackets)

What it does NOT do yet (later versions): algebra, equations, calculus,
matrices, probability, and the shortcut tricks library.

Run:   python math_engine.py "2 + 3 * (4 - 1)"
or:    python math_engine.py          (interactive mode)
"""

import sys

MAX_BITS = 3000  # guard: refuse powers that would produce enormous numbers


class MathError(Exception):
    """A problem with the user's input, with a message we can show them."""


# ---------------------------------------------------------------------------
# Exact numbers
# ---------------------------------------------------------------------------

def gcd(a, b):
    """Greatest common divisor (Euclid's algorithm)."""
    a, b = abs(a), abs(b)
    while b:
        a, b = b, a % b
    return a


def lcm(a, b):
    return a // gcd(a, b) * b


def ipow(base, exp):
    """Integer power by repeated squaring."""
    result = 1
    while exp:
        if exp & 1:
            result *= base
        base *= base
        exp >>= 1
    return result


class Frac:
    """An exact fraction n/d, always stored in lowest terms with d > 0."""

    __slots__ = ("n", "d")

    def __init__(self, n, d=1):
        if d == 0:
            raise MathError("Cannot divide by zero.")
        if d < 0:
            n, d = -n, -d
        g = gcd(n, d)
        if g > 1:
            n, d = n // g, d // g
        self.n, self.d = n, d

    def is_int(self):
        return self.d == 1

    def __add__(self, o):
        return Frac(self.n * o.d + o.n * self.d, self.d * o.d)

    def __sub__(self, o):
        return Frac(self.n * o.d - o.n * self.d, self.d * o.d)

    def __mul__(self, o):
        return Frac(self.n * o.n, self.d * o.d)

    def __truediv__(self, o):
        if o.n == 0:
            raise MathError("Cannot divide by zero.")
        return Frac(self.n * o.d, self.d * o.n)

    def __eq__(self, o):
        return isinstance(o, Frac) and self.n == o.n and self.d == o.d

    def __hash__(self):
        return hash((self.n, self.d))

    def pow_int(self, e):
        """Raise to a whole-number power e (may be negative)."""
        if e < 0:
            if self.n == 0:
                raise MathError("Cannot divide by zero: 0 cannot be raised to a negative power.")
            return Frac(self.d, self.n).pow_int(-e)
        if self.d == 1 and self.n in (0, 1):
            return Frac(self.n) if e > 0 else Frac(1)
        if self.d == 1 and self.n == -1:
            return Frac(-1 if e % 2 else 1)
        if max(abs(self.n).bit_length(), self.d.bit_length()) * e > MAX_BITS:
            raise MathError("That power would produce a number too large for this version.")
        return Frac(ipow(self.n, e), ipow(self.d, e))

    def __str__(self):
        return str(self.n) if self.d == 1 else f"{self.n}/{self.d}"

    __repr__ = __str__


def to_decimal(f, max_digits=40):
    """Exact decimal expansion. Repeating digits go in brackets: 1/3 -> 0.(3)"""
    sign = "-" if f.n < 0 else ""
    n, d = abs(f.n), f.d
    whole, rem = divmod(n, d)
    if rem == 0:
        return f"{sign}{whole}"
    digits, seen = [], {}
    while rem and rem not in seen and len(digits) < max_digits:
        seen[rem] = len(digits)
        rem *= 10
        digits.append(str(rem // d))
        rem %= d
    if rem == 0:
        return f"{sign}{whole}." + "".join(digits)
    if rem in seen:
        i = seen[rem]
        return f"{sign}{whole}." + "".join(digits[:i]) + "(" + "".join(digits[i:]) + ")"
    return f"{sign}{whole}." + "".join(digits) + "..."


def to_mixed(f):
    """Mixed-number form of an improper fraction, or None if not applicable."""
    if f.is_int():
        return None
    whole, rem = divmod(abs(f.n), f.d)
    if whole == 0:
        return None
    return f"{'-' if f.n < 0 else ''}{whole} {rem}/{f.d}"


# ---------------------------------------------------------------------------
# Expression tree
# ---------------------------------------------------------------------------

class Num:
    __slots__ = ("value",)

    def __init__(self, value):
        self.value = value


class Neg:
    __slots__ = ("c",)

    def __init__(self, c):
        self.c = c


class Paren:
    __slots__ = ("c",)

    def __init__(self, c):
        self.c = c


class Bin:
    __slots__ = ("op", "l", "r")

    def __init__(self, op, l, r):
        self.op, self.l, self.r = op, l, r


# ---------------------------------------------------------------------------
# Reading the expression (tokenizer + parser)
# ---------------------------------------------------------------------------

DIGITS = "0123456789"


def tokenize(text):
    text = (text.replace("×", "*").replace("÷", "/").replace("−", "-")
                .replace("–", "-").replace("**", "^"))
    tokens, i = [], 0
    while i < len(text):
        c = text[i]
        if c.isspace():
            i += 1
        elif c in "+-*/^()":
            tokens.append((c, c, i))
            i += 1
        elif c in DIGITS or c == ".":
            j, dots = i, 0
            while j < len(text) and (text[j] in DIGITS or text[j] == "."):
                dots += text[j] == "."
                j += 1
            lit = text[i:j]
            if dots > 1 or lit == ".":
                raise MathError(f"'{lit}' is not a valid number (position {i + 1}).")
            tokens.append(("num", lit, i))
            i = j
        else:
            raise MathError(f"I don't understand '{c}' at position {i + 1}. "
                            "Version 1 supports numbers, + - * / ^ and parentheses.")
    return tokens


def parse_number(lit):
    whole, _, frac = lit.partition(".")
    return Frac(int((whole + frac) or "0"), 10 ** len(frac))


class Parser:
    """
    Grammar (lowest to highest precedence):
      expr  := term (('+' | '-') term)*
      term  := unary (('*' | '/') unary)*
      unary := '-' unary | '+' unary | power
      power := atom ('^' unary)?          (right-associative)
      atom  := number | '(' expr ')'
    """

    def __init__(self, tokens):
        self.toks = tokens
        self.i = 0
        self.decimals = []  # decimal literals we converted to fractions

    def peek(self):
        return self.toks[self.i][0] if self.i < len(self.toks) else "end"

    def next(self):
        tok = self.toks[self.i]
        self.i += 1
        return tok

    def parse(self):
        node = self.expr()
        if self.peek() != "end":
            kind, val, pos = self.toks[self.i]
            if kind == "(":
                raise MathError(f"Missing operator before '(' at position {pos + 1}. "
                                "Write multiplication explicitly, like 2 * (3 + 4).")
            if kind == ")":
                raise MathError(f"Unmatched ')' at position {pos + 1}.")
            raise MathError(f"I didn't expect '{val}' at position {pos + 1}. "
                            "Is an operator like + or * missing?")
        return node

    def expr(self):
        node = self.term()
        while self.peek() in ("+", "-"):
            op = self.next()[0]
            node = Bin(op, node, self.term())
        return node

    def term(self):
        node = self.unary()
        while self.peek() in ("*", "/"):
            op = self.next()[0]
            node = Bin(op, node, self.unary())
        return node

    def unary(self):
        if self.peek() == "-":
            self.next()
            c = self.unary()
            if isinstance(c, Num):
                return Num(Frac(-c.value.n, c.value.d))
            return Neg(c)
        if self.peek() == "+":
            self.next()
            return self.unary()
        return self.power()

    def power(self):
        base = self.atom()
        if self.peek() == "^":
            self.next()
            return Bin("^", base, self.unary())
        return base

    def atom(self):
        kind = self.peek()
        if kind == "num":
            _, lit, _ = self.next()
            value = parse_number(lit)
            if "." in lit:
                self.decimals.append((lit, value))
            return Num(value)
        if kind == "(":
            self.next()
            inner = self.expr()
            if self.peek() != ")":
                raise MathError("A parenthesis '(' is never closed. Add the missing ')'.")
            self.next()
            return Paren(inner)
        if kind == "end":
            raise MathError("The expression ends too early: something is missing at the end.")
        _, val, pos = self.toks[self.i]
        raise MathError(f"I expected a number or '(' but found '{val}' at position {pos + 1}.")


# ---------------------------------------------------------------------------
# Showing the expression as text
# ---------------------------------------------------------------------------

def fmt(node, parent_op=None, side=None):
    if isinstance(node, Num):
        v = node.value
        if parent_op is None:
            return str(v)
        if not v.is_int():
            return f"({v})"
        if v.n < 0 and (side == "right" or parent_op in ("^", "neg")):
            return f"({v})"
        return str(v)
    if isinstance(node, Neg):
        return "-" + fmt(node.c, "neg")
    if isinstance(node, Paren):
        return "(" + fmt(node.c) + ")"
    return f"{fmt(node.l, node.op, 'left')} {node.op} {fmt(node.r, node.op, 'right')}"


def sh(x):
    """Show a Frac inside a sentence: negatives and fractions get brackets."""
    if x.is_int():
        return f"({x.n})" if x.n < 0 else str(x.n)
    return f"({x.n}/{x.d})"


def ints(n):
    return f"({n})" if n < 0 else str(n)


def q(n, d):
    return f"({n}/{d})" if n < 0 else f"{n}/{d}"


# ---------------------------------------------------------------------------
# Doing the math, one explained step at a time
# ---------------------------------------------------------------------------

def tail(raw_n, raw_d, v):
    """Add a 'simplifies to' note when the raw result isn't in lowest terms."""
    if v.n != raw_n or v.d != raw_d:
        return f", which simplifies to {v}"
    return ""


def add_sub(a, b, sign):
    sym = "+" if sign > 0 else "-"
    verb = "Add" if sign > 0 else "Subtract"
    if a.is_int() and b.is_int():
        v = Frac(a.n + sign * b.n)
        return v, f"{verb}: {sh(a)} {sym} {sh(b)} = {v}"
    l = lcm(a.d, b.d)
    an, bn = a.n * (l // a.d), b.n * (l // b.d)
    raw_n = an + sign * bn
    v = Frac(raw_n, l)
    if a.d == b.d:
        text = f"{sh(a)} {sym} {sh(b)} = ({a.n} {sym} {ints(b.n)})/{l} = {raw_n}/{l}"
    else:
        text = (f"{sh(a)} {sym} {sh(b)}: the common bottom number is {l}. "
                f"{q(an, l)} {sym} {q(bn, l)} = {raw_n}/{l}")
    return v, f"{verb}: {text}{tail(raw_n, l, v)}"


def multiply(a, b):
    v = a * b
    if a.is_int() and b.is_int():
        return v, f"Multiply: {sh(a)} * {sh(b)} = {v}"
    rn, rd = a.n * b.n, a.d * b.d
    return v, (f"Multiply: {sh(a)} * {sh(b)}: multiply the tops and the bottoms: "
               f"{rn}/{rd}{tail(rn, rd, v)}")


def divide(a, b):
    if b.n == 0:
        raise MathError("Cannot divide by zero.")
    v = a / b
    if a.is_int() and b.is_int():
        text = f"Divide: {sh(a)} / {sh(b)} = {v}"
        if not v.is_int():
            g = gcd(a.n, b.n)
            text += (f" (divide top and bottom by {g})" if g > 1
                     else " (a fraction already in lowest terms)")
        return v, text
    recip = Frac(b.d, b.n)
    rn, rd = a.n * recip.n, a.d * recip.d
    return v, (f"Divide: {sh(a)} / {sh(b)}: dividing by a fraction means multiplying by "
               f"its flip, {sh(recip)}. {rn}/{rd}{tail(rn, rd, v)}")


def power(a, b):
    if not b.is_int():
        raise MathError("Only whole-number exponents are supported in version 1.")
    e = b.n
    if a.n == 0 and e == 0:
        raise MathError("0 to the power 0 is undefined.")
    v = a.pow_int(e)
    pe = f"({e})" if e < 0 else str(e)
    if e < 0:
        return v, (f"Power: a negative power means flip, then use the positive power: "
                   f"{sh(a)}^{pe} = 1/({sh(a)}^{-e}) = {v}")
    if e == 0:
        return v, f"Power: {sh(a)}^0 = 1 (any non-zero number to the power 0 is 1)"
    if e == 1:
        return v, f"Power: {sh(a)}^1 = {v}"
    if a.is_int():
        if 2 <= e <= 6 and abs(a.n) < 1000:
            return v, f"Power: {sh(a)}^{e} = " + " * ".join([sh(a)] * e) + f" = {v}"
        return v, f"Power: {sh(a)}^{e} = {v}"
    return v, f"Power: {sh(a)}^{e} = {ints(a.n)}^{e}/{a.d}^{e} = {v}"


def compute(node):
    if isinstance(node, Neg):
        x = node.c.value
        v = Frac(-x.n, x.d)
        return v, f"Apply the minus sign to {sh(x)}: {v}"
    a, b = node.l.value, node.r.value
    if node.op == "+":
        return add_sub(a, b, 1)
    if node.op == "-":
        return add_sub(a, b, -1)
    if node.op == "*":
        return multiply(a, b)
    if node.op == "/":
        return divide(a, b)
    return power(a, b)


def unwrap(node):
    """Remove parentheses that now contain just a number."""
    if isinstance(node, Paren):
        c = unwrap(node.c)
        return c if isinstance(c, Num) else Paren(c)
    if isinstance(node, Bin):
        return Bin(node.op, unwrap(node.l), unwrap(node.r))
    if isinstance(node, Neg):
        return Neg(unwrap(node.c))
    return node


def replace(node, target, new):
    if node is target:
        return new
    if isinstance(node, Bin):
        l, r = replace(node.l, target, new), replace(node.r, target, new)
        return node if (l is node.l and r is node.r) else Bin(node.op, l, r)
    if isinstance(node, (Neg, Paren)):
        c = replace(node.c, target, new)
        return node if c is node.c else type(node)(c)
    return node


def collect(node, depth, out):
    """Find every operation that is ready to be computed (all inputs are numbers)."""
    if isinstance(node, Bin):
        collect(node.l, depth, out)
        collect(node.r, depth, out)
        if isinstance(node.l, Num) and isinstance(node.r, Num):
            out.append((depth, node))
    elif isinstance(node, Neg):
        collect(node.c, depth, out)
        if isinstance(node.c, Num):
            out.append((depth, node))
    elif isinstance(node, Paren):
        collect(node.c, depth + 1, out)


def rank(node):
    """Lower rank is done first: powers, minus sign, then * and /, then + and -."""
    if isinstance(node, Neg):
        return 1
    return {"^": 0, "*": 2, "/": 2, "+": 3, "-": 3}[node.op]


def has_lower(node):
    if isinstance(node, Bin):
        return node.op in "*/+-" or has_lower(node.l) or has_lower(node.r)
    if isinstance(node, (Neg, Paren)):
        return has_lower(node.c)
    return False


def has_addsub(node):
    if isinstance(node, Bin):
        return node.op in "+-" or has_addsub(node.l) or has_addsub(node.r)
    if isinstance(node, (Neg, Paren)):
        return has_addsub(node.c)
    return False


def reason_for(node, depth, tree):
    if depth > 0:
        return "Work inside the parentheses first."
    if node is tree or isinstance(node, Neg):
        return None
    if node.op == "^" and has_lower(tree):
        return "Powers come before multiplication, division, addition and subtraction."
    if node.op in "*/" and has_addsub(tree):
        return "Multiplication and division come before addition and subtraction."
    return None


# ---------------------------------------------------------------------------
# Putting it together
# ---------------------------------------------------------------------------

class Step:
    def __init__(self, explanation, after, reason=None):
        self.explanation, self.after, self.reason = explanation, after, reason


class Solution:
    def __init__(self, expression, steps, answer):
        self.expression, self.steps, self.answer = expression, steps, answer

    def text(self):
        lines = [f"Problem: {self.expression}", ""]
        for i, st in enumerate(self.steps, 1):
            lines.append(f"Step {i}: {st.explanation}")
            if st.reason:
                lines.append(f"  Why: {st.reason}")
            lines.append(f"  Now: {st.after}")
        forms = [str(self.answer)]
        mixed = to_mixed(self.answer)
        if mixed:
            forms.append(mixed)
        if not self.answer.is_int():
            forms.append(to_decimal(self.answer))
        lines.append("")
        lines.append("Answer: " + " = ".join(forms))
        return "\n".join(lines)


def solve(text):
    if len(text) > 500:
        raise MathError("That expression is too long for this version (limit: 500 characters).")
    tokens = tokenize(text)
    if not tokens:
        raise MathError("Type an expression, for example: 2 + 3 * 4")
    parser = Parser(tokens)
    tree = unwrap(parser.parse())
    steps = []
    if parser.decimals:
        conv = ", ".join(f"{lit} = {val}" for lit, val in parser.decimals)
        steps.append(Step(f"Write the decimals as fractions so nothing gets rounded: {conv}",
                          fmt(tree)))
    for _ in range(2000):
        if isinstance(tree, Num):
            break
        ready = []
        collect(tree, 0, ready)
        best = min(range(len(ready)), key=lambda i: (-ready[i][0], rank(ready[i][1]), i))
        depth, node = ready[best]
        reason = reason_for(node, depth, tree)
        value, explanation = compute(node)
        tree = unwrap(replace(tree, node, Num(value)))
        steps.append(Step(explanation, fmt(tree), reason))
    else:
        raise MathError("That expression needs too many steps for this version.")
    return Solution(text.strip(), steps, tree.value)


def main():
    if len(sys.argv) > 1:
        lines = [" ".join(sys.argv[1:])]
    else:
        print("Math engine v1. Type an expression, or 'quit' to stop.")
        lines = None
    while True:
        if lines is not None:
            if not lines:
                break
            expr = lines.pop(0)
        else:
            try:
                expr = input("> ")
            except EOFError:
                break
            if expr.strip().lower() in ("quit", "exit"):
                break
            if not expr.strip():
                continue
        try:
            print(solve(expr).text())
        except MathError as err:
            print(f"Error: {err}")
        print()


if __name__ == "__main__":
    main()
