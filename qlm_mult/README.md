# QLM multiplication experiments.

A couple of weeks ago I got forwarded a chain of emails from a researcher who was having difficulty getting QLM to do what he expected when he multiplied a `Qint` by an integer.

MyQLM claims to be able to do this both as part of `qftarith` package with [qftarith.mult\_const](https://myqlm.github.io/qat-lang-arith.html#qat.lang.AQASM.qftarith.mult_const), and by operator overloading. As we will see from these examples, this is not the case.

## Background:

I am a long term programmer of classical computers.  I have been on some courses of programming quantum machines and have used both (my)QLM and QISKIT to write small systems.  I am extremely far from an expert however.  I've documented this mainly to show how I tried to reason my way through the problem, particularly when we have a piece of software which is closed source (MyQLM) and cannot inspect its inner workings.  Maybe this is of help to others.  In addition to the stuff described here, I *also* re-implemented some of this in QISKIT, to try and reason about why MyQLM was behaving as it was (in particular in step 6, there is an equivalent function in QISKIT), and before I had the big/little endian stuff worked out I did a lot of work manually setting wires rather than using `Qint`s to see what was going on.  Maybe I'll add these parts at a later date.  Or maybe not.

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

This is an interesting description because the developers, it would seem, had two choices when implementing *b* + *a* × *c* - either add *a* *c* times to *b* or add *c* *a* times to *b*.  Given the value in *c* is a classical integer and therefore easily understood, while *a* is a qubit and therefore a superposition state, it is conceptually easier to go with the first option. Unfortunately, the documentation claims the second and because MyQLM is obstinently closed source, it is impossible to see what they have done.

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

That's pretty interesting in and of itself because we are somehow getting an arity of 8 out of calling it with `reg_size,reg_size` where `reg_size` = 6, and *all we have changed* is that we are now inlining instead of accepting the abstract gate.  If we fudge it by adding 4 to the arity of the first register [`circuit_mult_q_r_inline_fudge.py`](circuit_mult_q_r_inline_fudge.py), we get a circuit diagram which is clearly way to simple to be correct, as it consists of a QFT, a phase by π and a reverse QFT:

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

## 6. Making *c* a `Qint` ([`circuit_q_r_register.py`](circuit_q_r_register.py), [`circuit_q_r_register_noinline.py`](circuit_q_r_register_noinline.py))

Because MyQLM is closed source it is impossible to see what the `mult_const` routine is doing and so I took a look at implementing the problem in QISKIT to see if I could replicate the behaviour. The guide I found to multiplying numbers with the equivalent routine set wires directly (it's not clear to me if QISKIT has an equivalent of `Qint` but I didn't look very hard) and in fact effectively multiplied two `Qint`s together.  So I thought it was worth a shot in MyQLM.  To multiply two `Qint` "registers" together you use  [qftarith.mult](https://myqlm.github.io/qat-lang-arith.html#qat.lang.AQASM.qftarith.mult):

```python
x = prog.qalloc(ans_size, QInt, reverse_bit_order=True)
y = prog.qalloc(reg_size, QInt, reverse_bit_order=True)
c = prog.qalloc(reg_size, QInt, reverse_bit_order=True)

# y = 3, x = c*y
y.set_value(3)
c.set_value(constant)
gate = (~qftarith.mult)(reg_size,reg_size, ans_size)
prog.apply(gate, [c,y,x])

```

When we run this, we get both a satisfyingly complex circuit diagram, and the correct answer:

```
 ┌──────┐                                                                                                                                                                             ┌─────┐                                                                                                                                                                                                                                                                     ┌───────┐                 
─┤      ├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤PH[π]├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤       ├                 
 │      │                                                                                                                                                                             └┬────┘                                                                                                                                                                                                                                                                     │       │                 
 │      │                                                                                                                                                                              │                                                                                                                                                                                                                                                                          │       │                 
 │      │                                                                                                                                                             ┌─────┐┌───────┐ │                                                                                                                       ┌─────┐                                                                                                                                            │       │                 
─┤      ├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤PH[π]├┤PH[π/2]├─┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤PH[π]├────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤       ├                 
 │      │                                                                                                                                                             └┬────┘└┬──────┘ │                                                                                                                       └┬────┘                                                                                                                                            │       │                 
 │      │                                                                                                                                                              │      │        │                                                                                                                        │                                                                                                                                                 │       │                 
 │      │                                                                                                                                    ┌─────┐┌───────┐┌───────┐ │      │        │                                                                                                       ┌─────┐┌───────┐ │                                                                           ┌─────┐                                                               │       │                 
─┤QFT[6]├────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤PH[π]├┤PH[π/2]├┤PH[π/4]├─┼──────┼────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────┤PH[π]├┤PH[π/2]├─┼───────────────────────────────────────────────────────────────────────────┤PH[π]├───────────────────────────────────────────────────────────────┤QFT†[6]├                 
 │      │                                                                                                                                    └┬────┘└┬──────┘└┬──────┘ │      │        │                                                                                                       └┬────┘└┬──────┘ │                                                                           └┬────┘                                                               │       │                 
 │      │                                                                                                                                     │      │        │        │      │        │                                                                                                        │      │        │                                                                            │                                                                    │       │                 
 │      │                                                                                                  ┌─────┐┌───────┐┌───────┐┌───────┐ │      │        │        │      │        │                                                                              ┌─────┐┌───────┐┌───────┐ │      │        │                                                           ┌─────┐┌───────┐ │                                         ┌─────┐                    │       │                 
─┤      ├──────────────────────────────────────────────────────────────────────────────────────────────────┤PH[π]├┤PH[π/2]├┤PH[π/4]├┤PH[π/8]├─┼──────┼────────┼────────┼──────┼────────┼──────────────────────────────────────────────────────────────────────────────┤PH[π]├┤PH[π/2]├┤PH[π/4]├─┼──────┼────────┼───────────────────────────────────────────────────────────┤PH[π]├┤PH[π/2]├─┼─────────────────────────────────────────┤PH[π]├────────────────────┤       ├                 
 │      │                                                                                                  └┬────┘└┬──────┘└┬──────┘└┬──────┘ │      │        │        │      │        │                                                                              └┬────┘└┬──────┘└┬──────┘ │      │        │                                                           └┬────┘└┬──────┘ │                                         └┬────┘                    │       │                 
 │      │                                                                                                   │      │        │        │        │      │        │        │      │        │                                                                               │      │        │        │      │        │                                                            │      │        │                                          │                         │       │                 
 │      │                                                      ┌─────┐┌───────┐┌───────┐┌───────┐┌────────┐ │      │        │        │        │      │        │        │      │        │                                            ┌─────┐┌───────┐┌───────┐┌───────┐ │      │        │        │      │        │                                  ┌─────┐┌───────┐┌───────┐ │      │        │                         ┌─────┐┌───────┐ │                ┌─────┐  │       │                 
─┤      ├──────────────────────────────────────────────────────┤PH[π]├┤PH[π/2]├┤PH[π/4]├┤PH[π/8]├┤PH[π/16]├─┼──────┼────────┼────────┼────────┼──────┼────────┼────────┼──────┼────────┼────────────────────────────────────────────┤PH[π]├┤PH[π/2]├┤PH[π/4]├┤PH[π/8]├─┼──────┼────────┼────────┼──────┼────────┼──────────────────────────────────┤PH[π]├┤PH[π/2]├┤PH[π/4]├─┼──────┼────────┼─────────────────────────┤PH[π]├┤PH[π/2]├─┼────────────────┤PH[π]├──┤       ├                 
 │      │                                                      └┬────┘└┬──────┘└┬──────┘└┬──────┘└┬───────┘ │      │        │        │        │      │        │        │      │        │                                            └┬────┘└┬──────┘└┬──────┘└┬──────┘ │      │        │        │      │        │                                  └┬────┘└┬──────┘└┬──────┘ │      │        │                         └┬────┘└┬──────┘ │                └┬────┘  │       │                 
 │      │                                                       │      │        │        │        │         │      │        │        │        │      │        │        │      │        │                                             │      │        │        │        │      │        │        │      │        │                                   │      │        │        │      │        │                          │      │        │                 │       │       │                 
 │      │┌─────┐┌───────┐┌───────┐┌───────┐┌────────┐┌────────┐ │      │        │        │        │         │      │        │        │        │      │        │        │      │        │┌─────┐┌───────┐┌───────┐┌───────┐┌────────┐ │      │        │        │        │      │        │        │      │        │┌─────┐┌───────┐┌───────┐┌───────┐ │      │        │        │      │        │┌─────┐┌───────┐┌───────┐ │      │        │┌─────┐┌───────┐ │┌─────┐│       │                 
─┤      ├┤PH[π]├┤PH[π/2]├┤PH[π/4]├┤PH[π/8]├┤PH[π/16]├┤PH[π/32]├─┼──────┼────────┼────────┼────────┼─────────┼──────┼────────┼────────┼────────┼──────┼────────┼────────┼──────┼────────┼┤PH[π]├┤PH[π/2]├┤PH[π/4]├┤PH[π/8]├┤PH[π/16]├─┼──────┼────────┼────────┼────────┼──────┼────────┼────────┼──────┼────────┼┤PH[π]├┤PH[π/2]├┤PH[π/4]├┤PH[π/8]├─┼──────┼────────┼────────┼──────┼────────┼┤PH[π]├┤PH[π/2]├┤PH[π/4]├─┼──────┼────────┼┤PH[π]├┤PH[π/2]├─┼┤PH[π]├┤       ├                 
 └──────┘└┬────┘└┬──────┘└┬──────┘└┬──────┘└┬───────┘└┬───────┘ │      │        │        │        │         │      │        │        │        │      │        │        │      │        │└┬────┘└┬──────┘└┬──────┘└┬──────┘└┬───────┘ │      │        │        │        │      │        │        │      │        │└┬────┘└┬──────┘└┬──────┘└┬──────┘ │      │        │        │      │        │└┬────┘└┬──────┘└┬──────┘ │      │        │└┬────┘└┬──────┘ │└┬────┘└───────┘                 
          │      │        │        │        │         │         │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │      │        │        │      │        │ │      │        │        │      │        │ │      │        │ │                               
 ┌─┐      │      │        │        │        │         │         │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │      │        │        │      │        │ │      │        │        │      │        │ │      │        │ │                               
─┤X├──────●──────●────────●────────●────────●─────────●─────────●──────●────────●────────●────────●─────────●──────●────────●────────●────────●──────●────────●────────●──────●────────●─┼──────┼────────┼────────┼────────┼─────────┼──────┼────────┼────────┼────────┼──────┼────────┼────────┼──────┼────────┼─┼──────┼────────┼────────┼────────┼──────┼────────┼────────┼──────┼────────┼─┼──────┼────────┼────────┼──────┼────────┼─┼──────┼────────┼─┼──────────────                 
 └─┘      │      │        │        │        │         │         │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │      │        │        │      │        │ │      │        │        │      │        │ │      │        │ │                               
          │      │        │        │        │         │         │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │      │        │        │      │        │ │      │        │        │      │        │ │      │        │ │                               
 ┌─┐      │      │        │        │        │         │         │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │      │        │        │      │        │ │      │        │        │      │        │ │      │        │ │                               
─┤X├──────┼──────┼────────┼────────┼────────┼─────────┼─────────┼──────┼────────┼────────┼────────┼─────────┼──────┼────────┼────────┼────────┼──────┼────────┼────────┼──────┼────────┼─●──────●────────●────────●────────●─────────●──────●────────●────────●────────●──────●────────●────────●──────●────────●─┼──────┼────────┼────────┼────────┼──────┼────────┼────────┼──────┼────────┼─┼──────┼────────┼────────┼──────┼────────┼─┼──────┼────────┼─┼──────────────                 
 └─┘      │      │        │        │        │         │         │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │      │        │        │      │        │ │      │        │        │      │        │ │      │        │ │                               
          │      │        │        │        │         │         │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │      │        │        │      │        │ │      │        │        │      │        │ │      │        │ │                               
          │      │        │        │        │         │         │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │      │        │        │      │        │ │      │        │        │      │        │ │      │        │ │                               
──────────┼──────┼────────┼────────┼────────┼─────────┼─────────┼──────┼────────┼────────┼────────┼─────────┼──────┼────────┼────────┼────────┼──────┼────────┼────────┼──────┼────────┼─┼──────┼────────┼────────┼────────┼─────────┼──────┼────────┼────────┼────────┼──────┼────────┼────────┼──────┼────────┼─●──────●────────●────────●────────●──────●────────●────────●──────●────────●─┼──────┼────────┼────────┼──────┼────────┼─┼──────┼────────┼─┼──────────────                 
          │      │        │        │        │         │         │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │      │        │        │      │        │ │      │        │        │      │        │ │      │        │ │                               
          │      │        │        │        │         │         │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │      │        │        │      │        │ │      │        │        │      │        │ │      │        │ │                               
          │      │        │        │        │         │         │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │      │        │        │      │        │ │      │        │        │      │        │ │      │        │ │                               
──────────┼──────┼────────┼────────┼────────┼─────────┼─────────┼──────┼────────┼────────┼────────┼─────────┼──────┼────────┼────────┼────────┼──────┼────────┼────────┼──────┼────────┼─┼──────┼────────┼────────┼────────┼─────────┼──────┼────────┼────────┼────────┼──────┼────────┼────────┼──────┼────────┼─┼──────┼────────┼────────┼────────┼──────┼────────┼────────┼──────┼────────┼─●──────●────────●────────●──────●────────●─┼──────┼────────┼─┼──────────────                 
          │      │        │        │        │         │         │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │      │        │        │      │        │ │      │        │        │      │        │ │      │        │ │                               
          │      │        │        │        │         │         │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │      │        │        │      │        │ │      │        │        │      │        │ │      │        │ │                               
          │      │        │        │        │         │         │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │      │        │        │      │        │ │      │        │        │      │        │ │      │        │ │                               
──────────┼──────┼────────┼────────┼────────┼─────────┼─────────┼──────┼────────┼────────┼────────┼─────────┼──────┼────────┼────────┼────────┼──────┼────────┼────────┼──────┼────────┼─┼──────┼────────┼────────┼────────┼─────────┼──────┼────────┼────────┼────────┼──────┼────────┼────────┼──────┼────────┼─┼──────┼────────┼────────┼────────┼──────┼────────┼────────┼──────┼────────┼─┼──────┼────────┼────────┼──────┼────────┼─●──────●────────●─┼──────────────                 
          │      │        │        │        │         │         │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │      │        │        │      │        │ │      │        │        │      │        │ │      │        │ │                               
          │      │        │        │        │         │         │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │      │        │        │      │        │ │      │        │        │      │        │ │      │        │ │                               
          │      │        │        │        │         │         │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │      │        │        │      │        │ │      │        │        │      │        │ │      │        │ │                               
──────────┼──────┼────────┼────────┼────────┼─────────┼─────────┼──────┼────────┼────────┼────────┼─────────┼──────┼────────┼────────┼────────┼──────┼────────┼────────┼──────┼────────┼─┼──────┼────────┼────────┼────────┼─────────┼──────┼────────┼────────┼────────┼──────┼────────┼────────┼──────┼────────┼─┼──────┼────────┼────────┼────────┼──────┼────────┼────────┼──────┼────────┼─┼──────┼────────┼────────┼──────┼────────┼─┼──────┼────────┼─●──────────────                 
          │      │        │        │        │         │         │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │      │        │        │      │        │ │      │        │        │      │        │ │      │        │ │                               
          │      │        │        │        │         │         │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │      │        │        │      │        │ │      │        │        │      │        │ │      │        │ │                               
          │      │        │        │        │         │         │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │         │      │        │        │        │      │        │        │      │        │ │      │        │        │        │      │        │        │      │        │ │      │        │        │      │        │ │      │        │ │                               
──────────┼──────┼────────┼────────┼────────┼─────────●─────────┼──────┼────────┼────────┼────────●─────────┼──────┼────────┼────────●────────┼──────┼────────●────────┼──────●────────●─┼──────┼────────┼────────┼────────●─────────┼──────┼────────┼────────●────────┼──────┼────────●────────┼──────●────────●─┼──────┼────────┼────────●────────┼──────┼────────●────────┼──────●────────●─┼──────┼────────●────────┼──────●────────●─┼──────●────────●─●──────────────                 
          │      │        │        │        │                   │      │        │        │                  │      │        │                 │      │                 │                 │      │        │        │                  │      │        │                 │      │                 │                 │      │        │                 │      │                 │                 │      │                 │                 │                                                 
          │      │        │        │        │                   │      │        │        │                  │      │        │                 │      │                 │                 │      │        │        │                  │      │        │                 │      │                 │                 │      │        │                 │      │                 │                 │      │                 │                 │                                                 
 ┌─┐      │      │        │        │        │                   │      │        │        │                  │      │        │                 │      │                 │                 │      │        │        │                  │      │        │                 │      │                 │                 │      │        │                 │      │                 │                 │      │                 │                 │                                                 
─┤X├──────┼──────┼────────┼────────┼────────●───────────────────┼──────┼────────┼────────●──────────────────┼──────┼────────●─────────────────┼──────●─────────────────●─────────────────┼──────┼────────┼────────●──────────────────┼──────┼────────●─────────────────┼──────●─────────────────●─────────────────┼──────┼────────●─────────────────┼──────●─────────────────●─────────────────┼──────●─────────────────●─────────────────●────────────────────────────────                 
 └─┘      │      │        │        │                            │      │        │                           │      │                          │                                          │      │        │                           │      │                          │                                          │      │                          │                                          │                                                                                            
          │      │        │        │                            │      │        │                           │      │                          │                                          │      │        │                           │      │                          │                                          │      │                          │                                          │                                                                                            
          │      │        │        │                            │      │        │                           │      │                          │                                          │      │        │                           │      │                          │                                          │      │                          │                                          │                                                                                            
──────────┼──────┼────────┼────────●────────────────────────────┼──────┼────────●───────────────────────────┼──────●──────────────────────────●──────────────────────────────────────────┼──────┼────────●───────────────────────────┼──────●──────────────────────────●──────────────────────────────────────────┼──────●──────────────────────────●──────────────────────────────────────────●───────────────────────────────────────────────────────────────────────────                 
          │      │        │                                     │      │                                    │                                                                            │      │                                    │                                                                            │                                                                                                                                                                         
          │      │        │                                     │      │                                    │                                                                            │      │                                    │                                                                            │                                                                                                                                                                         
          │      │        │                                     │      │                                    │                                                                            │      │                                    │                                                                            │                                                                                                                                                                         
──────────┼──────┼────────●─────────────────────────────────────┼──────●────────────────────────────────────●────────────────────────────────────────────────────────────────────────────┼──────●────────────────────────────────────●────────────────────────────────────────────────────────────────────────────●────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────                 
          │      │                                              │                                                                                                                        │                                                                                                                                                                                                                                                                                                  
          │      │                                              │                                                                                                                        │                                                                                                                                                                                                                                                                                                  
          │      │                                              │                                                                                                                        │                                                                                                                                                                                                                                                                                                  
──────────┼──────●──────────────────────────────────────────────●────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────●─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────                 
          │                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 
          │                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 
          │                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 
──────────●────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────                 

```

Output:

```
State [qft arith]: |6>|3>|2>
```

There is a version without the inlining [`circuit_q_r_register_noinline.py`](circuit_q_r_register_noinline.py), and this also works as expected.


## Conclusions

Well obviously as a massively old-fashioned classical programmer I can't exclude the possibility that [qftarith.mult\_const](https://myqlm.github.io/qat-lang-arith.html#qat.lang.AQASM.qftarith.mult_const) is fine and it is me that is wrong, but I personally suspect a bug.  Here is my reasoning.

1. The biggest smoking gun is arity changing when we in-line.  This definitely means something is broken.
2. The implementation is inverted, doing *a* additions of *c* rather than the other way around.  Implementing it the more intuitive way gives the correct answer.
3. Using 2 `Qint`s gives the correct answer.

It's hard to tell how this is implemented when it is closed source.  I did take a look in my python library directory and bafflingly, the *python* code is distributed as (presumably `.pyc` bytecode inside) `.so` files, something I didn't even know you could do.  Theoretically it would be possible to extract somewhat readable python from that but I'm not really keen on going that far.  I'd rather just... use QISKIT which is properly Open Source.

You can replicate all of this by setting wires directly, with an `X` gate which was interesting when working out the little vs big endian stuff.  It's not clear to me why the math library is one while the `Qint` representation is the other but again, that's a bit problematic.  Finally, I found that there is a serouse lack of documentation and useful example code in the MyQLM release.  For example, I did not find anything clear on writing Qroutines/AbsttractGates and so when writing my own multiplier, I fudged it a lot.
