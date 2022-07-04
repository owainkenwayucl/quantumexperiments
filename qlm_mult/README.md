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

## 2. Call `qftarith.mult_const` directly ([`circuit_mult_q.py`](circuit_mult_q.py))

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

## 4. Write our own multiplication routine ([`qlm_math.py`](qlm_math.py), [`circuit_q_r_mylib.py`](circuit_q_r_mylib.py))

This code implements our own multiply routine (`looped_add`) which for `|a>|b>` -> `|a>|b + a × c>` implements it as `c` [qftarith.add\_const](https://myqlm.github.io/qat-lang-arith.html#qat.lang.AQASM.qftarith.add_const) additions of `a` to `b`.

This generates both the expected circuit diagram and answer:

```
    ┌─────────┐┌─────────┐ 
────┤         ├┤         ├ 
    │         ││         │ 
    │         ││         │ 
    │         ││         │ 
────┤         ├┤         ├ 
    │         ││         │ 
    │         ││         │ 
    │         ││         │ 
────┤         ├┤         ├ 
    │         ││         │ 
    │         ││         │ 
    │         ││         │ 
────┤         ├┤         ├ 
    │         ││         │ 
    │         ││         │ 
    │         ││         │ 
────┤         ├┤         ├ 
    │         ││         │ 
    │         ││         │ 
    │         ││         │ 
────┤ADD[6, 6]├┤ADD[6, 6]├ 
    │         ││         │ 
    │         ││         │ 
 ┌─┐│         ││         │ 
─┤X├┤         ├┤         ├ 
 └─┘│         ││         │ 
    │         ││         │ 
 ┌─┐│         ││         │ 
─┤X├┤         ├┤         ├ 
 └─┘│         ││         │ 
    │         ││         │ 
    │         ││         │ 
────┤         ├┤         ├ 
    │         ││         │ 
    │         ││         │ 
    │         ││         │ 
────┤         ├┤         ├ 
    │         ││         │ 
    │         ││         │ 
    │         ││         │ 
────┤         ├┤         ├ 
    │         ││         │ 
    │         ││         │ 
    │         ││         │ 
────┤         ├┤         ├ 
    └─────────┘└─────────┘ 

```

Output:

```
State [kenway arith]: |6>|3>
```

This makes me very suspicious about what [qftarith.mult\_const](https://myqlm.github.io/qat-lang-arith.html#qat.lang.AQASM.qftarith.mult_const) is doing...

## 5. Try to see inside `qftarith.mult_const`.

One of the features describbed in the documentation is that you can see inside some of these complex gates by inlining them, using `~`.  I tried to do this in [`circuit_mult_q_r_inline.py`](circuit_mult_q_r_inline.py):

```python
# y = 3, x = 2*y
y.set_value(3)
gate = (~qftarith.mult_const)(reg_size,reg_size,constant)
prog.apply(gate, [y,x])

```

This however crashes when run throwing an arity error:

```
(ql2) lab@phobos:~/Source/quantumexperiments/qlm_mult$ python3 circuit_mult_q_r_inline.py
Traceback (most recent call last):
  File "/home/lab/Source/quantumexperiments/qlm_mult/circuit_mult_q_r_inline.py", line 25, in <module>
    prog.apply(gate, [y,x])
  File "program.py", line 193, in qat.lang.AQASM.program.Program.apply
  File "operations.py", line 70, in qat.lang.AQASM.operations.QGateOperation.__init__
  File "aqasm_util.py", line 135, in qat.lang.AQASM.aqasm_util.sanity
qat.lang.AQASM.aqasm_util.InvalidGateArguments: Gate None of arity 8 cannot be applied on [q[6],q[7],q[8],q[9],q[10],q[11],q[0],q[1],q[2],q[3],q[4],q[5]]
```

That's pretty interesting in and of itself because we are somehow getting an arity of 8 out of calling it with `reg_size,reg_size` where `reg_size` = 6, and *all we have changed* is that we are no inlining instead of accepting tthe abstract gate.  If we fudge it by adding 4 to the arity of the first register [`circuit_mult_q_r_inline_fudge.py`](circuit_mult_q_r_inline_fudge.py), we get a circuit diagram which is clearly way to simple to be correct, as it consists of a QFT, a phase by π and a reverse QFT:

```
                                                                                                                                                                                                                   
───────────────────────── 
                          
                          
                          
───────────────────────── 
                          
                          
                          
───────────────────────── 
                          
                          
                          
───────────────────────── 
                          
                          
 ┌──────┐       ┌───────┐ 
─┤QFT[2]├───────┤QFT†[2]├ 
 │      │       │       │ 
 │      │       │       │ 
 │      │┌─────┐│       │ 
─┤      ├┤PH[π]├┤       ├ 
 └──────┘└┬────┘└───────┘ 
          │               
 ┌─┐      │               
─┤X├──────●────────────── 
 └─┘                      
                          
 ┌─┐                      
─┤X├───────────────────── 
 └─┘                      
                          
                          
───────────────────────── 
                          
                          
                          
───────────────────────── 
                          
                          
                          
───────────────────────── 
                          
                          
                          
─────────────────────────  
```


