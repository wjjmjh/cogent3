#!/usr/bin/env python
import os
import warnings

from numpy.testing import assert_allclose, assert_equal

warnings.filterwarnings('ignore', 'Not using MPI as mpi4py not found')

import numpy

# hides the warning from taking log of -ve determinant
numpy.seterr(invalid='ignore')

from unittest import TestCase, main
from cogent3 import LoadSeqs, DNA, RNA, PROTEIN
from cogent3.evolve.distance import EstimateDistances
from cogent3.evolve.fast_distance import (get_moltype_index_array,
                                          seq_to_indices,
                                          _fill_diversity_matrix,
                                          _jc69_from_matrix, JC69Pair,
                                          _tn93_from_matrix, TN93Pair,
                                          LogDetPair,
                                          ParalinearPair, HammingPair,
                                          _hamming, get_calculator,
                                          _calculators,
                                          available_distances,
                                          DistanceMatrix, )
from cogent3.evolve.models import JC69, HKY85, F81
from cogent3.evolve._pairwise_distance import \
    _fill_diversity_matrix as pyx_fill_diversity_matrix

__author__ = "Gavin Huttley, Yicheng Zhu and Ben Kaehler"
__copyright__ = "Copyright 2007-2016, The Cogent Project"
__credits__ = ["Gavin Huttley", "Yicheng Zhu", "Ben Kaehler"]
__license__ = "GPL"
__version__ = "3.0a2"
__maintainer__ = "Gavin Huttley"
__email__ = "Gavin.Huttley@anu.edu.au"
__status__ = "Production"


class TestPair(TestCase):
    dna_char_indices = get_moltype_index_array(DNA)
    rna_char_indices = get_moltype_index_array(RNA)
    alignment = LoadSeqs(data=[('s1', 'ACGTACGTAC'),
                               ('s2', 'GTGTACGTAC')], moltype=DNA)

    ambig_alignment = LoadSeqs(data=[('s1', 'RACGTACGTACN'),
                                     ('s2', 'AGTGTACGTACA')], moltype=DNA)

    diff_alignment = LoadSeqs(data=[('s1', 'ACGTACGTTT'),
                                    ('s2', 'GTGTACGTAC')], moltype=DNA)

    def test_char_to_index(self):
        """should correctly recode a DNA & RNA seqs into indices"""
        seq = 'TCAGRNY?-'
        expected = [0, 1, 2, 3, -9, -9, -9, -9, -9]
        indices = seq_to_indices(seq, self.dna_char_indices)
        assert_equal(indices, expected)
        seq = 'UCAGRNY?-'
        indices = seq_to_indices(seq, self.rna_char_indices)
        assert_equal(indices, expected)

    def test_fill_diversity_matrix_all(self):
        """make correct diversity matrix when all chars valid"""
        s1 = seq_to_indices('ACGTACGTAC', self.dna_char_indices)
        s2 = seq_to_indices('GTGTACGTAC', self.dna_char_indices)
        matrix = numpy.zeros((4, 4), float)
        # self-self should just be an identity matrix
        _fill_diversity_matrix(matrix, s1, s1)
        assert_equal(matrix.sum(), len(s1))
        assert_equal(matrix,
                         numpy.array([[2, 0, 0, 0],
                                      [0, 3, 0, 0],
                                      [0, 0, 3, 0],
                                      [0, 0, 0, 2]], float))

        # small diffs
        matrix.fill(0)
        _fill_diversity_matrix(matrix, s1, s2)
        assert_equal(matrix, numpy.array([[2, 0, 0, 0],
                                          [1, 2, 0, 0],
                                          [0, 0, 2, 1],
                                          [0, 0, 0, 2]], float))

    def test_fill_diversity_matrix_some(self):
        """make correct diversity matrix when not all chars valid"""
        s1 = seq_to_indices('RACGTACGTACN', self.dna_char_indices)
        s2 = seq_to_indices('AGTGTACGTACA', self.dna_char_indices)
        matrix = numpy.zeros((4, 4), float)
        # small diffs
        matrix.fill(0)
        _fill_diversity_matrix(matrix, s1, s2)
        assert_equal(matrix, numpy.array([[2, 0, 0, 0],
                                          [1, 2, 0, 0],
                                          [0, 0, 2, 1],
                                          [0, 0, 0, 2]], float))

    def test_python_vs_cython_fill_matrix(self):
        """python & cython fill_diversity_matrix give same answer"""
        s1 = seq_to_indices('RACGTACGTACN', self.dna_char_indices)
        s2 = seq_to_indices('AGTGTACGTACA', self.dna_char_indices)
        matrix1 = numpy.zeros((4, 4), float)
        _fill_diversity_matrix(matrix1, s1, s2)
        matrix2 = numpy.zeros((4, 4), float)
        pyx_fill_diversity_matrix(matrix2, s1, s2)
        assert_allclose(matrix1, matrix2)

    def test_hamming_from_matrix(self):
        """compute hamming from diversity matrix"""
        s1 = seq_to_indices('ACGTACGTAC', self.dna_char_indices)
        s2 = seq_to_indices('GTGTACGTAC', self.dna_char_indices)
        matrix = numpy.zeros((4, 4), float)
        _fill_diversity_matrix(matrix, s1, s2)
        total, p, dist, var = _hamming(matrix)
        self.assertEqual(total, 10.0)
        self.assertEqual(dist, 2)
        self.assertEqual(p, 0.2)

    def test_jc69_from_matrix(self):
        """compute JC69 from diversity matrix"""
        s1 = seq_to_indices('ACGTACGTAC', self.dna_char_indices)
        s2 = seq_to_indices('GTGTACGTAC', self.dna_char_indices)
        matrix = numpy.zeros((4, 4), float)
        _fill_diversity_matrix(matrix, s1, s2)
        total, p, dist, var = _jc69_from_matrix(matrix)
        self.assertEqual(total, 10.0)
        self.assertEqual(p, 0.2)

    def test_wrong_moltype(self):
        """specifying wrong moltype raises ValueError"""
        with self.assertRaises(ValueError):
            _ = JC69Pair(PROTEIN, alignment=self.alignment)

    def test_jc69_from_alignment(self):
        """compute JC69 dists from an alignment"""
        calc = JC69Pair(DNA, alignment=self.alignment)
        calc.run(show_progress=False)
        self.assertEqual(calc.lengths['s1', 's2'], 10)
        self.assertEqual(calc.proportions['s1', 's2'], 0.2)
        # value from OSX MEGA 5
        assert_allclose(calc.dists['s1', 's2'], 0.2326161962)
        # value**2 from OSX MEGA 5
        assert_allclose(calc.variances['s1', 's2'],
                              0.029752066125078681)
        # value from OSX MEGA 5
        assert_allclose(calc.stderr['s1', 's2'], 0.1724878724)

        # same answer when using ambiguous alignment
        calc.run(self.ambig_alignment, show_progress=False)
        assert_allclose(calc.dists['s1', 's2'], 0.2326161962)

        # but different answer if subsequent alignment is different
        calc.run(self.diff_alignment, show_progress=False)
        self.assertTrue(calc.dists['s1', 's2'] != 0.2326161962)

    def test_tn93_from_matrix(self):
        """compute TN93 distances"""
        calc = TN93Pair(DNA, alignment=self.alignment)
        calc.run(show_progress=False)
        self.assertEqual(calc.lengths['s1', 's2'], 10)
        self.assertEqual(calc.proportions['s1', 's2'], 0.2)
        # value from OSX MEGA 5
        assert_allclose(calc.dists['s1', 's2'], 0.2554128119)
        # value**2 from OSX MEGA 5
        assert_allclose(calc.variances['s1', 's2'], 0.04444444445376601)
        # value from OSX MEGA 5
        assert_allclose(calc.stderr['s1', 's2'], 0.2108185107)

        # same answer when using ambiguous alignment
        calc.run(self.ambig_alignment, show_progress=False)
        assert_allclose(calc.dists['s1', 's2'], 0.2554128119)

        # but different answer if subsequent alignment is different
        calc.run(self.diff_alignment, show_progress=False)
        self.assertTrue(calc.dists['s1', 's2'] != 0.2554128119)

    def test_distance_pair(self):
        """get distances dict"""
        calc = TN93Pair(DNA, alignment=self.alignment)
        calc.run(show_progress=False)
        dists = calc.get_pairwise_distances()
        dists = dists.todict()
        dist = 0.2554128119
        expect = {('s1', 's2'): dist, ('s2', 's1'): dist}
        self.assertEqual(list(dists.keys()), list(expect.keys()))
        assert_allclose(list(dists.values()), list(expect.values()))

    def test_logdet_pair_dna(self):
        """logdet should produce distances that match MEGA"""
        aln = LoadSeqs('data/brca1_5.paml', moltype=DNA)
        logdet_calc = LogDetPair(moltype=DNA, alignment=aln)
        logdet_calc.run(use_tk_adjustment=True, show_progress=False)
        dists = logdet_calc.get_pairwise_distances().todict()
        all_expected = {('Human', 'NineBande'): 0.075336929999999996,
                        ('NineBande', 'DogFaced'): 0.0898575452,
                        ('DogFaced', 'Human'): 0.1061747919,
                        ('HowlerMon', 'DogFaced'): 0.0934480008,
                        ('Mouse', 'HowlerMon'): 0.26422862920000001,
                        ('NineBande', 'Human'): 0.075336929999999996,
                        ('HowlerMon', 'NineBande'): 0.062202897899999998,
                        ('DogFaced', 'NineBande'): 0.0898575452,
                        ('DogFaced', 'HowlerMon'): 0.0934480008,
                        ('Human', 'DogFaced'): 0.1061747919,
                        ('Mouse', 'Human'): 0.26539976700000001,
                        ('NineBande', 'HowlerMon'): 0.062202897899999998,
                        ('HowlerMon', 'Human'): 0.036571181899999999,
                        ('DogFaced', 'Mouse'): 0.2652555144,
                        ('HowlerMon', 'Mouse'): 0.26422862920000001,
                        ('Mouse', 'DogFaced'): 0.2652555144,
                        ('NineBande', 'Mouse'): 0.22754789210000001,
                        ('Mouse', 'NineBande'): 0.22754789210000001,
                        ('Human', 'Mouse'): 0.26539976700000001,
                        ('Human', 'HowlerMon'): 0.036571181899999999}
        for pair in dists:
            got = dists[pair]
            expected = all_expected[pair]
            assert_allclose(got, expected)

    def test_logdet_tk_adjustment(self):
        """logdet using tamura kumar differs from classic"""
        aln = LoadSeqs('data/brca1_5.paml', moltype=DNA)
        logdet_calc = LogDetPair(moltype=DNA, alignment=aln)
        logdet_calc.run(use_tk_adjustment=True, show_progress=False)
        tk = logdet_calc.get_pairwise_distances()
        logdet_calc.run(use_tk_adjustment=False, show_progress=False)
        not_tk = logdet_calc.get_pairwise_distances()
        self.assertNotEqual(tk, not_tk)

    def test_logdet_pair_aa(self):
        """logdet shouldn't fail to produce distances for aa seqs"""
        aln = LoadSeqs('data/brca1_5.paml', moltype=DNA)
        aln = aln.get_translation()
        logdet_calc = LogDetPair(moltype=PROTEIN, alignment=aln)
        logdet_calc.run(use_tk_adjustment=True, show_progress=False)
        dists = logdet_calc.get_pairwise_distances()

    def test_logdet_missing_states(self):
        """should calculate logdet measurement with missing states"""
        data = [('seq1',
                 "GGGGGGGGGGGCCCCCCCCCCCCCCCCCGGGGGGGGGGGGGGGCGGTTTTTTTTTTTTTTTTTT"),
                ('seq2',
                 "TAAAAAAAAAAGGGGGGGGGGGGGGGGGGTTTTTNTTTTTTTTTTTTCCCCCCCCCCCCCCCCC")]
        aln = LoadSeqs(data=data, moltype=DNA)
        logdet_calc = LogDetPair(moltype=DNA, alignment=aln)
        logdet_calc.run(use_tk_adjustment=True, show_progress=False)

        dists = logdet_calc.get_pairwise_distances().todict()
        self.assertTrue(list(dists.values())[0] is not None)

        logdet_calc.run(use_tk_adjustment=False, show_progress=False)
        dists = logdet_calc.get_pairwise_distances().todict()
        self.assertTrue(list(dists.values())[0] is not None)

    def test_logdet_variance(self):
        """calculate logdet variance consistent with hand calculation"""
        data = [('seq1',
                 "GGGGGGGGGGGCCCCCCCCCCCCCCCCCGGGGGGGGGGGGGGGCGGTTTTTTTTTTTTTTTTTT"),
                ('seq2',
                 "TAAAAAAAAAAGGGGGGGGGGGGGGGGGGTTTTTTTTTTTTTTTTTTCCCCCCCCCCCCCCCCC")]
        aln = LoadSeqs(data=data, moltype=DNA)
        logdet_calc = LogDetPair(moltype=DNA, alignment=aln)
        logdet_calc.run(use_tk_adjustment=True, show_progress=False)
        self.assertEqual(logdet_calc.variances[1, 1], None)

        index = dict(list(zip('ACGT', list(range(4)))))
        J = numpy.zeros((4, 4))
        for p in zip(data[0][1], data[1][1]):
            J[index[p[0]], index[p[1]]] += 1
        for i in range(4):
            if J[i, i] == 0:
                J[i, i] += 0.5
        J /= J.sum()
        M = numpy.linalg.inv(J)
        var = 0.
        for i in range(4):
            for j in range(4):
                var += M[j, i] ** 2 * J[i, j] - 1
        var /= 16 * len(data[0][1])

        logdet_calc.run(use_tk_adjustment=False, show_progress=False)
        dists = logdet_calc.get_pairwise_distances()
        assert_allclose(logdet_calc.variances[1, 1], var, atol=1e-3)

    def test_logdet_for_determinant_lte_zero(self):
        """returns distance of None if the determinant is <= 0"""
        data = dict(
            seq1="AGGGGGGGGGGCCCCCCCCCCCCCCCCCGGGGGGGGGGGGGGGCGGTTTTTTTTTTTTTTTTTT",
            seq2="TAAAAAAAAAAGGGGGGGGGGGGGGGGGGTTTTTTTTTTTTTTTTTTCCCCCCCCCCCCCCCCC")
        aln = LoadSeqs(data=data, moltype=DNA)

        logdet_calc = LogDetPair(moltype=DNA, alignment=aln)
        logdet_calc.run(use_tk_adjustment=True, show_progress=False)
        dists = logdet_calc.get_pairwise_distances().todict()
        self.assertTrue(list(dists.values())[0] is None)
        logdet_calc.run(use_tk_adjustment=False, show_progress=False)
        dists = logdet_calc.get_pairwise_distances().todict()
        self.assertTrue(list(dists.values())[0] is None)

    def test_paralinear_pair_aa(self):
        """paralinear shouldn't fail to produce distances for aa seqs"""
        aln = LoadSeqs('data/brca1_5.paml', moltype=DNA)
        aln = aln.get_translation()
        paralinear_calc = ParalinearPair(moltype=PROTEIN, alignment=aln)
        paralinear_calc.run(show_progress=False)
        dists = paralinear_calc.get_pairwise_distances()

    def test_paralinear_distance(self):
        """calculate paralinear variance consistent with hand calculation"""
        data = [('seq1',
                 "GGGGGGGGGGGCCCCCCCCCCCCCCCCCGGGGGGGGGGGGGGGCGGTTTTTTTTTTTTTTTTTT"),
                ('seq2',
                 "TAAAAAAAAAAGGGGGGGGGGGGGGGGGGTTTTTTTTTTTTTTTTTTCCCCCCCCCCCCCCCCC")]
        aln = LoadSeqs(data=data, moltype=DNA)
        paralinear_calc = ParalinearPair(moltype=DNA, alignment=aln)
        paralinear_calc.run(show_progress=False)

        index = dict(list(zip('ACGT', list(range(4)))))
        J = numpy.zeros((4, 4))
        for p in zip(data[0][1], data[1][1]):
            J[index[p[0]], index[p[1]]] += 1
        for i in range(4):
            if J[i, i] == 0:
                J[i, i] += 0.5
        J /= J.sum()
        M = numpy.linalg.inv(J)
        f = J.sum(1), J.sum(0)
        dist = -0.25 * numpy.log(numpy.linalg.det(J) /
                                 numpy.sqrt(f[0].prod() * f[1].prod()))

        assert_allclose(paralinear_calc.dists['seq1', 'seq2'], dist)

    def test_paralinear_variance(self):
        """calculate paralinear variance consistent with hand calculation"""
        data = [('seq1',
                 "GGGGGGGGGGGCCCCCCCCCCCCCCCCCGGGGGGGGGGGGGGGCGGTTTTTTTTTTTTTTTTTT"),
                ('seq2',
                 "TAAAAAAAAAAGGGGGGGGGGGGGGGGGGTTTTTTTTTTTTTTTTTTCCCCCCCCCCCCCCCCC")]
        aln = LoadSeqs(data=data, moltype=DNA)
        paralinear_calc = ParalinearPair(moltype=DNA, alignment=aln)
        paralinear_calc.run(show_progress=False)

        index = dict(list(zip('ACGT', list(range(4)))))
        J = numpy.zeros((4, 4))
        for p in zip(data[0][1], data[1][1]):
            J[index[p[0]], index[p[1]]] += 1
        for i in range(4):
            if J[i, i] == 0:
                J[i, i] += 0.5
        J /= J.sum()
        M = numpy.linalg.inv(J)
        f = J.sum(1), J.sum(0)
        var = 0.
        for i in range(4):
            for j in range(4):
                var += M[j, i] ** 2 * J[i, j]
            var -= 1 / numpy.sqrt(f[0][i] * f[1][i])
        var /= 16 * len(data[0][1])

        assert_allclose(paralinear_calc.variances[1, 1], var, atol=1e-3)

    def test_paralinear_for_determinant_lte_zero(self):
        """returns distance of None if the determinant is <= 0"""
        data = dict(
            seq1="AGGGGGGGGGGCCCCCCCCCCCCCCCCCGGGGGGGGGGGGGGGCGGTTTTTTTTTTTTTTTTTT",
            seq2="TAAAAAAAAAAGGGGGGGGGGGGGGGGGGTTTTTTTTTTTTTTTTTTCCCCCCCCCCCCCCCCC")
        aln = LoadSeqs(data=data, moltype=DNA)

        paralinear_calc = ParalinearPair(moltype=DNA, alignment=aln)
        paralinear_calc.run(show_progress=False)
        dists = paralinear_calc.get_pairwise_distances().todict()
        self.assertTrue(list(dists.values())[0] is None)
        paralinear_calc.run(show_progress=False)
        dists = paralinear_calc.get_pairwise_distances().todict()
        self.assertTrue(list(dists.values())[0] is None)

    def test_paralinear_pair_dna(self):
        """calculate paralinear distance consistent with logdet distance"""
        data = [('seq1',
                 'TAATTCATTGGGACGTCGAATCCGGCAGTCCTGCCGCAAAAGCTTCCGGAATCGAATTTTGGCA'),
                ('seq2',
                 'AAAAAAAAAAAAAAAACCCCCCCCCCCCCCCCTTTTTTTTTTTTTTTTGGGGGGGGGGGGGGGG')]
        aln = LoadSeqs(data=data, moltype=DNA)
        paralinear_calc = ParalinearPair(moltype=DNA, alignment=aln)
        paralinear_calc.run(show_progress=False)
        logdet_calc = LogDetPair(moltype=DNA, alignment=aln)
        logdet_calc.run(show_progress=False)
        self.assertEqual(logdet_calc.dists[1, 1],
                              paralinear_calc.dists[1, 1])
        self.assertEqual(paralinear_calc.variances[1, 1],
                              logdet_calc.variances[1, 1])

    def test_duplicated(self):
        """correctly identifies duplicates"""

        def get_calc(data):
            aln = LoadSeqs(data=data, moltype=DNA)
            calc = ParalinearPair(moltype=DNA, alignment=aln)
            calc(show_progress=False)
            return calc

        # no duplicates
        data = [('seq1',
                 "GGGGGGGGGGGCCCCCCCCCCCCCCCCCGGGGGGGGGGGGGGGCGGTTTTTTTTTTTTTTTTTT"),
                ('seq2',
                 "TAAAAAAAAAAGGGGGGGGGGGGGGGGGGTTTTTTTTTTTTTTTTTTCCCCCCCCCCCCCCCCC")]
        calc = get_calc(data)
        self.assertEqual(calc.duplicated, None)
        data = [('seq1',
                 "GGGGGGGGGGGCCCCCCCCCCCCCCCCCGGGGGGGGGGGGGGGCGGTTTTTTTTTTTTTTTTTT"),
                ('seq2',
                 "TAAAAAAAAAAGGGGGGGGGGGGGGGGGGTTTTTTTTTTTTTTTTTTCCCCCCCCCCCCCCCCC"),
                ('seq3',
                 "TAAAAAAAAAAGGGGGGGGGGGGGGGGGGTTTTTTTTTTTTTTTTTTCCCCCCCCCCCCCCCCC")]
        calc = get_calc(data)
        self.assertTrue({"seq2": ["seq3"]} == calc.duplicated or
                        {"seq3": ["seq2"]} == calc.duplicated)
        # default to get all pairwise distances
        pwds = calc.get_pairwise_distances().todict()
        self.assertEqual(pwds[('seq2', 'seq3')], 0.0)
        self.assertEqual(pwds[('seq2', 'seq1')], pwds[('seq3', 'seq1')])

        # only unique seqs when using include_duplicates=False

        pwds = calc.get_pairwise_distances(include_duplicates=False).todict()
        present = list(calc.duplicated.keys())[0]
        missing = calc.duplicated[present][0]
        self.assertEqual(set([(present, missing)]), set([('seq2', 'seq3')]))
        self.assertTrue((present, 'seq1') in pwds)
        self.assertFalse((missing, 'seq1') in pwds)


class TestGetDisplayCalculators(TestCase):
    def test_get_calculator(self):
        """exercising getting specified calculator"""
        for key in _calculators:
            get_calculator(key)
            get_calculator(key.upper())

        with self.assertRaises(ValueError):
            get_calculator('blahblah')

    def test_available_distances(self):
        """available_distances has correct content"""
        content = available_distances()
        self.assertEqual(content.shape, (5, 2))
        self.assertEqual(content['tn93', 1], 'dna, rna')


class TestDistanceMatrix(TestCase):
    def test_to_dict(self):
        """distance matrix correctly produces a 1D dict"""
        data = {('s1', 's2'): 0.25, ('s2', 's1'): 0.25}
        dmat = DistanceMatrix(data)
        got = dmat.todict()
        self.assertEqual(got, data)

    def test_dropping_from_matrix(self):
        """pairwise distances should have method for dropping invalid data"""
        data = {('ABAYE2984', 'Atu3667'): None,
                ('ABAYE2984', 'Avin_42730'): 0.638,
                ('ABAYE2984', 'BAA10469'): None,
                ('Atu3667', 'ABAYE2984'): None,
                ('Atu3667', 'Avin_42730'): 2.368,
                ('Atu3667', 'BAA10469'): None,
                ('Avin_42730', 'ABAYE2984'): 0.638,
                ('Avin_42730', 'Atu3667'): 2.368,
                ('Avin_42730', 'BAA10469'): 1.85,
                ('BAA10469', 'ABAYE2984'): None,
                ('BAA10469', 'Atu3667'): None,
                ('BAA10469', 'Avin_42730'): 1.85}

        darr = DistanceMatrix(data)
        new = darr.drop_invalid()
        self.assertEqual(new, None)

        data = {('ABAYE2984', 'Atu3667'): 0.25,
                ('ABAYE2984', 'Avin_42730'): 0.638,
                ('ABAYE2984', 'BAA10469'): None,
                ('Atu3667', 'ABAYE2984'): 0.25,
                ('Atu3667', 'Avin_42730'): 2.368,
                ('Atu3667', 'BAA10469'): 0.25,
                ('Avin_42730', 'ABAYE2984'): 0.638,
                ('Avin_42730', 'Atu3667'): 2.368,
                ('Avin_42730', 'BAA10469'): 1.85,
                ('BAA10469', 'ABAYE2984'): 0.25,
                ('BAA10469', 'Atu3667'): 0.25,
                ('BAA10469', 'Avin_42730'): 1.85}
        darr = DistanceMatrix(data)
        new = darr.drop_invalid()
        self.assertEqual(new.shape, (2, 2))

class DistancesTests(TestCase):

    def setUp(self):
        self.al = LoadSeqs(data={'a': 'GTACGTACGATC',
                                   'b': 'GTACGTACGTAC',
                                   'c': 'GTACGTACGTTC',
                                   'e': 'GTACGTACTGGT'})
        self.collection = LoadSeqs(data={'a': 'GTACGTACGATC',
                                           'b': 'GTACGTACGTAC',
                                           'c': 'GTACGTACGTTC',
                                           'e': 'GTACGTACTGGT'}, aligned=False)

    def assertDistsAlmostEqual(self, expected, observed, precision=4):
        observed = dict([(frozenset(k), v)
                        for (k, v) in list(observed.items())])
        expected = dict([(frozenset(k), v)
                        for (k, v) in list(expected.items())])
        for key in expected:
            self.assertAlmostEqual(expected[key], observed[key], precision)

    def test_EstimateDistances(self):
        """testing (well, exercising at least), EstimateDistances"""
        d = EstimateDistances(self.al, JC69())
        d.run()
        canned_result = {('b', 'e'): 0.440840,
                         ('c', 'e'): 0.440840,
                         ('a', 'c'): 0.088337,
                         ('a', 'b'): 0.188486,
                         ('a', 'e'): 0.440840,
                         ('b', 'c'): 0.0883373}
        result = d.get_pairwise_distances().todict()
        self.assertDistsAlmostEqual(canned_result, result)

        # excercise writing to file
        d.write('junk.txt')
        try:
            os.remove('junk.txt')
        except OSError:
            pass  # probably parallel

    def test_EstimateDistancesWithMotifProbs(self):
        """EstimateDistances with supplied motif probs"""
        motif_probs = {'A': 0.1, 'C': 0.2, 'G': 0.2, 'T': 0.5}
        d = EstimateDistances(self.al, HKY85(), motif_probs=motif_probs)
        d.run()
        canned_result = {('a', 'c'): 0.07537,
                         ('b', 'c'): 0.07537,
                         ('a', 'e'): 0.39921,
                         ('a', 'b'): 0.15096,
                         ('b', 'e'): 0.39921,
                         ('c', 'e'): 0.37243}
        result = d.get_pairwise_distances().todict()
        self.assertDistsAlmostEqual(canned_result, result)

    def test_EstimateDistances_fromThreeway(self):
        """testing (well, exercising at least), EsimateDistances fromThreeway"""
        d = EstimateDistances(self.al, JC69(), threeway=True)
        d.run()
        canned_result = {('b', 'e'): 0.495312,
                         ('c', 'e'): 0.479380,
                         ('a', 'c'): 0.089934,
                         ('a', 'b'): 0.190021,
                         ('a', 'e'): 0.495305,
                         ('b', 'c'): 0.0899339}
        result = d.get_pairwise_distances(summary_function="mean").todict()
        self.assertDistsAlmostEqual(canned_result, result)

    def test_EstimateDistances_fromUnaligned(self):
        """Excercising estimate distances from unaligned sequences"""
        d = EstimateDistances(self.collection, JC69(), do_pair_align=True,
                              rigorous_align=True)
        d.run()
        canned_result = {('b', 'e'): 0.440840,
                         ('c', 'e'): 0.440840,
                         ('a', 'c'): 0.088337,
                         ('a', 'b'): 0.188486,
                         ('a', 'e'): 0.440840,
                         ('b', 'c'): 0.0883373}
        result = d.get_pairwise_distances().todict()
        self.assertDistsAlmostEqual(canned_result, result)

        d = EstimateDistances(self.collection, JC69(), do_pair_align=True,
                              rigorous_align=False)
        d.run()
        canned_result = {('b', 'e'): 0.440840,
                         ('c', 'e'): 0.440840,
                         ('a', 'c'): 0.088337,
                         ('a', 'b'): 0.188486,
                         ('a', 'e'): 0.440840,
                         ('b', 'c'): 0.0883373}
        result = d.get_pairwise_distances().todict()
        self.assertDistsAlmostEqual(canned_result, result)

    def test_EstimateDistances_other_model_params(self):
        """test getting other model params from EstimateDistances"""
        d = EstimateDistances(self.al, HKY85(), est_params=['kappa'])
        d.run()
        # this will be a Number object with Mean, Median etc ..
        kappa = d.get_param_values('kappa')
        self.assertAlmostEqual(kappa.mean, 0.8939, 4)
        # this will be a dict with pairwise instances, it's called by the above
        # method, so the correctness of it's values is already checked
        kappa = d.get_pairwise_param('kappa')

    def test_EstimateDistances_modify_lf(self):
        """tests modifying the lf"""
        def constrain_fit(lf):
            lf.set_param_rule('kappa', is_constant=True)
            lf.optimise(local=True)
            return lf

        d = EstimateDistances(self.al, HKY85(), modify_lf=constrain_fit)
        d.run()
        result = d.get_pairwise_distances().todict()
        d = EstimateDistances(self.al, F81())
        d.run()
        expect = d.get_pairwise_distances().todict()
        self.assertDistsAlmostEqual(expect, result)

    def test_get_raw_estimates(self):
        """correctly return raw result object"""
        d = EstimateDistances(self.al, HKY85(), est_params=['kappa'])
        d.run()
        expect = {('a', 'b'): {'kappa': 1.0000226766004808e-06, 'length': 0.18232155856115662},
                  ('a', 'c'): {'kappa': 1.0010380037049357e-06, 'length': 0.087070406623635604},
                  ('a', 'e'): {'kappa': 2.3965871843412687, 'length': 0.4389176272584539},
                  ('b', 'e'): {'kappa': 2.3965871854366592, 'length': 0.43891762729173389},
                  ('b', 'c'): {'kappa': 1.0010380037049357e-06, 'length': 0.087070406623635604},
                  ('c', 'e'): {'kappa': 0.57046787478038707, 'length': 0.43260232210282784}}
        got = d.get_all_param_values()
        for pair in expect:
            for param in expect[pair]:
                self.assertAlmostEqual(got[pair][param], expect[
                                       pair][param], places=6)

if __name__ == '__main__':
    main()