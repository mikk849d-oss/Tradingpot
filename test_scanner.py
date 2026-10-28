import unittest
from main import synthetic_prices,rank_universe,render_report,percentile_ranks

class ScreenerTest(unittest.TestCase):
    def test_full_ranking(self):
        universe=synthetic_prices()
        ranks=rank_universe(universe)
        self.assertEqual(len(ranks),len(universe))
        self.assertEqual(len({x['ticker'] for x in ranks}),len(ranks))
        self.assertEqual(ranks,sorted(ranks,key=lambda x:x['score'],reverse=True))
        self.assertTrue(all(0<=x['score']<=100 for x in ranks))
    def test_does_not_trade(self):
        ranks=rank_universe(synthetic_prices())
        report=render_report(ranks,[],True)
        self.assertIn('DEMO: FIKTIVE DATA',report)
        self.assertIn('ingen handler udføres',report)
    def test_rank(self):
        self.assertEqual(percentile_ranks({'a':1,'b':2,'c':3}),{'a':0,'b':50,'c':100})
    def test_invalid_length(self):
        universe=synthetic_prices()
        universe['MSFT']['prices']=universe['MSFT']['prices'][:100]
        with self.assertRaises(ValueError):rank_universe(universe)

if __name__=='__main__':unittest.main()
