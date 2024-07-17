from qmiotools.integrations.tkbackend import Qmio

#
# Creatre the circuit
#
from pytket.circuit import Circuit
bell = Circuit(32,2)
bell.H(0)
bell.CX(0,1)
bell.Measure(0,0)
bell.Measure(1,1)

#
# Create an instance of the Backend
#
Q=Qmio()

#
# Compile the circuit with optimisation 1 (could be 0, 1 or 2)
#
ibell=Q.get_compiled_circuit(bell,1)

#
# Execute the circuit in the QPU. This operation is synchronous
#
br=Q.run_circuit(ibell,n_shots=5000)
