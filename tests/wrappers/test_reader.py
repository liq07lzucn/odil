import unittest

import StringIO

import odil

class TestReader(unittest.TestCase):
    def test_constructor(self):
        stream = odil.iostream(StringIO.StringIO())
        reader = odil.Reader(stream, odil.registry.ImplicitVRLittleEndian)
        self.assertEqual(
            reader.transfer_syntax, odil.registry.ImplicitVRLittleEndian)
        self.assertEqual(reader.byte_ordering, odil.ByteOrdering.LittleEndian)
        self.assertFalse(reader.explicit_vr)
        self.assertFalse(reader.keep_group_length)

    def test_constructor_no_default(self):
        stream = odil.iostream(StringIO.StringIO())
        reader = odil.Reader(
            stream, odil.registry.ExplicitVRBigEndian_Retired, True)
        self.assertEqual(
            reader.transfer_syntax, odil.registry.ExplicitVRBigEndian_Retired)
        self.assertEqual(reader.byte_ordering, odil.ByteOrdering.BigEndian)
        self.assertTrue(reader.explicit_vr)
        self.assertTrue(reader.keep_group_length)

    def test_read_data_set(self):
        string_io = StringIO.StringIO(
            "\x10\x00\x10\x00PN\x07\x00Foo^Bar"
            "\x10\x00\x20\x00CS\x03\x00FOO"
        )
        stream = odil.iostream(string_io)
        reader = odil.Reader(stream, odil.registry.ExplicitVRLittleEndian)
        data_set = reader.read_data_set()
        self.assertEqual(data_set.size(), 2)
        self.assertSequenceEqual(data_set.as_string("PatientName"), ["Foo^Bar"])
        self.assertSequenceEqual(data_set.as_string("PatientID"), ["FOO"])

    def test_read_data_set_halt_condition(self):
        string_io = StringIO.StringIO(
            "\x10\x00\x10\x00PN\x07\x00Foo^Bar"
            "\x10\x00\x20\x00CS\x03\x00FOO"
        )
        stream = odil.iostream(string_io)
        reader = odil.Reader(stream, odil.registry.ExplicitVRLittleEndian)
        data_set = reader.read_data_set(lambda x: x==odil.registry.PatientID)
        self.assertEqual(data_set.size(), 1)
        self.assertSequenceEqual(data_set.as_string("PatientName"), ["Foo^Bar"])

    def test_read_tag(self):
        string_io = StringIO.StringIO("\x10\x00\x20\x00")
        stream = odil.iostream(string_io)
        reader = odil.Reader(stream, odil.registry.ExplicitVRLittleEndian)
        self.assertEqual(reader.read_tag(), odil.registry.PatientID)

    def test_read_length(self):
        string_io = StringIO.StringIO("\x34\x12")
        stream = odil.iostream(string_io)
        reader = odil.Reader(stream, odil.registry.ExplicitVRLittleEndian)
        self.assertEqual(reader.read_length(odil.VR.CS), 0x1234)

    def test_read_element(self):
        string_io = StringIO.StringIO("PN\x07\x00Foo^Bar")
        stream = odil.iostream(string_io)
        reader = odil.Reader(stream, odil.registry.ExplicitVRLittleEndian)
        self.assertEqual(
            reader.read_element(odil.registry.PatientName),
            odil.Element(["Foo^Bar"], odil.VR.PN))

    def test_read_file(self):
        data = (
            128*"\0"+"DICM"+
            "\x02\x00\x10\x00" "UI" "\x14\x00" "1.2.840.10008.1.2.1 "
            "\x10\x00\x10\x00" "PN" "\x07\x00" "Foo^Bar"
        )
        string_io = StringIO.StringIO(data)
        stream = odil.iostream(string_io)

        header, data_set = odil.Reader.read_file(stream)

        self.assertEqual(len(header), 1)
        self.assertSequenceEqual(
            header.as_string("TransferSyntaxUID"),
            [odil.registry.ExplicitVRLittleEndian])

        self.assertEqual(len(data_set), 1)
        self.assertSequenceEqual(data_set.as_string("PatientName"), ["Foo^Bar"])

if __name__ == "__main__":
    unittest.main()