"""Author-constructed software conformance tests, not scientific validation."""
import unittest,copy,json
import numpy as np
from numpy.testing import assert_allclose
from scipy.optimize import check_grad
from sklearn.metrics import average_precision_score
from fuzzy_core import *

class CoreTests(unittest.TestCase):
    def setUp(self):self.spec=MembershipSpec([-8,-5,-2],.3,'unit_test')
    def test_01_rule_count(self):self.assertEqual(len(RULES),12);self.assertEqual(len(set(RULES)),12)
    def test_02_hats_sum_one(self):
        h=hats(np.linspace(-20,20,2001),[-8,-5,-2]);assert_allclose(h.sum(1),1,atol=1e-14);self.assertTrue((h>=0).all())
    def test_03_knots_one_hot(self):assert_allclose(hats(np.array([-8,-5,-2]),[-8,-5,-2]),np.eye(3))
    def test_04_shoulders(self):assert_allclose(hats(np.array([-100,100]),[-8,-5,-2]),[[1,0,0],[0,0,1]])
    def test_05_invalid_knots(self):
        with self.assertRaises(GateError):hats(np.array([1]),[0,0,1])
    def test_06_current_missing_rejected(self):
        with self.assertRaises(GateError):firing([np.nan],[0],[1],self.spec)
    def test_07_unknown_not_stable(self):
        a=firing([-5,-5],[0,0],[0,1],self.spec);self.assertEqual(a[0,4],1);self.assertEqual(a[1,10],1)
    def test_08_missing_ignores_delta(self):
        assert_allclose(firing([-5],[np.nan],[1],self.spec),firing([-5],[1e10],[1],self.spec))
    def test_09_valid_nan_delta_rejected(self):
        with self.assertRaises(GateError):firing([-5],[np.nan],[0],self.spec)
    def test_10_invalid_flag(self):
        with self.assertRaises(GateError):firing([-5],[0],[2],self.spec)
    def test_11_full_grid_rule_coverage(self):
        a=firing(np.tile(np.linspace(-12,0,25),2),np.linspace(-2,2,50),np.r_[np.zeros(25),np.ones(25)],self.spec);assert_allclose(a.sum(1),1,atol=1e-14)
    def test_12_bounds_convex_combination(self):
        m={'membership':self.spec.__dict__,'consequents':np.linspace(.01,.9,12).tolist()};p=score_sugeno(m,[-100,-5,100],[-2,0,2],[0,1,0]);self.assertTrue(((p>=.01)&(p<=.9)).all())
    def test_13_quantile_weighted_inversecdf(self):self.assertEqual(weighted_quantile([1,2,3],[1,8,1],.5),2)
    def test_14_negative_weight_rejected(self):
        with self.assertRaises(GateError):weighted_quantile([1,2],[-1,1],.5)
    def test_15_loss_gradient(self):
        rng=np.random.default_rng(1);a=rng.uniform(size=(100,12));a/=a.sum(1)[:,None];y=rng.integers(0,2,100);w=np.ones(100)/100;b=np.linspace(.2,.7,12)
        err=check_grad(lambda z:binary_loss_gradient(z,a,y,w)[0],lambda z:binary_loss_gradient(z,a,y,w)[1],b)
        self.assertLess(err,1e-6)
    def test_16_convex_loss(self):
        rng=np.random.default_rng(2);a=rng.uniform(size=(100,12));a/=a.sum(1)[:,None];y=rng.integers(0,2,100);w=np.ones(100)/100;b1=rng.uniform(.01,.99,12);b2=rng.uniform(.01,.99,12)
        f=lambda b:binary_loss_gradient(b,a,y,w)[0]
        self.assertLessEqual(f((b1+b2)/2),(f(b1)+f(b2))/2+1e-14)
    def test_17_training_knots_and_no_prediction_refit(self):
        x=np.linspace(-10,1,101);d=np.linspace(-1,1,101);u=np.zeros(101);spec=estimate_memberships(x,d,u,np.ones(101));old=json.dumps(spec.__dict__,sort_keys=True)
        firing([-100,100],[-100,100],[0,1],spec);self.assertEqual(old,json.dumps(spec.__dict__,sort_keys=True))
    def test_18_no_trend_data_hold(self):
        with self.assertRaises(GateError):estimate_memberships(np.linspace(-10,1,10),np.zeros(10),np.zeros(10),np.ones(10))
    def test_19_ap_complete_ties(self):
        y=np.array([1,0,1,0,0]);s=np.array([.9,.9,.2,.2,.1]);self.assertAlmostEqual(average_precision(y,s),average_precision_score(y,s),14)
        self.assertEqual(average_precision(y,s),average_precision(y[::-1],s[::-1]))
    def test_20_ap_zero_events(self):self.assertTrue(np.isnan(average_precision([0,0],[1,2])))
    def test_21_topk_tie_bounds(self):
        r=topk_ties([0,1,1,0],[1,.5,.5,.5],2);self.assertEqual((r['tp_min'],r['tp_max']),(0,1));self.assertEqual(r['event_sure_mask'].sum(),0)
    def test_22_topk_full_group(self):
        r=topk_ties([0,1,1,0],[1,.5,.5,.1],3);self.assertEqual((r['tp_min'],r['tp_max']),(2,2));self.assertEqual(r['event_sure_mask'].sum(),2)
    def test_23_bad_k_rejected(self):
        with self.assertRaises(GateError):topk_ties([0,1],[0,1],0)
    def test_24_fit_synthetic_conformance(self):
        rng=np.random.default_rng(23);x=rng.uniform(-10,0,600);d=rng.uniform(-1,1,600);u=rng.random(600)<.15;y=rng.integers(0,2,600)
        m=fit_sugeno(x,d,u,y,np.ones(600));p=score_sugeno(m,x,d,u);self.assertTrue(np.isfinite(p).all());self.assertTrue(m['audit']['solver_success'])
    def test_25_invalid_consequents(self):
        with self.assertRaises(GateError):score_sugeno({'membership':self.spec.__dict__,'consequents':[1]*12},[-5],[0],[0])

if __name__=='__main__':unittest.main(verbosity=2)
