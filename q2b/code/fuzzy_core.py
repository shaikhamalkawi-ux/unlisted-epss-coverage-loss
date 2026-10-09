"""Frozen E01, twelve-rule zero-order Sugeno comparator.
No exploitation-probability, equivalence, or empirical interpretability claim.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any
import warnings
import numpy as np
from scipy.optimize import minimize
from scipy.special import expit
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.exceptions import ConvergenceWarning

EPS = 1e-8
LEVELS = ('low', 'middle', 'high')
TRENDS = ('falling', 'stable', 'rising')
RULES = [f'{l}__{t}__history_valid' for l in LEVELS for t in TRENDS] + [f'{l}__history_unavailable' for l in LEVELS]

class GateError(RuntimeError):
    """An admission/convergence failure; do not report partial performance."""


def weighted_quantile(x: np.ndarray, w: np.ndarray, q: float) -> float:
    x, w = np.asarray(x, float), np.asarray(w, float)
    if x.ndim != 1 or w.shape != x.shape or len(x)==0 or not 0<=q<=1:
        raise GateError('Invalid quantile inputs')
    if not np.isfinite(x).all() or not np.isfinite(w).all() or (w<=0).any():
        raise GateError('Nonfinite/nonpositive quantile inputs')
    order=np.argsort(x, kind='stable'); xs=x[order]; cs=np.cumsum(w[order])
    return float(xs[min(np.searchsorted(cs, q*cs[-1], side='left'), len(xs)-1)])


def hats(x: np.ndarray, knots: np.ndarray) -> np.ndarray:
    x=np.asarray(x,float); knots=np.asarray(knots,float)
    if x.ndim!=1 or knots.shape!=(3,) or not np.isfinite(x).all() or not np.isfinite(knots).all() or not np.all(np.diff(knots)>0):
        raise GateError('Invalid three-knot membership inputs')
    a,b,c=knots
    low=np.clip((b-x)/(b-a),0,1)
    high=np.clip((x-b)/(c-b),0,1)
    middle=np.minimum(np.clip((x-a)/(b-a),0,1),np.clip((c-x)/(c-b),0,1))
    ans=np.column_stack((low,middle,high))
    if not np.allclose(ans.sum(1),1,atol=1e-14,rtol=0):
        raise GateError('Membership partition is incomplete')
    return ans


def validate_inputs(x: np.ndarray, delta: np.ndarray, unavailable: np.ndarray):
    x,delta,u=np.asarray(x,float),np.asarray(delta,float),np.asarray(unavailable)
    if x.ndim!=1 or delta.shape!=x.shape or u.shape!=x.shape or len(x)==0:
        raise GateError('Unequal/empty input arrays')
    if not np.isfinite(x).all() or not np.isin(u,[0,1]).all():
        raise GateError('Current-score input or history state is invalid')
    u=u.astype(bool)
    if not np.isfinite(delta[~u]).all(): raise GateError('Known history has nonfinite trend')
    return x, np.where(u,0.0,delta),u


@dataclass
class MembershipSpec:
    level_knots: list[float]
    trend_scale: float
    trend_scale_rule: str


def estimate_memberships(x,delta,unavailable,weights) -> MembershipSpec:
    x,d,u=validate_inputs(x,delta,unavailable); w=np.asarray(weights,float)
    if w.shape!=x.shape or (w<=0).any() or not np.isfinite(w).all():raise GateError('Invalid training weights')
    knots=[weighted_quantile(x,w,q) for q in (0.1,0.5,0.9)]
    if not np.all(np.diff(knots)>0):raise GateError('HOLD: duplicate level knots; no test-based fallback allowed')
    if u.all():raise GateError('HOLD: no valid training trends')
    a=weighted_quantile(np.abs(d[~u]),w[~u],.9); method='weighted_absolute_trend_q90'
    if a<=0:
        a=float(np.max(np.abs(d[~u]))); method='max_positive_absolute_training_trend_fallback'
    if not a>0:raise GateError('HOLD: no nonzero known training trend')
    return MembershipSpec(knots,a,method)


def firing(x,delta,unavailable,spec: MembershipSpec) -> np.ndarray:
    x,d,u=validate_inputs(x,delta,unavailable)
    lx=hats(x,np.array(spec.level_knots)); td=hats(d,np.array([-spec.trend_scale,0,spec.trend_scale]))
    a=np.zeros((len(x),12),float)
    a[:,:9]=(lx[:,:,None]*td[:,None,:]).reshape(-1,9)*(~u)[:,None]
    a[:,9:]=lx*u[:,None]
    den=a.sum(1)
    if (den<=0).any() or not np.isfinite(a).all() or (a<0).any():raise GateError('Invalid/no active rule')
    a/=den[:,None]
    return a


def binary_loss_gradient(b, a, y, wn):
    p=a@b
    if (p<=0).any() or (p>=1).any():raise GateError('Out-of-domain Sugeno score')
    loss=-np.dot(wn,y*np.log(p)+(1-y)*np.log1p(-p))
    grad=a.T@(wn*(p-y)/(p*(1-p)))
    return float(loss),grad


def fit_sugeno(x,delta,unavailable,y,weights) -> dict[str,Any]:
    y=np.asarray(y,float); weights=np.asarray(weights,float)
    if not np.isin(y,[0,1]).all() or y.shape!=weights.shape:raise GateError('Invalid observed endpoint/weights')
    spec=estimate_memberships(x,delta,unavailable,weights)
    a=firing(x,delta,unavailable,spec)
    if len(a)!=len(y):raise GateError('Training labels and feature rows differ')
    wn=weights/weights.sum(); prevalence=float(np.dot(wn,y))
    if not EPS<prevalence<1-EPS:raise GateError('No admissible two-class training prevalence')
    scale=prevalence; lo=EPS/scale; hi=(1-EPS)/scale
    def fun(u):
        loss,g=binary_loss_gradient(u*scale,a,y,wn)
        return loss/scale,g  # d(loss/scale)/d(u) == d(loss)/d(b)
    opt=minimize(fun,np.ones(12),jac=True,method='L-BFGS-B',bounds=[(lo,hi)]*12,
                 options={'maxiter':5000,'maxls':50,'ftol':1e-12,'gtol':1e-8})
    u=opt.x; _,g=fun(u); pg=g.copy()
    pg[(u<=lo+1e-12)&(g>0)]=0; pg[(u>=hi-1e-12)&(g<0)]=0
    pgmax=float(np.max(np.abs(pg)))
    b=u*scale
    audit={'solver_success':bool(opt.success),'message':str(opt.message),'iterations':int(opt.nit),
           'projected_gradient_max':pgmax,'training_weighted_log_loss':float(opt.fun*scale),
           'training_prevalence':prevalence,'training_rows':len(y),'training_events':int(y.sum()),
           'effective_rule_weight':(a.T@weights).tolist(),'effective_positive_rule_weight':(a.T@(weights*y)).tolist(),
           'interpretation':'Training/conformance only; not held-out empirical performance.'}
    if not opt.success or pgmax>1e-5 or (b<EPS-1e-15).any() or (b>1-EPS+1e-15).any():
        raise GateError(f'Sugeno convergence HOLD: {audit}')
    return {'membership':asdict(spec),'consequents':b.tolist(),'rules':RULES,'audit':audit}


def score_sugeno(model,x,delta,unavailable):
    spec=MembershipSpec(**model['membership']); a=firing(x,delta,unavailable,spec)
    b=np.asarray(model['consequents'],float)
    if b.shape!=(12,) or not np.isfinite(b).all() or (b<=0).any() or (b>=1).any():raise GateError('Invalid consequents')
    p=a@b
    if not np.isfinite(p).all() or (p<=0).any() or (p>=1).any():raise GateError('Invalid ranking scores')
    return p


def fit_reduced_logistic(x,delta,unavailable,y,weights):
    x,d,u=validate_inputs(x,delta,unavailable); a=np.column_stack((x,d,u.astype(float)))
    sc=StandardScaler(); xs=sc.fit_transform(a)
    lr=LogisticRegression(penalty=None,solver='lbfgs',max_iter=1000,tol=1e-4,random_state=260711)
    with warnings.catch_warnings(record=True) as ws:
        warnings.simplefilter('always');lr.fit(xs,np.asarray(y,int),sample_weight=weights)
    conv=[str(w.message) for w in ws if issubclass(w.category,ConvergenceWarning)]
    if conv:raise GateError('Reduced-logistic convergence HOLD: '+str(conv))
    return {'mean':sc.mean_.tolist(),'scale':sc.scale_.tolist(),'coef':lr.coef_[0].tolist(),
            'intercept':float(lr.intercept_[0]),'iterations':int(lr.n_iter_[0]),'warnings':[str(w.message) for w in ws]}


def score_reduced_logistic(model,x,delta,unavailable):
    x,d,u=validate_inputs(x,delta,unavailable); a=np.column_stack((x,d,u.astype(float)))
    return expit(((a-np.array(model['mean']))/np.array(model['scale']))@np.array(model['coef'])+model['intercept'])


def average_precision(y,s):
    y=np.asarray(y,int);s=np.asarray(s,float)
    if len(y)!=len(s) or not np.isfinite(s).all() or not np.isin(y,[0,1]).all():raise GateError('Invalid metrics inputs')
    if y.sum()==0:return float('nan')
    o=np.argsort(-s,kind='stable');ss=s[o];yy=y[o];ends=np.r_[np.flatnonzero(np.diff(ss)!=0),len(y)-1]
    tp=np.cumsum(yy)[ends]; recall=tp/y.sum()
    return float(np.sum(np.diff(np.r_[0,recall])*(tp/(ends+1))))


def topk_ties(y,s,k):
    y=np.asarray(y,int);s=np.asarray(s,float)
    if k<=0 or len(y)!=len(s) or len(s)==0 or not np.isfinite(s).all():raise GateError('Invalid Top-K inputs')
    k=min(k,len(s)); threshold=float(np.partition(s,len(s)-k)[len(s)-k]); above=s>threshold; equal=s==threshold
    slots=int(k-above.sum()); n=int(equal.sum()); e=int(y[equal].sum()); fixed=int(y[above].sum())
    sure=above | (equal if slots==n else False);possible=above|equal
    return {'k':k,'threshold':threshold,'tie_size':n,'remaining_slots':slots,
            'tp_min':fixed+max(0,slots-(n-e)),'tp_max':fixed+min(slots,e),
            'event_sure_mask':sure & (y==1),'event_possible_mask':possible & (y==1)}
