# This quantum routine does multiplication though multiple adds.
def looped_add(reg_size, constant, registers):
	from qat.lang.AQASM import QRoutine
	from qat.lang.AQASM.arithmetic import add
	
	routine = QRoutine()
	gate = add(reg_size, reg_size)
	for a in range(constant):
		routine.apply(gate, registers)

	return routine
