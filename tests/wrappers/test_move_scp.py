import glob
import multiprocessing
import os
import subprocess
import sys
import time
import unittest

import odil

class Generator(odil.MoveSCP.DataSetGenerator):
    def __init__(self, association):
        odil.MoveSCP.DataSetGenerator.__init__(self)
        self._association = association
        self._responses = []
        self._response_index = None
        
    def initialize(self, message):
        data_set_1 = odil.DataSet()
        data_set_1.add("SOPClassUID", [odil.registry.RawDataStorage])
        data_set_1.add(
            "SOPInstanceUID", 
            ["1.2.826.0.1.3680043.9.5560.3127449359877365688774406533090568532"])
        data_set_1.add("PatientName", ["Hello^World"])
        data_set_1.add("PatientID", ["1234"])
        self._responses.append(data_set_1)
        
        data_set_2 = odil.DataSet()
        data_set_2.add("SOPClassUID", [odil.registry.RawDataStorage])
        data_set_2.add(
            "SOPInstanceUID", 
            ["1.2.826.0.1.3680043.9.5560.3221615743193123463515381981101110692"])
        data_set_2.add("PatientName", ["Doe^John"])
        data_set_2.add("PatientID", ["5678"])
        self._responses.append(data_set_2)
        
        self._response_index = 0
    
    def done(self):
        return (self._response_index == len(self._responses))
    
    def next(self):
        self._response_index += 1
    
    def get(self):
        return self._responses[self._response_index]
    
    def count(self):
        return 2
    
    def get_association(self, request):
        move_association = odil.Association()
        move_association.set_peer_host(self._association.get_peer_host())
        move_association.set_peer_port(11114)
        
        presentation_contexts = [
            odil.AssociationParameters.PresentationContext(
                1, odil.registry.RawDataStorage,
                [odil.registry.ImplicitVRLittleEndian], 
                odil.AssociationParameters.PresentationContext.Role.SCU)]
        
        move_association.update_parameters()\
            .set_calling_ae_title(
                self._association.get_negotiated_parameters().get_called_ae_title())\
            .set_called_ae_title(request.get_move_destination())\
            .set_presentation_contexts(presentation_contexts)

        return move_association

class TestMoveSCP(unittest.TestCase):
    def test_move_scp_release(self):
        process = multiprocessing.Process(target=self.run_server)
        process.start()
        time.sleep(0.5)
        data_sets = self.run_client()
        process.join(2)
        server_code = process.exitcode
        
        self.assertEqual(server_code, 0)
        
        self.assertEqual(len(data_sets), 2)
        
        self.assertEqual(len(data_sets[0]), 4)
        
        self.assertSequenceEqual(
            data_sets[0].as_string("SOPClassUID"), 
            [odil.registry.RawDataStorage])
        self.assertSequenceEqual(
            data_sets[0].as_string("SOPInstanceUID"), 
            [b"1.2.826.0.1.3680043.9.5560.3127449359877365688774406533090568532"])
        self.assertSequenceEqual(
            data_sets[0].as_string("PatientName"), [b"Hello^World"])
        self.assertSequenceEqual(data_sets[0].as_string("PatientID"), [b"1234"])
        
        self.assertSequenceEqual(
            data_sets[1].as_string("SOPClassUID"), 
            [odil.registry.RawDataStorage])
        self.assertSequenceEqual(
            data_sets[1].as_string("SOPInstanceUID"), 
            [b"1.2.826.0.1.3680043.9.5560.3221615743193123463515381981101110692"])
        self.assertSequenceEqual(
            data_sets[1].as_string("PatientName"), [b"Doe^John"])
        self.assertSequenceEqual(data_sets[1].as_string("PatientID"), [b"5678"])
    
    def run_client(self):
        command = [
            "movescu", 
            "-ll", "error",
            "-P", "-k", "QueryRetrieveLevel=PATIENT",
            "-k", "PatientID=*", "-k", "PatientName",
            "+P", "11114",
            "localhost", "11113"]
        
        retcode = subprocess.call(command)
        if retcode != 0:
            return []
        
        files = sorted(glob.glob("RAW*"))
        data_sets = []
        for file_ in files:
            with odil.open(file_, "rb") as fd:
                data_sets.append(odil.Reader.read_file(fd)[1])
        for file_ in files:
            os.remove(file_)
        
        return data_sets

    def run_server(self):
        association = odil.Association()
        association.set_tcp_timeout(1)
        association.receive_association("v4", 11113)

        move_scp = odil.MoveSCP(association)
        generator = Generator(association)
        move_scp.set_generator(generator)

        message = association.receive_message()
        move_scp(message)
        
        termination_ok = False

        try:
            association.receive_message()
        except odil.AssociationReleased:
            termination_ok = True
        except odil.AssociationAborted:
            pass
        
        if termination_ok:
            sys.exit(0)
        else:
            sys.exit(1)

if __name__ == "__main__":
    unittest.main()
