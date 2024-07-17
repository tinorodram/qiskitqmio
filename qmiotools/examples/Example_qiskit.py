from qiskit.circuit import QuantumCircuit
from qiskit import transpile
from qmiotools.integrations.qiskitqmio import QmioBackend

#
# Start the Qmiobackend. Loads the last calibration from the folder indicated in QMIO_CALIBRATIONS environ
#
backend=QmioBackend()

#
# Create the circuit
#
nqubits=3
ghz = QuantumCircuit(nqubits)
ghz.h(0)
ghz.cx(0, range(1, nqubits))
ghz.measure_all()
ghz_3=transpile(ghz,backend,optimization_level=3)

#
# Execute in the QPU. This execution is synchronous, so, only returns when the job has been executed
#
job=backend.run(ghz_3, shots=1000)

#
# Return the results
#
print(job.result().get_counts(ghz_3))

