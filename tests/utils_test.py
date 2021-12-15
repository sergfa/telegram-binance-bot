import unittest
from utils import *
class TestUtils(unittest.TestCase):
    
    def test_boolAsYorNo(self):
        yesStr = boolAsYorNo(True)
        self.assertEqual(yesStr, 'Y')
        noStr = boolAsYorNo(False)
        self.assertEqual(noStr, 'N')

    def test_symbols_alerts_to_table(self):
        data = [('A',True, False)]
        table = str(symbols_alerts_to_table(data))
        self.assertTrue("A" in table)
        self.assertTrue("Y" in table)
        self.assertTrue("N" in table)

    def test_symbols_to_table(self):
        data = ["BTC", "ETH"]
        table = symbols_to_table(data)
        self.assertTrue("BTC" in table)
        self.assertTrue("ETH" in table)    

    def test_split_list_to_chunks(self):
        data = [x for x in range(0, 100)]
        data_chunks1 = split_list_to_chunks(data, 20)
        self.assertEqual(len(data_chunks1), 5)

        data_chunks2 = split_list_to_chunks(data, 200)
        self.assertEqual(len(data_chunks2), 1)

        data_chunks3 = split_list_to_chunks(data, 30)
        self.assertEqual(len(data_chunks3), 4)

    def test_list_to_tables(self):
        symbols_data = [chr(i + 65) for i in range(0, 10)] # A,B,C,D,E,F,G,H,I,G
        tables1 = list_to_tables(symbols_data,5, symbols_to_table)
        self.assertEqual(len(tables1), 2)
        
        alerts_data = [('A', True, False),
                       ('B', True, False),
                       ('C', True, False),
                       ('D', True, False),
                       ('E', True, False) ]

        tables2 = list_to_tables(alerts_data,2, symbols_alerts_to_table)
        self.assertEqual(len(tables2), 3)
       


if __name__ == '__main__':
    unittest.main()       