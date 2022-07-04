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

## 2. Call `qftarith.mult_const` directly ([`circuit_mult_q.py`](circuit_mult_q.py)

This example sets up *x* and *y* as above and generates a circuit by calling [qftarith.mult\_const](https://myqlm.github.io/qat-lang-arith.html#qat.lang.AQASM.qftarith.mult_const) directly:

```python
y.set_value(3)
prog.apply(qftarith.mult_const(reg_size,reg_size,constant), [y,x])
```

According to the documentation:

> "Builds a circuit performing a multiplication by a constant c. Only the content of the second register is changed:
>
> `|a>|b>` -> `|a>|b + a × c>`
>
> The multiplication is performed by a repeated additions of c into the second register. All additions, unless specified, are modulo where n is the size of the register holding the result."

This is an interesting description because the developers, it would seem, had two choices when implementing *b* + *a* × *c* - either add *a* *c* times to *b* or add *c* *a* times to *b*.  Given the value in *c* is a classical integer and therefore easily understood, while *a* is a qubit and therefore a superposition state, it is conceptually easier to go with the first option. Unfortunately, the documentation claims the second and because myQLM is obstinently closed source, it is impossible to see what they have done.

Either way it does not work:

```
State [qft arith]: |0>|3>
```

What's interesting here is that it's a different wrong answer from before.

As part of this process the code prints out cicuit diagram and one of the things I noticed is that when setting the values of *y* to 3, it is setting the furthermost qubits:

```
    ┌───────────────────┐  
────┤                   ├  
    │                   │  
    │                   │  
    │                   │  
────┤                   ├  
    │                   │  
    │                   │  
    │                   │  
────┤                   ├  
    │                   │  
    │                   │  
    │                   │  
────┤                   ├  
    │                   │  
    │                   │  
    │                   │  
────┤                   ├  
    │                   │  
    │                   │  
    │                   │  
────┤MULT_CONST[6, 6, 2]├  
    │                   │  
    │                   │  
    │                   │  
────┤                   ├  
    │                   │  
    │                   │  
    │                   │  
────┤                   ├  
    │                   │  
    │                   │  
    │                   │  
────┤                   ├  
    │                   │  
    │                   │  
    │                   │  
────┤                   ├  
    │                   │  
    │                   │  
 ┌─┐│                   │  
─┤X├┤                   ├  
 └─┘│                   │  
    │                   │  
 ┌─┐│                   │  
─┤X├┤                   ├  
 └─┘└───────────────────┘      

```

This started me thinking about little vs big endian issues.

## 3. Working out (qu)bit order ([`circuit_add_q.py`](circuit_add_q.py), [`circuit_mult_q_r.py`](circuit_mult_q_r.py))

This cicuit allocates *x* and *y* but allocates *x* with a reversed bit order, and then adds 2 to each of those values with [qftarith.add\_const](https://myqlm.github.io/qat-lang-arith.html#qat.lang.AQASM.qftarith.add_const).

```python

# allocate two registers, x and y
x = prog.qalloc(reg_size, QInt, reverse_bit_order=True)
y = prog.qalloc(reg_size, QInt)

# y = 3, x = 3
y.set_value(3)
x.set_value(3)

# add constant to each
prog.apply(qftarith.add_const(reg_size,constant), [x])
prog.apply(qftarith.add_const(reg_size,constant), [y])

``` 

The output is:

```
State [qft arith]: |5>|19>
```

This tells us that for `qftarith` to work at all, we need our `Qint`s to be reversed.  Applying this to 2. gives us [`circuit_mult_q_r.py`](circuit_mult_q_r.py) which gives us the same answer as the over-loaded version when run:

```
State [qft arith]: |2>|3>
```



