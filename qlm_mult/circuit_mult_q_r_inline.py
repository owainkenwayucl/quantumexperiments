# Investigating issues spotted by a colleague with library math functions
# in MyQLM

# This program fails with a mysterious arity problem....
from qat.lang.AQASM import Program
from qat.lang.AQASM.qint import QInt
import qat.lang.AQASM.qftarith as qftarith
import qat.lang.AQASM.classarith as classarith
from qat.qpus import PyLinalg
from qat.core.console import display

# Some settings
reg_size = 6
constant = 2

prog = Program()

# allocate two registers, x and y
x = prog.qalloc(reg_size, QInt, reverse_bit_order=True)
y = prog.qalloc(reg_size, QInt, reverse_bit_order=True)

# y = 3, x = 2*y
y.set_value(3)
gate = (~qftarith.mult_const)(reg_size,reg_size,constant)
prog.apply(gate, [y,x])

# Use the most basic, on computer linear algebra engine.
qpu = PyLinalg()

# Create the circuit.
circ_q = prog.to_circ(link=[qftarith])

# This is probably boring as we can't inline operators?
display(circ_q)

# Run the circuits
job_q = circ_q.to_job()

result_q = qpu.submit(job_q)

# Print the results.
for sample in result_q:
	print("State [qft arith]: {}".format(sample.state))
