from __future__ import annotations
import os
import glob
from collections import OrderedDict
import json

from typing import Union, Optional, List


class Calibrations(OrderedDict):

    def __init__(self,calibration: Optional[Union[OrderedDict,str]]=None):
        if isinstance(calibration,str):
            cal=OrderedDict(calibration)
        else:
            cal=calibration
        if cal is None:
            super().__init__()
        else:
            super().__init__(cal)
    def get_mapping(self) -> List:
        Q2Gates=self["Q2Gates"]
        mapping=[]
        for k in Q2Gates:
            mapping.append((Q2Gates[k]["Control"],Q2Gates[k]["Target"]))
        return mapping

    def get_gateset(self)-> List:
        Q1Gates=self["Q1Gates"]
        gateset=[]
        for i in Q1Gates[list(Q1Gates.keys())[0]].keys():
            gateset.append(i)
        return gateset

    def from_json_file(self, imput: str):
        with open(imput,"r") as f:
            jj=OrderedDict(json.load(f))
            print(jj)
            for k in jj:
                self[k]=jj[k]

    def from_json_str(self, imput: str):
        jj=OrderedDict(imput)
        #print(jj)

        for k in jj:
            print(k)
            self[k]=jj[k]
    
    def from_last_calibrations(self, path: str=None):
        if path is None:
            path=os.getenv("QMIO_CALIBRATIONS",".")

        dic=import_last_calibration(path)
        print(dic)
        self.__init__(dic)
    
    def get_2Q_errors(self) -> OrderedDict:
        errors=OrderedDict()
        errors_1Q=self.get_1Q_errors()
        for k in self["Q2Gates"]:
            control=int(self["Q2Gates"][k]["Control"])
            target = int(self["Q2Gates"][k]["Target"])
            errors[control,target]= \
                1.0-((self["Q2Gates"][k]["Fidelity"]**2/10000)*(1-errors_1Q[(control,)]**2/10000))
            #print(k,errors[control,target], errors_1Q[(control,)])
        return errors
            
    def get_1Q_errors(self,gate: str = "SX") -> OrderedDict:
        errors=OrderedDict()
        for k in self["Q1Gates"]:
            errors[(int(k[2:-1]),)]= 1.0 - self["Q1Gates"][k][gate]["Fidelity"]/100
        return errors
    
    def get_1Q_durations(self,gate: str = "SX") -> OrderedDict:
        durations=OrderedDict()
        for k in self["Q1Gates"]:
            durations[(int(k[2:-1]),)]= self["Q1Gates"][k][gate]["duration (ns)"]*1e-9    
        return durations
    
    def get_2Q_durations(self,gate: str = "ECR") -> OrderedDict:
        durations=OrderedDict()
        durations_1Q=self.get_1Q_durations("SX")
        
        #print(self["Q2Gates"])
        if (gate != "ECR"):
            raise RuntimeError("Gate %s not supported in this device"%gate)
        for k in self["Q2Gates"]:
            control=int(self["Q2Gates"][k]["Control"])
            target = int(self["Q2Gates"][k]["Target"])
            durations[control,target]= \
                2*(self["Q2Gates"][k]["Duration (ns)"]*1e-9+durations_1Q[(control,)])
        return durations
    
    def get_qubits(self) -> OrderedDict:
        return self["Qubits"]

    
    @classmethod
    def import_last_calibration(cls, jsonpath: str = None) -> Calibrations:
        """
        A static method to create an instance of the class using a specific file for the calibrations.

        parameters:
                    jsonpath:
        returns:
                An instance of the class


        """
        if jsonpath is None:
            jsonpath=os.getenv("QMIO_CALIBRATIONS",".")
            files=jsonpath+"/????_??_??__??_??_??.json"
            try:
                files = glob.glob(files)
            except:
                raise RuntimeError("Error reading folder ".format(jsonpath))
            if len(files)!=0:
                imput=max(files, key=os.path.getctime)
            else:
                raise RuntimeError("No calibration files on %s"%jsonpath)
        else:
            imput=jsonpath
        print("Importing calibrations from ",imput)
        try:
            with open(imput,"r") as f:
                calibrations=Calibrations(OrderedDict(json.load(f)))
        except:
            raise RuntimeError("Error reading file ".format(imput))
        return calibrations


