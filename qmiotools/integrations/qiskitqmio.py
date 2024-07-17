from qiskit.providers import QubitProperties, BackendV2, Provider, Options, Job
from qiskit.providers import JobStatus, JobV1  
from qiskit.providers.models.backendstatus import BackendStatus

from qiskit.circuit.gate import Instruction
from qiskit.circuit.library import ECRGate, IGate, Measure, RZXGate, RZGate, SXGate,ECRGate, XGate
from qiskit.circuit import Delay
from qiskit.transpiler import Target, InstructionProperties
from qiskit.circuit.library import UGate, CXGate, Measure
from qiskit.circuit import Parameter, QuantumCircuit, ClassicalRegister
from qiskit.pulse import Schedule
from qiskit.result.models import ExperimentResult, ExperimentResultData
from qiskit.result import Result, Counts  
from qiskit.qobj import QobjExperimentHeader
from qiskit import qasm3, transpile
from qiskit.qobj.utils import MeasLevel
from subprocess import Popen, PIPE

import os
import math
import uuid
from datetime import date,datetime,timedelta
import time
from collections import Counter, OrderedDict
from typing import Union, List, Optional, Dict,  Any, TYPE_CHECKING, Union, cast
from dataclasses import dataclass
import warnings

from ..exceptions import QPUException, QmioException
from .utils import Calibrations 
from ..version import VERSION
from ..data import QBIT_MAP, QUBIT_POSITIONS

from qmio import QmioRuntimeService


time.sleep(10)
stdout = Popen('squeue --format="%.10L"', shell=True, stdout=PIPE).stdout
output = stdout.read()

datetime_str=output.decode("utf-8").split('\n')[1].strip()

fs=datetime_str.count(':')
ophms=['%S','%M:%S','%H:%M:%S']

timeleft= time.strptime(datetime_str, ophms[fs])
SlurmJobTime=timedelta(hours=timeleft.tm_hour,minutes=timeleft.tm_min,seconds=timeleft.tm_sec).total_seconds()

#QUBIT_POSITIONS=[(1,2),(1,3),(1,4),(1,5),(1,6),
#            (2,6.5),(2,4.5),(2,2.5),
#            (3,1),(3,2),(3,3),(3,4),(3,5),
#            (4,5.5),(4,3.5),(4,1.5),
#            (5,1),(5,2),(5,3),(5,4),(5,5),(5,6),
#            (6,6.5),(6,4.5),(6,2.5),(6,1),
#            (7,1),(7,2),(7,3),(7,4),(7,5),(7,6)]

#QBIT_MAP=[2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35]
QBIT_MAP2=QBIT_MAP.copy()
QBIT_MAP=[i for i in range(32)]

import logging


class QmioJob(JobV1):
    """

    A class to return the results of a Job following the structure of :py:class:`qiskit.providers.JobV1`"""

    def __init__(
        self,
        backend: Optional[BackendV2],
        job_id: str,
        jobstatus: JobStatus = JobStatus.INITIALIZING,
        result: Result = None,
        **kwargs 
    ):
        """Initializes the synchronous job."""

        super().__init__(backend, job_id, **kwargs)
        self._jobstatus=jobstatus
        self._result=result
        self.version=VERSION
        
    def submit(self) -> None:
        """
        
        This method is not necessary for this backend, because currently the execution is synchronous


        """
        raise NotImplemented("Not necessary for this backend")

    def result(self) -> Result:   
        return self._result
        
        

    def cancel(self) -> None:
        """
        This method is not necessary for this backend, because currently the execution is synchronous
        """
        raise NotImplemented("Not necessary for this backend")

    def status(self) -> Any:
        return self._jobstatus

@dataclass
class QasmCircuit():
    """
    A dataclass for storing basic data to return data of one execution for inputs in OpenQasm"""
    circuit=None
    name=None
    metadata={}







DEFAULT_OPTIONS=Options(shots=8192,memory=False,repetition_period=None,res_format="binary_count")
FORMATS=["binary_count","raw","binary","squash_binary_result_arrays"]
DT=0.5*1e-9 #0.5ns

class QmioBackend(BackendV2):
    """
    Backend to execute Jobs in Qmio QPU.
    
    Args:
            calibration_file (Str or None):  full path to a calibration file. Default *None* and loads the last calibration file from the directory indicated by environment QMIO_CALIBRATIONS
            
            logging_level (int): flag to indicate the logging level. Better if use the logging package levels. Default logging.NOTSET
            
            logging_filename (Str):  Path to store the logging messages. Default *Nonei*, i.e., output in stdout
            
            kwargs: Other parameters to pass to Qisbit BackendV2 class

    
    It uses :py:class:`qmio.QmioRuntimeService` to submit circuits to the QPU. By default, the calibrations are read from the last JSON file in the directory set by environ variable QMIO_CALIBRATIONS, but accepts a direct filename to use instead of.
    
    The execution using the method run is synchronous.
    
    To create a new backend use::
    
        backend=QmioBackend()
    
    It will print the file where the calibration were read in. If you want to use a specific calibrations file, use::
        
        backend=QmioBackend(<file name>)

    where <file name> is the path to the calibrations file that must be used. If the file is not found, it raises a exception.

    **Example**::

        from qiskit.circuit import QuantumCircuit
        from qiskit import transpile
        from qmiotools.integrations.qiskitqmio import QmioBackend
       
        backend=QmioBackend() # loads the last calibration file from the directory $QMIO_CALIBRARTIONS
        
        # Creates a circuit qwith 2 qubits 
        c=QuantumCircuit(2)
        c.h(0)
        c.h(0)
        c.measure_all()

        #Transpile the circuit using the optimization_level equal to 2
        c=transpile(c,backend,optimization_level=2)
   
        #Execute the circuit with 1000 shots. Must be executed from a node with a QPU.
        job=backend.run(c,shots=1000)

        #Return the results
        print(job.result().get_counts())
    
   
    """
    

    def __init__(self, calibration_file: str=None, logging_level: int=logging.NOTSET, logging_filename: str=None, **kwargs):
        
        self._provider=None
        self._name="Qmio"
        self._description="CESGA Qmio"
        self._backend_version=VERSION
        self._logger = logging.getLogger("QmioBackend") 

        self._logger.setLevel(logging_level)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        
        
        
        if logging_filename!=None:
            handler = logging.FileHandler(logging_filename)
        else:
            import sys
            handler = logging.StreamHandler(sys.stdout)
        
        handler.setFormatter(formatter)
        if (self._logger.hasHandlers()):
            self._logger.handlers.clear()
        self._logger.addHandler(handler)
        
        self._logger.info("Logging started:")
        handler.flush()
            
        super().__init__(self,name=self._name, description=self._description, **kwargs)
        
        self._logger.info("Loading calibrations")
        handler.flush()
        
        calibrations=Calibrations.import_last_calibration(calibration_file)
        properties=[]
        qubits=calibrations.get_qubits()
        
        #
        # Load Qubits Properties
        #
        
        T1s=[]
        for k in qubits.keys():
            T1s.append(qubits[k]["T1"]*1e-6)      
        self._rep_per=5*max(T1s)
        
        keys=list(qubits.keys())
        num_qubits=len(keys)
        
        j=0
        for i in range(max(QBIT_MAP)+1):
            if i in QBIT_MAP:
                key=keys[j]
                properties.append(QubitProperties(t1=qubits[key]["T1"]*1e-6,t2=qubits[key]["T2e"]*1e-6,frequency=qubits[key]["Drive Frequency "]))
                j=j+1
                self._logger.debug("Qubit:%s, T1=%f, T2=%f, Drive Freq:%f"%(key,qubits[key]["T1"]*1e-6,qubits[key]["T2e"]*1e-6,qubits[key]["Drive Frequency "]))
            else:
                properties.append(None)
                
        self._logger.info("Number of loaded qubits %d"%len(properties))
        
        
        target = Target(description="qmio", num_qubits=len(properties), dt=DT, granularity=1, 
                        min_length=1, pulse_alignment=1, acquire_alignment=1, 
                        qubit_properties=properties, concurrent_measurements=None)
        
        
        theta = Parameter('theta')
        
        errors=calibrations.get_1Q_errors()
        durations=calibrations.get_1Q_durations()
       
        sx_inst=OrderedDict()
        x_inst=OrderedDict()
        for i in errors:
            sx_inst[(QBIT_MAP[i[0]],)]=InstructionProperties(duration=durations[i], error=errors[i])
            self._logger.debug("Added SX[%d]- Duration %fns - error %f"%(QBIT_MAP[i[0]],durations[i]*1e9,errors[i]))
        for i in errors:
            x_inst[(QBIT_MAP[i[0]],)]=InstructionProperties(duration=durations[i]*2, error=errors[i])
            self._logger.debug("Added X[%d]- Duration %fns - error %f"%(QBIT_MAP[i[0]],durations[i]*1e9*2,errors[i]))
        
        target.add_instruction(SXGate(), sx_inst)
        target.add_instruction(XGate(), x_inst)
        
        rz_inst=OrderedDict()
        for i in durations:
            rz_inst[(QBIT_MAP[i[0]],)]=InstructionProperties(duration=0.0)
            self._logger.debug("Added rz[%d]- Duration %fns - error %f"%(QBIT_MAP[i[0]],0.0,0.0))
                
        target.add_instruction(RZGate(theta), rz_inst)
        
        #q2_inst=calibrations.get_2Q_errors()
        #target.add_instruction(ECRGate(), q2_inst)   
        errors=calibrations.get_2Q_errors()
        durations=calibrations.get_2Q_durations()
        
        #self._logger.debug(durations)
        
        ecr_inst=OrderedDict()
        for i in errors:
            self._logger.debug("Added ecr_inst[(%d,%d) - duration %fns - error %f]"%(QBIT_MAP[i[0]],QBIT_MAP[i[1]],durations[i]*1e9,errors[i]))
            ecr_inst[(QBIT_MAP[i[0]],QBIT_MAP[i[1]])]=InstructionProperties(duration=durations[i], error=errors[i])
            
        
        target.add_instruction(ECRGate(), ecr_inst)
        #target.add_instruction(RZXGate(math.pi/4), ecr_inst, name="rzx(pi/4)")
        
        measures=OrderedDict()
        
        #for i in qubits:
        j=0
        for i in range(max(QBIT_MAP)+1):
            if i in QBIT_MAP:
                k=keys[j]
                j=j+1
                measures[(i,)]=InstructionProperties(error=1.0-qubits[k]["Fidelity readout"],duration=qubits[k]["Measuring time"]*1e-6)
                self._logger.debug("measures[%d] - error %f - duration %fs"%(i,1.0-qubits[k]["Fidelity readout"],qubits[k]["Measuring time"]*1e-6))
            else:
                measures[(i,)]=InstructionProperties(error=1.0)
        target.add_instruction(Measure(),measures)
        
        delays=OrderedDict()
        for i in qubits:
            delays[(QBIT_MAP[int(i[2:-1])],)]=None
        
        target.add_instruction(Delay(Parameter("t")),measures)
                               
        self._target = target
        
        self._options = DEFAULT_OPTIONS
        self._logger.info("Default options %s"%DEFAULT_OPTIONS)
        
        self._version = VERSION
        self._logger.info("VERSION %s"%VERSION)
        
        self._max_circuits=1000
        self._logger.info("MAX CIRCUITS %d"%self._max_circuits)
        
        self._max_shots=8192
        self._logger.info("MAX SHOTS PER STEP %d"%self._max_shots)
        
        self.max_shots=self._max_circuits*self._max_shots
        self._logger.info("MAX SHOTS PER JOB %d"%self.max_shots)
        

    @property
    def target(self) -> Target:
        return self._target
    
    @classmethod
    def _default_options(cls):
        return DEFAULT_OPTIONS
    
    @property
    def max_circuits(self):
        return self._max_circuits
    
    
    def run(self, run_input: Union[Union[QuantumCircuit,Schedule, str],List[Union[QuantumCircuit,Schedule,str]]], **options) -> QmioJob:
        """Run on QMIO QPU. This method is Synchronous, so it will wait for the results from the QPU

        Args:
            run_input (QuantumCircuit or Schedule or Str - a QASM string - or list): An
                individual or a list of :class:`.QuantumCircuit`,
                or :class:`~qiskit.pulse.Schedule` or a string with a QASM 3.0 objects to
                run on the backend.
            options: Any kwarg options to pass to the backend for running the
                config. If a key is also present in the options
                attribute/object then the expectation is that the value
                specified will be used instead of what's set in the options
                object.

        Returns:
            :class:`.qiskitqmio.QmioJob`: The job object for the run
        
        Raises:
            QPUException: if there is one error in the QPU
            QmioException: if there are errors in the input parameters.
        """

        if isinstance(options,Options):
            shots=options.get("shots",default=self._options.get("shots"))
            memory=options.get("memory",default=self._options.get("memory"))
            repetition_period=options.get("repetition_period",default=self._options.get("repetition_period"))
            res_format=options.get("res_format",default=self._options.get("res_format"))
        else:
            if "shots" in options:
                shots=options["shots"]
            else:
                shots=self._options.get("shots")
            
            if "memory" in options:
                memory=options["memory"]
            else:
                memory=self._options.get("memory")

            if "repetition_period" in options:
                repetition_period=options["repetition_period"]
            else:
                repetition_period=self._options.get("repetition_period")
            
            if "res_format" in options:
                res_format=options["res_format"]
            else:
                res_format=self._options.get("res_format")
        
        self._logger.info("Requested parameters: Shots %d - memory %s - Repetition_period %s - Res_format %s"%(shots, memory, str(repetition_period), res_format))
               
        if res_format not in FORMATS:
            raise QmioException("Format %s not in available formats:%s"%(res_format,FORMATS))

        if isinstance(run_input,str) and not "OPENQASM" in run_input:
            raise QmioException("Input seems not to be a valid OPENQASM 3.0 file...")
        
        if isinstance(run_input,QuantumCircuit) or isinstance(run_input,Schedule) or isinstance(run_input,str):
            circuits=[run_input]
        else:
            circuits=run_input

        if shots*len(circuits) > self.max_shots:
            raise QmioException("Total number of shots %d larger than capacity %d"%(shots,self.max_shots))
        
        
        est_time=shots*len(circuits)*self._rep_per
        
        if est_time>SlurmJobTime:
            raise QmioException('The expected execution time '+str(est_time)+' s exceeds the remaining slurm-job time '+str(SlurmJobTime)+' s')
        
	
        self._logger.debug("Starting QmioRuntimeService")
        service = QmioRuntimeService()
                          
        
        job_id=uuid.uuid4()
                          
        self._logger.debug("Job id %s"%job_id)
                          
        ExpResult=[]
        with service.backend(name="qpu") as backend:
            for circuit in circuits:
                
                if isinstance(circuit,QuantumCircuit):
                    if len(circuit.cregs)>1:
                        c=FlattenCircuit(circuit)
                    else:
                        c=circuit
                else:
                    c=circuit
                
                #print("Metadata",c.metadata)
                if isinstance(c,QuantumCircuit) or isinstance(c,Schedule):
                    qasm=qasm3.dumps(c, basis_gates=self.operation_names).replace("\n","")
                    if "qubit[" in qasm:
                        c=transpile(c,self)
                        qasm=qasm3.dumps(c, basis_gates=self.operation_names).replace("\n","")
                    #print("Antes:\n",qasm)
                    for i in range(self.num_qubits-1,-1,-1):
                        #print("$%d;"%i,"$%d;"%QBIT_MAP2[i])
                        qasm=qasm.replace("$%d;"%i,"$%d;"%QBIT_MAP2[i])
                        qasm=qasm.replace("$%d,"%i,"$%d,"%QBIT_MAP2[i])
                        qasm=qasm.replace("$%d "%i,"$%d "%QBIT_MAP2[i])
                    #print(qasm)
                else:
                    qasm=c
                
                
                remain_shots=shots
                ExpDict={}
                self._logger.info("QASM %s"%qasm)
                warning_raised = False
                while (remain_shots > 0):
                    self._logger.info("Requesting SHOTS=%d"%min(self._max_shots,remain_shots))
                    results = backend.run(circuit=qasm, shots=min(self._max_shots,remain_shots),repetition_period=repetition_period,res_format=res_format)
                        
                    self._logger.debug("Results:%s"%results)
                    if "Exception" in results:
                        raise QPUException(results["Exception"])
                    try:
                        r=results["results"][list(results["results"].keys())[0]]
                    except:
                        raise QPUException("QPU does not return results")
                    for k in r:
                        if not memory:
                            key=hex(int(k[::-1],base=2))
                            ExpDict[key]=ExpDict[key]+r[k] if key in ExpDict else r[k]
                        else:
                            raise QmioException("Binary for the next version")
                    remain_shots=remain_shots-self._max_shots
                
                if isinstance(c,QuantumCircuit):
                    metadata=c.metadata
                else:
                    metadata={}
                
                if "execution_metrics" in results:
                    metadata["execution_metrics"]=results["execution_metrics"]
                    
                metadata["repetition_period"]=repetition_period
                metadata["res_format"]=res_format
                
                creg_sizes=[]
                qreg_sizes=[]
                memory_slots=0
                n_qubits=0
                if isinstance(circuit,str):
                    c_copy=circuit
                    circuit=QasmCircuit()
                    circuit.circuit=c_copy
                    circuit.name="QASM"
                    c=circuit
                    print(c)
                else:
                    for c1 in circuit.cregs:
                        creg_sizes.append([c1.name,c1.size])
                        memory_slots+=c1.size

                    for c1 in circuit.qregs:
                        qreg_sizes.append([c1.name,c1.size])
                    n_qubits=len(circuit.qubits)
                header ={'name': c.name, 'creg_sizes':creg_sizes, 'memory_slots':memory_slots, 'n_qubits':n_qubits,
                               'qreg_sizes':qreg_sizes,'metadata':circuit.metadata}
                #header.update(c.metadata)

                self._logger.debug("Retorno: %s"%ExpDict)
                

                dd={
                    'shots': shots,
                    'success': True,
                    'data': {

                        'counts': ExpDict,
                        'metadata': metadata,
                    },
                    'header': header,

                    }
                
                ExpResult.append(dd)

        result_dict = {
            'backend_name': self._name,
            'backend_version': self._version,
            'qobj_id': None,
            'job_id': job_id,
            'success': True,
            'results': ExpResult,
            'date': datetime.now().isoformat(),

        }
        self._logger.debug("Final Results returned: %s"%result_dict)
                          
        results=Result.from_dict(result_dict)

        job=QmioJob(backend=self,job_id=uuid.uuid4(), jobstatus=JobStatus.DONE, result=results)
        
        return job
    
    
    
def FlattenCircuit(circ: QuantumCircuit) -> QuantumCircuit:
    """
    Method to convert a Qiskit circuit with several ClassicalRegisters in a single ClassicalRegister
    
    Args:
        circ: A QuantumCircuit
        
    Returns: 
        A new QuantumCircuit with a single ClassicalRegister
    """
    d=QuantumCircuit()
    [d.add_register(i) for i in circ.qregs]
    j=0

    registers={}
    for i in circ.cregs:
        registers[i.name]=j
        j=j+i.size
        #print(i)
        #print(j)
    #print(registers)
    ag=ClassicalRegister(j,"C")
    d.add_register(ag)
    #print(j) # Probar a hacerlo en vectorial
    for i in circ.data:
        if i.operation.name == "measure":
            j=i.clbits[0]

            d.measure(i.qubits[0],ag[registers[j._register.name]+j._index])
            #print(i.clbits[0])

        else:
            d.data.append(i)
    d.name=circ.name
    return d



from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel

def FakeQmio(calibration_file: str=None, thermal_relaxation: bool = True, temperature: float = 0 , gate_error: bool=False, readout_error: bool=False, **kwargs) -> AerSimulator:
    """
    Create a Fake backend for Qmio that uses the last calibrations and AerSimulator. 

    Args:
        calibration_file (str): A path to a valid calibration file. If the path is **None** (default), the last calibration is loaded.
        thermal_relaxation (bool): If True, the noise model will include the thermal relaxation using the data from the calibration. Default: *True*
        temperature (float): the temperature in mK. If it is different of 0 (defaul)
        gate_error (bool): Flag to include (True) or not (False. Default option) the gate errors in the model.
        readout_error (bool): Flag to include (True) or not (False. Default) the readout error from the calibrations file.
        **kwargs: other parameters to pass directly to AerSimulator

    Returns:
        (AerSimulator): A valid backend including the defined noise model.

    Raises:
        QmioException: if the configuration file could not be found. 

    """
    qmio=QmioBackend(calibration_file)
    noise_model = NoiseModel.from_backend(
        qmio, thermal_relaxation=thermal_relaxation,
        temperature=temperature,
        gate_error=gate_error,
        readout_error=readout_error)

    cls= AerSimulator.from_backend(qmio, noise_model=noise_model, **kwargs)
    cls.name = "FakeQmio"
    cls.description ="Fake backend for Qmio that uses the last calibrations and AerSimulator"
    return cls
        
    
