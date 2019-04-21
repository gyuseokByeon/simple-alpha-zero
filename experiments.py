

import os
import matplotlib.pyplot as plt
import numpy as np
from models.smallvgg import SmallVGG
from models.minivgg import MiniVGG
from models.mlp import MLP
from models.senet import SENet
from neural_network import NeuralNetwork
from games.connect4 import Connect4
from games.tictactoe import TicTacToe
from games.tictacmo import TicTacMo
from games.leapfrog import ThreePlayerLeapFrog
from players.deep_mcts_player import DeepMCTSPlayer
from players.uninformed_mcts_player import UninformedMCTSPlayer
from play import play_match


# Evaluate the outcome of playing a checkpoint against an uninformed MCTS agent
def evaluate_against_uninformed(checkpoint, game, model_class, my_sims, opponent_sims, cuda=False):
    my_model = NeuralNetwork(game, model_class, cuda=cuda)
    my_model.load(checkpoint)
    num_opponents = game.get_num_players() - 1
    uninformeds = [UninformedMCTSPlayer(game, opponent_sims) for _ in range(num_opponents)]
    informed = DeepMCTSPlayer(game, my_model, my_sims)
    scores = play_match(game, [informed] + uninformeds, permute=True)
    print("Opponent strength: {}     Scores: {}".format(opponent_sims, scores))


# Tracks the current best checkpoint across all checkpoints
def rank_checkpoints(game, model_class, sims, cuda=False):
    winning_model = NeuralNetwork(game, model_class, cuda=cuda)
    contending_model = NeuralNetwork(game, model_class, cuda=cuda)
    ckpts = winning_model.list_checkpoints()
    num_opponents = game.get_num_players() - 1
    current_winner = ckpts[0]

    for contender in ckpts:

        # Load contending player
        contending_model.load(contender)
        contending_player = DeepMCTSPlayer(game, contending_model, sims)

        # Load winning player
        winning_model.load(current_winner)
        winners = [DeepMCTSPlayer(game, winning_model, sims) for _ in range(num_opponents)]
        
        scores = play_match(game, [contending_player] + winners, verbose=False, permute=True)
        print("Current Champ: {}    Challenger: {}    <{}>    "
                .format(current_winner, contender, scores), end= "")
        if scores[0] >= scores.max():
            current_winner = contender
        print("New Champ: {}".format(current_winner))


# Plays the given checkpoint against all other checkpoints and logs upsets.
def one_vs_all(checkpoint, game, model_class, sims, cuda=False):
    my_model = NeuralNetwork(game, model_class, cuda=cuda)
    my_model.load(checkpoint)
    contending_model = NeuralNetwork(game, model_class, cuda=cuda)
    ckpts = my_model.list_checkpoints()
    num_opponents = game.get_num_players() - 1

    for contender in ckpts:
        contending_model.load(contender)
        my_player = DeepMCTSPlayer(game, my_model, sims)
        contenders = [DeepMCTSPlayer(game, contending_model, sims) for _ in range(num_opponents)]
        scores = play_match(game, [my_player] + contenders, verbose=False, permute=True)
        print("Challenger:", contender, "Outcome:", scores, "My score:", scores[0])
        if scores.max() != scores[0]:
                print("UPSET!")


# Finds the effective MCTS strength of a checkpoint
# Also presents a control at each checkpoint - that is, the result
# if you had used no heuristic but the same num_simulations.
def effective_model_power(checkpoint, game, model_class, sims, cuda=False):
    my_model = NeuralNetwork(game, model_class, cuda=cuda)
    my_model.load(checkpoint)
    my_player = DeepMCTSPlayer(game, my_model, sims)
    strength = 10
    num_opponents = game.get_num_players() - 1
    lost = False

    while not lost: 
        contenders = [UninformedMCTSPlayer(game, strength) for _ in range(num_opponents)]

        # Play main game
        scores = play_match(game, [my_player] + contenders, verbose=False, permute=True)
        if scores[0] != scores.max(): lost = True
        print("{} <{}>      Opponent strength: {}".format(scores, round(scores[0]), strength), end="")

        # Play control game
        control_player = UninformedMCTSPlayer(game, sims)
        scores = play_match(game, [control_player] + contenders, verbose=False, permute=True)
        print("      (Control: {} <{}>)".format(scores, round(scores[0], 3)))

        strength *= 2 # Opponent strength doubles every turn


# Plot training error against checkpoints.
def plot_train_loss(game, model_classes, cudas):
    fig, ax = plt.subplots()
    min_len = None
    for cuda, model_class in zip(cudas, model_classes):
        nn = NeuralNetwork(game, model_class, cuda=cuda)
        ckpt = nn.list_checkpoints()[-1]
        _, error = nn.load(ckpt, load_supplementary_data=True)
        window = 1
        error = np.convolve(error, np.ones(window), mode="valid")/window
        min_len = len(error) if min_len is None else min(min_len, len(error))
        plt.plot(error, label=model_class.__name__)

    plt.title("Training loss for {}".format(game.__class__.__name__))
    ax.set_xlim(left=0, right=min_len)
    ax.set_ylabel("Error")
    ax.set_xlabel("Iteration")
    plt.legend()
    plt.show()






if __name__ == "__main__":
    checkpoint = 102
    game = TicTacMo()
    model_class = SENet
    sims = 50
    cuda = True
    
    print("*** Rank Checkpoints ***")
    rank_checkpoints(game, model_class, sims, cuda)
    print("*** One vs All ***")
    one_vs_all(checkpoint, game, model_class, sims, cuda)
    print("*** Effective Model Power ***")
    effective_model_power(checkpoint, game, model_class, sims, cuda)
    print("*** Train Loss Plot ***")
    plot_train_loss(game, [model_class], [cuda])


    '''
    x = [10,20,40,80,160,320,640,1280,2560,5120,10240,20480]
    control = [1., .5, .5, .25, .25, .25, .25, .25, .25, .25, .5, .5]
    senet = [1., .75, .75, .75, .75, .75, .75, .5, .5, .5, .5, .5]
    mini = [1., .75, .75, .75, .75, .75, .75, .5, .5, .5, .5, .5]
    mlp = [1., .5, .5, .5, .5, .5, .5, .5, .5, .5, .5, .5]
    print("control", sum(control)/len(control))
    print("senet", sum(senet)/len(senet))
    print("mini", sum(mini)/len(mini))
    print("mlp", sum(mlp)/len(mlp))

    f, ax = plt.subplots()
    plt.plot(x, control, color="black", label="Vanilla (Control)", linewidth=4)
    plt.plot(x,senet, label="SENet", linewidth=4)
    plt.plot(x,mini, linestyle="--", label="MiniVGG", linewidth=4)
    plt.plot(x,mlp, linestyle=":", label="MLP", linewidth=4)
    plt.ylabel("AlphaZero Win Rate")
    plt.xscale("log")
    plt.xlabel("Opponent Vanilla MCTS Iterations per Turn (Opponent Strength)")
    plt.legend()
    ax.set_ylim(ymin=0)
    plt.title("TicTacToe - AlphaZero vs Vanilla MCTS Opponents")
    plt.show()

    '''

    '''
    x = [10,20,40,80,160,320,640,1280,2560,5120,10240,20480]
    control = [1.0, .75, .25, 1.0, .25, 0, .25, 0, 0, 0, 0, 0]
    senet = [1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,0,.75, .5, 0]
    small = [1.0,1.0,1.0,1.0,1.0,1.0,1.0,.5,0,0,.5,1]
    mlp = [1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,.25,.5,0,.5]

    print("control", sum(control)/len(control))
    print("senet", sum(senet)/len(senet))
    print("small", sum(small)/len(small))
    print("mlp", sum(mlp)/len(mlp))
    f, ax = plt.subplots()
    plt.plot(x, control, color="black", label="Vanilla (Control)", linewidth=4)
    plt.plot(x,senet, label="SENet", linewidth=4)
    plt.plot(x,small, linestyle="--", label="SmallVGG", linewidth=4)
    plt.plot(x,mlp, linestyle=":", label="MLP", linewidth=4)
    plt.ylabel("AlphaZero Win Rate")
    plt.xscale("log")
    plt.xlabel("Opponent Vanilla MCTS Iterations per Turn (Opponent Strength)")
    plt.legend()
    ax.set_ylim(ymin=0)
    plt.title("Connect4 - AlphaZero vs Vanilla MCTS Opponents")
    plt.show()
    '''
