### Information

- **Qiskit Aer version**: 0.10.4 
- **Python version**: 3.9.12, 3.9.10
- **Operating system**: Ubuntu 20.04, RHEL 7.x

### What is the current behavior?

Qiskit seg-faults when trying to execute the examples of the extended stabilizer tutorial (https://qiskit.org/documentation/stable/0.19/tutorials/simulators/6_extended_stabilizer_tutorial.html) at qubits >=40, regardless of whether I use the "extended stabilizer" simulator or the "state vector" simulator.  I have tested this on two systems, with three different installs of Qiskit:

1. Ubuntu 20.04 with conda envs for Qiskit 0.36.2 and Qiskit 0.37.1, 8GB of RAM (VM on my laptop)
2. RHEL 7 with virtualenv with Qiskit 0.36.2 and 192GB of RAM (cluster login node).

Both seem to have the same Qiskit Aer version, according to `qiskit.__version__`

Both are installed from pypi via pip.

When running the code in Jupyter from the tutorial, the kernel dies on boxes 3/4.  With the code isolated into scripts (see "Steps to reproduce the problem" below) it seems to "work" for 39 qubits but segfault on 40, almost immediately, before any work is done.

```
$ python3 test_ext.py 39
39
This succeeded?: True
$ python3 test_ext.py 40
40
Segmentation fault (core dumped)
$ python3 test_sv.py 39
39
This succeeded?: True
$ python3 test_sv.py 40
40
Segmentation fault (core dumped)
```

Experimentation with `print` statements show the issue is this line:

```python
es_job = QasmSimulator().run(qob, backend_options={
    'method': 'extended_stabilizer'
})
```

What is confusing to me, is that the behaviour is the same regardless of what I put in `method`.  Has something changed in the way Qiskit selects a method since 2020 when that tutorial was written?

### Steps to reproduce the problem

Initially when I tried to run the notebook example at the above link, I used Jupyter and this threw an error saying the kernel had died at the third/forth boxes i.e.

```python
statevector_job = QasmSimulator().run(qobj, backend_options={
    'method': 'statevector'
})
# This should error!
try:
    statevector_job.result()
except AerError as err:
    print(err)
```

and

```python
es_job = QasmSimulator().run(qobj, backend_options={
    'method': 'extended_stabilizer'
})
result = es_job.result()
print('This succeeded?: {}'.format(result.success))
```

I took the code out and put it into a pair of python scripts as follows:

**test_sv.py**
```python
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit.compiler import assemble
from qiskit.providers.aer import AerError, QasmSimulator
from qiskit.tools.visualization import plot_histogram
import sys
import random   

upper_limit=39
if len(sys.argv) > 1:
   upper_limit = int(sys.argv[1])

print(upper_limit)
circ = QuantumCircuit(upper_limit, upper_limit)

# Initialise with a Hadamard layer
circ.h(range(upper_limit))
# Apply some random CNOT and T gates
qubit_indices = [i for i in range(upper_limit)]
for i in range(10):
   control, target, t = random.sample(qubit_indices, 3)
   circ.cx(control, target)
   circ.t(t)
circ.measure(range(upper_limit), range(upper_limit))

qobj = assemble(circ, backend=QasmSimulator(), shots=1)

es_job = QasmSimulator().run(qobj, backend_options={
        'method': 'statevector'
        })
result = es_job.result()
print('This succeeded?: {}'.format(result.success))
```

**test_ext.py**
```python
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit.compiler import assemble
from qiskit.providers.aer import AerError, QasmSimulator
from qiskit.tools.visualization import plot_histogram
import sys
import random   

upper_limit=39
if len(sys.argv) > 1:
   upper_limit = int(sys.argv[1])

print(upper_limit)
circ = QuantumCircuit(upper_limit, upper_limit)

# Initialise with a Hadamard layer
circ.h(range(upper_limit))
# Apply some random CNOT and T gates
qubit_indices = [i for i in range(upper_limit)]
for i in range(10):
   control, target, t = random.sample(qubit_indices, 3)
   circ.cx(control, target)
   circ.t(t)
circ.measure(range(upper_limit), range(upper_limit))

qobj = assemble(circ, backend=QasmSimulator(), shots=1)

es_job = QasmSimulator().run(qobj, backend_options={
        'method': 'extended_stabilizer'
        })
result = es_job.result()
print('This succeeded?: {}'.format(result.success))
```

Running each script with an argument sets the number of qubits, e.g.

```
$ python3 test_ext.py 20
20
This succeeded?: True
```

runs the extended stabilizer version with 20 qubits

To see the behaviour:

```
$ python3 test_ext.py 39
39
This succeeded?: True
$ python3 test_ext.py 40
40
Segmentation fault (core dumped)
$ python3 test_sv.py 39
39
This succeeded?: True
$ python3 test_sv.py 40
40
Segmentation fault (core dumped)
```

### What is the expected behavior?

Running `python3 test_ext.py 40` should output:

```
40
This succeeded?: True
```
