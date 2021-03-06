import unittest
import sys
import torch
import numpy as np
sys.path.append("..")
from games.guessit import OnePlayerGuessIt, TwoPlayerGuessIt
from games.leapfrog import ThreePlayerLeapFrog, ThreePlayerLinearLeapFrog
from mcts import MCTS
from neural_network import NeuralNetwork
from models.biasednet import BiasedNet


class MCTSTest(unittest.TestCase):

    # Check that statistics of out-edges from expanded node are correct.
    def assertExpanded(self, state, mcts):
        hashed_s = mcts.np_hash(state)
        num_actions = len(mcts.tree[hashed_s])
        for v in mcts.tree[hashed_s]:
            np.testing.assert_almost_equal(v[1:].reshape(-1).astype(np.float32), np.array([0, 0, 1/num_actions], dtype=np.float32))

    # Allows you to check edge statistics (N, Q, P)
    def assertEdge(self, state, action, mcts, statistics, heuristic=None):
        true_stats = mcts.tree[mcts.np_hash(state)]
        i = np.where((np.array(true_stats[:,0].tolist()) == action).all(axis=1))[0][0]
        np.testing.assert_almost_equal(mcts.tree[mcts.np_hash(state)][i,1:].astype(np.float32), np.array(statistics, dtype=np.float32))

        if heuristic != None:
            n_total = true_stats[:,1].sum()
            self.assertEqual(statistics[1] + statistics[2]*(n_total**.5/(1+statistics[0])), heuristic)

class GuessItTest(MCTSTest):

    # Test that our MCTS behaves as expected for a one-player game of guess-it
    def test_one_player_guess_it(self):
        gi = OnePlayerGuessIt()
        b = NeuralNetwork(gi, BiasedNet)
        m = MCTS(gi, b)
        self.assertEqual(m.tree, {})
        init = gi.get_initial_state()

        # First simulation
        m.simulate(init) # Adds root and outward edges
        self.assertIn(m.np_hash(init), m.tree) # Root added to tree
        self.assertEqual(len(m.tree), 1)
        self.assertExpanded(init, m)
        self.assertListEqual(list(m.get_distribution(init, temperature=0)[:,1]), [1, 0, 0, 0])
        self.assertListEqual(list(m.get_distribution(init, temperature=.000000000001)[:,1]), [.25, .25, .25, .25])
        self.assertListEqual(list(m.get_distribution(init, temperature=.5)[:,1]), [.25, .25, .25, .25])
        self.assertListEqual(list(m.get_distribution(init, temperature=1)[:,1]), [.25, .25, .25, .25])
        self.assertListEqual(list(m.get_distribution(init, temperature=100)[:,1]), [.25, .25, .25, .25])

        # Second simulation
        m.simulate(init)
        s = gi.take_action(init, np.array([[1,0],[0,0]])) # Takes first action since uniform
        self.assertIn(m.np_hash(s), m.tree) # Node added to tree
        self.assertEqual(len(m.tree), 2)
        self.assertExpanded(s, m)
        self.assertEdge(init, np.array([0,0]), m, [1,.5,.25])
        self.assertEdge(init, np.array([0,1]), m, [0,0,.25])
        self.assertListEqual(list(m.get_distribution(init, temperature=0)[:,1]), [1, 0, 0, 0])
        self.assertListEqual(list(m.get_distribution(init, temperature=.00000001)[:,1]), [1, 0, 0, 0])
        self.assertListEqual(list(m.get_distribution(init, temperature=1)[:,1]), [1, 0, 0, 0])
        self.assertListEqual(list(m.get_distribution(s, temperature=1)[:,1]), [1/3]*3)

        # Third simulation
        m.simulate(init)
        s_prev = s
        s = gi.take_action(s_prev, np.array([[0,1],[0,0]])) # Takes first action since uniform
        self.assertIn(m.np_hash(s), m.tree) # Node added to tree
        self.assertEqual(len(m.tree), 3)
        self.assertExpanded(s, m)
        self.assertEdge(init, np.array([0,0]), m, [2,.5,.25])
        self.assertEdge(init, np.array([0,1]), m, [0,0,.25])
        self.assertEdge(s_prev, np.array([0,1]), m, [1,.5, 1/3])
        self.assertEdge(s_prev, np.array([1,1]), m, [0,0,1/3])
        self.assertListEqual(list(m.get_distribution(init, temperature=1)[:,1]), [1, 0, 0, 0])
        self.assertListEqual(list(m.get_distribution(s_prev, temperature=1)[:,1]), [1, 0, 0])
        self.assertListEqual(list(m.get_distribution(s, temperature=1)[:,1]), [.5, .5])

        # Fourth simulation
        m.simulate(init)
        s_prev = s
        s = gi.take_action(s_prev, np.array([[0,0],[1,0]])) # Takes first action since uniform
        self.assertIn(m.np_hash(s), m.tree) # Node added to tree
        self.assertEqual(len(m.tree), 4)
        self.assertExpanded(s, m)
        self.assertEdge(init, np.array([0,0]), m, [3,.5,.25])
        self.assertEdge(s_prev, np.array([1,0]), m, [1,.5,1/2])
        self.assertEdge(s_prev, np.array([1,1]), m, [0,0,1/2])
        self.assertListEqual(list(m.get_distribution(init, temperature=1)[:,1]), [1, 0, 0, 0])
        self.assertListEqual(list(m.get_distribution(s_prev, temperature=1)[:,1]), [1, 0])
        self.assertListEqual(list(m.get_distribution(s, temperature=1)[:,1]), [1])

        # Fifth simulation
        m.simulate(init)
        self.assertEqual(len(m.tree), 4) # Make sure it did not expand, terminal node.
        self.assertEdge(init, np.array([0,0]), m, [4,.625,.25])
        self.assertEdge(s_prev, np.array([1,0]), m, [2,.75,1/2])
        self.assertEdge(s_prev, np.array([1,1]), m, [0,0,1/2])
        self.assertListEqual(list(m.get_distribution(init, temperature=1)[:,1]), [1, 0, 0, 0])
        self.assertListEqual(list(m.get_distribution(s_prev, temperature=1)[:,1]), [1, 0])
        self.assertListEqual(list(m.get_distribution(s, temperature=1)[:,1]), [1])
        

        # Run alot. This test is here to ensure future changes don't brake this seemingly correct implementation.
        for _ in range(10000):
            m.simulate(init)
            
        # Since this is a one player game, there is no punishment for missing the guess on your first try.
        # That said, it does seem like the MCTS policy prefers the closer reward than the further one,
        # even without a punishment for taking longer to reach the goal.
        self.assertEdge(init, np.array([0,0]), m, [2384, 0.9991610738255033, 0.25])
        self.assertEdge(init, np.array([0,1]), m, [2488, 0.9995980707395499, 0.25])
        self.assertEdge(init, np.array([1,0]), m, [2540, 0.9998031496062992, 0.25])
        self.assertEdge(init, np.array([1,1]), m, [2592, 1.0, 0.25])
        self.assertListEqual(list(m.get_distribution(init, temperature=1)[:,1]), 
            [0.2383046781287485, 0.24870051979208316, 0.2538984406237505, 0.2590963614554178])



    # Test that our MCTS behaves as expected for a two-player game of guess-it
    def test_two_player_guess_it(self):
        gi = TwoPlayerGuessIt()
        b = NeuralNetwork(gi, BiasedNet)
        m = MCTS(gi, b)
        self.assertEqual(m.tree, {})
        init = gi.get_initial_state()

        # First simulation
        m.simulate(init) # Adds root and outward edges
        self.assertIn(m.np_hash(init), m.tree) # Root added to tree
        self.assertEqual(len(m.tree), 1)
        self.assertExpanded(init, m)
        self.assertListEqual(list(m.get_distribution(init, temperature=0)[:,1]), [1, 0, 0, 0])
        self.assertListEqual(list(m.get_distribution(init, temperature=1)[:,1]), [.25, .25, .25, .25])

        # Second simulation
        m.simulate(init)
        s = gi.take_action(init, np.array([[1,0],[0,0]])) # Takes first action since uniform
        self.assertIn(m.np_hash(s), m.tree) # Node added to tree
        self.assertEqual(len(m.tree), 2)
        self.assertExpanded(s, m)
        self.assertEdge(init, np.array([0,0]), m, [1,-.5,.25], heuristic=-.375)
        self.assertEdge(init, np.array([0,1]), m, [0,0,.25], heuristic=.25)
        self.assertListEqual(list(m.get_distribution(init, temperature=0)[:,1]), [1, 0, 0, 0])
        self.assertListEqual(list(m.get_distribution(init, temperature=1)[:,1]), [1, 0, 0, 0])
        self.assertListEqual(list(m.get_distribution(s, temperature=1)[:,1]), [1/3]*3)

        # Third simulation
        m.simulate(init)
        s = gi.take_action(init, np.array([[0,1],[0,0]])) # Now takes the second action
        self.assertIn(m.np_hash(s), m.tree) # Node added to tree
        self.assertEqual(len(m.tree), 3)
        self.assertExpanded(s, m)
        self.assertEdge(init, np.array([0,0]), m, [1,-.5,.25], heuristic=-0.32322330470336313)
        self.assertEdge(init, np.array([0,1]), m, [1,-.5,.25], heuristic=-0.32322330470336313)
        self.assertEdge(init, np.array([1,0]), m, [0,0,.25], heuristic=0.3535533905932738)
        self.assertListEqual(list(m.get_distribution(init, temperature=0)[:,1]), [1, 0, 0, 0])
        self.assertListEqual(list(m.get_distribution(init, temperature=1)[:,1]), [.5, .5, 0, 0])
        self.assertListEqual(list(m.get_distribution(s, temperature=1)[:,1]), [1/3]*3)

        # Fourth simulation
        m.simulate(init)
        s = gi.take_action(init, np.array([[0,0],[1,0]])) # Now takes the third action
        self.assertIn(m.np_hash(s), m.tree) # Node added to tree
        self.assertEqual(len(m.tree), 4)
        self.assertExpanded(s, m)
        self.assertEdge(init, np.array([0,0]), m, [1,-.5,.25], heuristic=-0.28349364905389035)
        self.assertEdge(init, np.array([0,1]), m, [1,-.5,.25], heuristic=-0.28349364905389035)
        self.assertEdge(init, np.array([1,0]), m, [1,-.5,.25], heuristic=-0.28349364905389035)
        self.assertEdge(init, np.array([1,1]), m, [0,0,.25], heuristic=0.4330127018922193)
        self.assertListEqual(list(m.get_distribution(init, temperature=0)[:,1]), [1, 0, 0, 0])
        self.assertListEqual(list(m.get_distribution(init, temperature=1)[:,1]), [1/3, 1/3, 1/3, 0])
        self.assertListEqual(list(m.get_distribution(s, temperature=1)[:,1]), [1/3]*3)

        # Fifth simulation
        m.simulate(init)
        s = gi.take_action(init, np.array([[0,0],[0,1]])) # Takes fourth action since uniform
        self.assertEqual(len(m.tree), 4)
        self.assertEdge(init, np.array([0,0]), m, [1,-.5,.25], heuristic=-.25)
        self.assertEdge(init, np.array([0,1]), m, [1,-.5,.25], heuristic=-.25)
        self.assertEdge(init, np.array([1,0]), m, [1,-.5,.25], heuristic=-.25)
        self.assertEdge(init, np.array([1,1]), m, [1,1,.25], heuristic=1.25)
        self.assertListEqual(list(m.get_distribution(init, temperature=0)[:,1]), [1, 0, 0, 0])
        self.assertListEqual(list(m.get_distribution(init, temperature=1)[:,1]), [.25]*4)

        # Run a few times until heuristic about to cross.
        for _ in range(145):
            m.simulate(init)
        self.assertEdge(init, np.array([0,0]), m, [1,-.5,.25], heuristic=1.0258194519667128)
        self.assertEdge(init, np.array([0,1]), m, [1,-.5,.25], heuristic=1.0258194519667128)
        self.assertEdge(init, np.array([1,0]), m, [1,-.5,.25], heuristic=1.0258194519667128)
        self.assertEdge(init, np.array([1,1]), m, [146,1,.25], heuristic=1.0207594483260778)
        self.assertListEqual(list(m.get_distribution(init, temperature=1)[:,1]), 
        [0.006711409395973154, 0.006711409395973154, 0.006711409395973154, 0.9798657718120806])
        self.assertListEqual(list(m.get_distribution(init, temperature=0)[:,1]), [0, 0, 0, 1])
        self.assertListEqual(list(m.get_distribution(init, temperature=.001)[:,1]), [0, 0, 0, 1])
        self.assertListEqual(list(m.get_distribution(init, temperature=.1)[:,1]),
            [2.2723302090432604e-22, 2.2723302090432604e-22, 2.2723302090432604e-22, 1.0])
        self.assertListEqual(list(m.get_distribution(init, temperature=.8)[:,1]),
        [0.001958841335585081, 0.001958841335585081, 0.001958841335585081, 0.9941234759932448])


        # Heuristic crosses over
        m.simulate(init)
        s_prev = gi.take_action(init, np.array([[1,0],[0,0]]))
        s = gi.take_action(s_prev, np.array([[0,1],[0,0]]))
        self.assertIn(m.np_hash(s), m.tree) # Node added to tree
        self.assertEqual(len(m.tree), 5)
        self.assertEdge(s_prev, np.array([0,1]), m, [1,-.5,1/3], heuristic=-0.33333333333333337)
        self.assertEdge(init, np.array([0,0]), m, [2, 0,.25], heuristic=1.0206207261596576)
        self.assertEdge(init, np.array([0,1]), m, [1,-.5,.25], heuristic=1.0309310892394863)
        self.assertEdge(init, np.array([1,0]), m, [1,-.5,.25], heuristic=1.0309310892394863)
        self.assertEdge(init, np.array([1,1]), m, [146,1,.25], heuristic=1.0208289944114215)

        # Run alot. This test is here to ensure future changes don't brake this seemingly correct implementation.
        for _ in range(10000):
            m.simulate(init)

        # We have learned that player 0's optimal strategy is to place the cross in the bottom right box
        self.assertEdge(init, np.array([0,0]), m,  [14, -0.75, 0.25], 0.9291201399674904)
        self.assertEdge(init, np.array([0,1]), m, [14, -0.75, 0.25], 0.9291201399674904)
        self.assertEdge(init, np.array([1,0]), m, [14, -0.75, 0.25], 0.9291201399674904)
        self.assertEdge(init, np.array([1,1]), m, [10108, 1.0, 0.25], 1.0024915226134645)

        # We have indirectly learn that player 1's optimal strategy, should player 0 fail on the first turn,
        # is the place the circle in the bottom right box
        self.assertEdge(s_prev, np.array([0,1]), m, [1, -0.5, 1/3], 0.10092521257733145)
        self.assertEdge(s_prev, np.array([1,0]), m, [1, -0.5, 1/3], 0.10092521257733145)
        self.assertEdge(s_prev, np.array([1,1]), m, [11, 1.0, 1/3], 1.1001542020962218)

        self.assertListEqual(list(m.get_distribution(init, temperature=1)[:,1]), 
        [0.001379310344827586, 0.001379310344827586, 0.001379310344827586, 0.9958620689655172])


class LeapFrogTest(MCTSTest):

    def test_three_player_linear_leap_frog(self):
        lf = ThreePlayerLinearLeapFrog()
        b = NeuralNetwork(lf, BiasedNet)
        m = MCTS(lf, b)
        self.assertEqual(m.tree, {})
        init = lf.get_initial_state()

        # First simulation
        m.simulate(init) # Adds root and outward edges
        self.assertIn(m.np_hash(init), m.tree) # Root added to tree
        self.assertEqual(len(m.tree), 1)
        self.assertExpanded(init, m)

        # Second simulation
        m.simulate(init)
        s1 = lf.take_action(init, np.array([1])) # Takes first action since uniform
        self.assertIn(m.np_hash(s1), m.tree) # Node added to tree
        self.assertEqual(len(m.tree), 2)
        self.assertExpanded(s1, m)
        self.assertEdge(init, np.array([0]), m, [1,-.5,1], heuristic=0)
        self.assertEdge(s1, np.array([0]), m, [0,0,1], heuristic=0)

        # Third simulation
        m.simulate(init)
        s2 = lf.take_action(s1, np.array([1])) # Takes first action since uniform
        self.assertIn(m.np_hash(s2), m.tree) # Node added to tree
        self.assertEqual(len(m.tree), 3)
        self.assertExpanded(s2, m)
        self.assertEdge(init, np.array([0]), m, [2,-.5,1], heuristic=-0.028595479208968266)
        self.assertEdge(s1, np.array([0]), m, [1,-.5,1], heuristic=0)
        self.assertEdge(s2, np.array([0]), m, [0,0,1], heuristic=0)

        # Fourth simulation
        m.simulate(init)
        s3 = lf.take_action(s2, np.array([1])) # Takes first action since uniform
        self.assertIn(m.np_hash(s3), m.tree) # Node added to tree
        self.assertEqual(len(m.tree), 4)
        self.assertExpanded(s3, m)
        self.assertEdge(init, np.array([0]), m, [3,-1/6,1], heuristic=0.26634603522555267)
        self.assertEdge(s1, np.array([0]), m, [2,-.5,1], heuristic=-0.028595479208968266)
        self.assertEdge(s2, np.array([0]), m, [1,-.5,1], heuristic=0)
        self.assertEdge(s3, np.array([0]), m, [0,0,1], heuristic=0)

        # Fifth simulation
        m.simulate(init)
        s4 = lf.take_action(s3, np.array([1])) # Takes first action since uniform
        self.assertIn(m.np_hash(s4), m.tree) # Node added to tree
        self.assertEqual(len(m.tree), 5)
        self.assertExpanded(s4, m)
        self.assertEdge(init, np.array([0]), m, [4,-.25,1], heuristic=0.15000000000000002)
        self.assertEdge(s1, np.array([0]), m, [3,-1/6,1], heuristic=0.26634603522555267)
        self.assertEdge(s2, np.array([0]), m, [2,-.5,1], heuristic=-0.028595479208968266)
        self.assertEdge(s3, np.array([0]), m, [1,-.5,1], heuristic=0)
        self.assertEdge(s4, np.array([0]), m, [0,0,1], heuristic=0)

        # Sixth simulation - terminal state
        m.simulate(init)
        self.assertEqual(len(m.tree), 5)
        self.assertEdge(init, np.array([0]), m, [5,-.4,1], heuristic=-0.027322003750035073)
        self.assertEdge(s1, np.array([0]), m, [4,.125,1], heuristic=0.525)
        self.assertEdge(s2, np.array([0]), m, [3,-2/3,1], heuristic=-0.23365396477444733)
        self.assertEdge(s3, np.array([0]), m, [2,-.75,1], heuristic=-0.27859547920896827)
        self.assertEdge(s4, np.array([0]), m, [1,1,1], heuristic=1.5)

        # Simulate from end of chain
        m.simulate(s4)
        self.assertEqual(len(m.tree), 5)
        self.assertEdge(init, np.array([0]), m, [5,-.4,1], heuristic=-0.027322003750035073)
        self.assertEdge(s1, np.array([0]), m, [4,.125,1], heuristic=0.525)
        self.assertEdge(s2, np.array([0]), m, [3,-2/3,1], heuristic=-0.23365396477444733)
        self.assertEdge(s3, np.array([0]), m, [2,-.75,1], heuristic=-0.27859547920896827)
        self.assertEdge(s4, np.array([0]), m, [2,1,1], heuristic=1.4714045207910318)

        # Simulate from middle of chain
        m.simulate(s3)
        self.assertEqual(len(m.tree), 5)
        self.assertEdge(init, np.array([0]), m, [5,-.4,1], heuristic=-0.027322003750035073)
        self.assertEdge(s1, np.array([0]), m, [4,.125,1], heuristic=0.525)
        self.assertEdge(s2, np.array([0]), m, [3,-2/3,1], heuristic=-0.23365396477444733)
        self.assertEdge(s3, np.array([0]), m, [3,-5/6,1], heuristic=-0.40032063144111407)
        self.assertEdge(s4, np.array([0]), m, [3,1,1], heuristic=1.4330127018922192)


    def test_three_player_leap_frog(self):
        lf = ThreePlayerLeapFrog()
        b = NeuralNetwork(lf, BiasedNet)
        m = MCTS(lf, b)
        self.assertEqual(m.tree, {})
        init = lf.get_initial_state()

        # First simulation
        m.simulate(init) # Adds root and outward edges
        self.assertIn(m.np_hash(init), m.tree) # Root added to tree
        self.assertEqual(len(m.tree), 1)
        self.assertExpanded(init, m)

        # Second simulation
        m.simulate(init)
        s = lf.take_action(init, np.array([1,0,0])) # Takes first action since uniform
        self.assertIn(m.np_hash(s), m.tree) # Node added to tree
        self.assertEqual(len(m.tree), 2)
        self.assertExpanded(s, m)
        self.assertEdge(init, np.array([0]), m, [1,-.5,1/3], heuristic=-0.33333333333333337)
        self.assertEdge(init, np.array([1]), m, [0,0,1/3], heuristic=1/3)

        # Third simulation
        m.simulate(init)
        s = lf.take_action(init, np.array([0,1,0])) # Takes first action since uniform
        self.assertIn(m.np_hash(s), m.tree) # Node added to tree
        self.assertEqual(len(m.tree), 3)
        self.assertExpanded(s, m)
        self.assertEdge(init, np.array([0]), m, [1,-.5,1/3], heuristic=-0.26429773960448416)
        self.assertEdge(init, np.array([1]), m, [1,-.5,1/3], heuristic=-0.26429773960448416)
        self.assertEdge(init, np.array([2]), m, [0,0,1/3], heuristic=0.4714045207910317)

        # Fourth simulation
        m.simulate(init)
        s = lf.take_action(init, np.array([0,0,1])) # Takes first action since uniform
        self.assertIn(m.np_hash(s), m.tree) # Node added to tree
        self.assertEqual(len(m.tree), 4)
        self.assertExpanded(s, m)
        self.assertEdge(init, np.array([0]), m, [1,-.5,1/3], heuristic=-0.21132486540518713)
        self.assertEdge(init, np.array([1]), m, [1,-.5,1/3], heuristic=-0.21132486540518713)
        self.assertEdge(init, np.array([2]), m, [1,-.5,1/3], heuristic=-0.21132486540518713)

        # Fifth simulation
        m.simulate(init)
        s_prev = lf.take_action(init, np.array([1,0,0]))
        s = lf.take_action(s_prev, np.array([1,0,0])) # Takes first action since uniform
        self.assertIn(m.np_hash(s), m.tree) # Node added to tree
        self.assertEqual(len(m.tree), 5)
        self.assertExpanded(s, m)
        self.assertEdge(s_prev, np.array([0]), m, [1,-.5,1/3], heuristic=-0.33333333333333337)
        self.assertEdge(init, np.array([0]), m, [2,-.5,1/3], heuristic=-0.2777777777777778)

        # Sixth simulation
        m.simulate(init)
        s_prev = lf.take_action(init, np.array([0,1,0]))
        s = lf.take_action(s_prev, np.array([1,0,0])) # Takes first action since uniform
        self.assertIn(m.np_hash(s), m.tree) # Node added to tree
        self.assertEqual(len(m.tree), 6)
        self.assertExpanded(s, m)
        self.assertEdge(s_prev, np.array([0]), m, [1,-.5,1/3], heuristic=-0.33333333333333337)
        self.assertEdge(init, np.array([0]), m, [2,-.5,1/3], heuristic=-0.2515480025000234)
        self.assertEdge(init, np.array([1]), m, [2,-.5,1/3], heuristic=-0.2515480025000234)

        # Seventh simulation
        m.simulate(init)
        s_prev = lf.take_action(init, np.array([0,0,1]))
        s = lf.take_action(s_prev, np.array([1,0,0])) # Takes first action since uniform
        self.assertIn(m.np_hash(s), m.tree) # Node added to tree
        self.assertEqual(len(m.tree), 7)
        self.assertExpanded(s, m)
        self.assertEdge(s_prev, np.array([0]), m, [1,-.5,1/3], heuristic=-0.33333333333333337)
        self.assertEdge(init, np.array([0]), m, [2,-.5,1/3], heuristic=-0.22783447302409138)
        self.assertEdge(init, np.array([1]), m, [2,-.5,1/3], heuristic=-0.22783447302409138)
        self.assertEdge(init, np.array([2]), m, [2,-.5,1/3], heuristic=-0.22783447302409138)

        # Eigth simulation - Q value should now be positive.
        m.simulate(init)
        s_prev = lf.take_action(init, np.array([1,0,0]))
        s_prev = lf.take_action(s_prev, np.array([0,1,0]))
        s = lf.take_action(s_prev, np.array([1,0,0]))
        self.assertIn(m.np_hash(s), m.tree) # Node added to tree
        self.assertEqual(len(m.tree), 8)
        self.assertExpanded(s, m)
        self.assertEdge(init, np.array([0]), m, [3,-1/6,1/3], heuristic=0.05381260925538256)

        # Something new: simulate starting from a node other than the root.
        # We should receive -.5 during propagtion because we switched perspectives.
        self.assertEdge(s_prev, np.array([0]), m, [1,-.5,1/3], heuristic=-0.33333333333333337)
        m.simulate(s_prev) # We are now player 3.
        self.assertEdge(s_prev, np.array([1]), m, [1,-.5,1/3], heuristic=-0.26429773960448416)

        # Run alot. This test is here to ensure future changes don't brake this seemingly correct implementation.
        for _ in range(1000):
            m.simulate(init)

        # We have learned that player 0's optimal strategy is to take a step of size 3
        self.assertEdge(init, np.array([0]), m, [28, -0.26785714285714285, 0.3333333333333333], 0.09689301007670609)
        self.assertEdge(init, np.array([1]), m, [60, -0.05000000000000002, 0.3333333333333333], 0.12340581041117407)
        self.assertEdge(init, np.array([2]), m, [919, 0.12459194776931437, 0.3333333333333333], 0.13608950693788135)

        





if __name__ == '__main__':
    unittest.main()