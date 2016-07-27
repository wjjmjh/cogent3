#!/usr/bin/env python'
from .tree_space import TreeEvaluator, ancestry2tree
from .least_squares import WLS
from math import exp
from .tree_collection import LogLikelihoodScoredTreeCollection
from .tree_collection import LoadTrees  # only for back compat.

__author__ = "Peter Maxwell"
__copyright__ = "Copyright 2007-2012, The Cogent Project"
__credits__ = ["Peter Maxwell", "Gavin Huttley"]
__license__ = "GPL"
__version__ = "1.5.3-dev"
__maintainer__ = "Peter Maxwell"
__email__ = "pm67nz@gmail.com"
__status__ = "Production"


class ML(TreeEvaluator):
    """(err, best_tree) = ML(model, alignment, [dists]).trex()

    'model' can be a substitution model or a likelihood function factory
    equivalent to SubstitutionModel.make_likelihood_function(tree).
    If 'dists' is provided uses WLS to get initial values for lengths"""

    def __init__(self, model, alignment, dists=None, opt_args={}):
        self.opt_args = opt_args
        self.names = alignment.get_seq_names()
        self.alignment = alignment
        if hasattr(model, 'make_likelihood_function'):
            self.lf_factory = lambda tree: model.make_likelihood_function(tree)
        else:
            self.lf_factory = model
        if dists:
            self.wlsMakeTreeScorer = WLS(dists).makeTreeScorer
        else:
            fake_wls = lambda a: (None, None)
            self.wlsMakeTreeScorer = lambda n: fake_wls

    def evaluateTree(self, tree):
        names = tree.get_tip_names()
        subalign = self.alignment.take_seqs(names)
        lf = self.lf_factory(tree)
        lf.set_alignment(subalign)
        return lf.get_log_likelihood()

    def makeTreeScorer(self, names):
        subalign = self.alignment.take_seqs(names)
        wls_eval = self.wlsMakeTreeScorer(names)

        def evaluate(ancestry, lengths=None):
            if lengths is None:
                (wls_err, init_lengths) = wls_eval(ancestry)
            else:
                init_lengths = lengths
            tree = ancestry2tree(ancestry, init_lengths, names)
            lf = self.lf_factory(tree)
            lf.set_alignment(subalign)
            if lengths is not None:
                lf.set_param_rule('length', is_constant=True)
            lf.optimise(show_progress=False, **self.opt_args)
            err = -1.0 * lf.get_log_likelihood()
            tree = lf.get_annotated_tree()
            return (err, tree)
        return evaluate

    def result2output(self, err, ancestry, annotated_tree, names):
        return (-1.0 * err, annotated_tree)

    def results2output(self, results):
        return LogLikelihoodScoredTreeCollection(results)
