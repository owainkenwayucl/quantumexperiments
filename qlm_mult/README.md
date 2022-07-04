# QLM multiplication experiments.

A couple of weeks ago I got forwarded a chain of emails from a researcher who was having difficulty getting QLM to do what he expected when he multiplied a `Qint` by an integer.

MyQLM claims to be able to do this both as part of `qftarith` package with [qftarith.mult\_const](https://myqlm.github.io/qat-lang-arith.html#qat.lang.AQASM.qftarith.mult_const), and by operator overloading. As we will see from these examples, this is not the case.

## 1. Operator overloading ([`basic_mult.py`](basic_mult.py))

This example allocates `Qint`s (*x* and *y*) and then sets *y* = 3 and *x* += 2 * *y*.  The "+" in the "+=" is important because according to the documentation if we leave it out nothing happens.

It generates and runs two circuits - one linking against the `qftarith` library and one linking against the classical `classarith` library.

What we expect as output is `|6>|3>` aka a state that represents *x* = 6, *y* = 3.  What we get when linked against `qftarith` is `|2>|3>`.  The `classarith` variant behaves as expected (note the **Anc**illiary qubits allocated).

```
State [qft arith]: |2>|3>
State [classical arith]: |6>|3>|Anc:000>
```
