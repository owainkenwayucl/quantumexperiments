# Investigating issues spotted by a colleague with library math functions
# in MyQLM
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
x = prog.qalloc(reg_size, QInt)
y = prog.qalloc(reg_size, QInt)

# y = 3, x = 2*y
y.set_value(3)
prog.apply(classarith.mult_const(reg_size,reg_size,constant), [y,x])

# Use the most basic, on computer linear algebra engine.
qpu = PyLinalg()

# Create the circuit.
circ_c = prog.to_circ(link=[classarith])

# This is probably boring as we can't inline operators?
display(circ_c)

# Run the circuits
job_c = circ_c.to_job()

result_c = qpu.submit(job_c)

# Print the results.
for sample in result_c:
	print("State [classical arith]: {}".format(sample.state))
