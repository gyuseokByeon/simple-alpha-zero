import sys
import torch
import torch.nn.functional as F
import numpy as np
sys.path.append("..")
from model import Model


class MiniVGG(Model):

  def __init__(self, input_shape, p_shape, v_shape):
    super(MiniVGG, self).__init__(input_shape, p_shape, v_shape)
    num_hidden_units = 128
    self.input_shape = input_shape
    self.conv1 = torch.nn.Conv2d(input_shape[-1], 64, 2)
    self.conv2 = torch.nn.Conv2d(64, 128, 2)
    self.p_head = torch.nn.Linear(num_hidden_units, np.prod(p_shape))
    self.v_head = torch.nn.Linear(num_hidden_units, np.prod(v_shape))

  def forward(self, x):
    batch_size = len(x)
    this_p_shape = tuple([batch_size] + list(self.p_shape))
    this_v_shape = tuple([batch_size] + list(self.v_shape))
    x = x.permute(0,3,1,2) # NHWC -> NCHW

    # Network
    relu_conv1 = F.relu(self.conv1(x))
    relu_conv2 = F.relu(self.conv2(relu_conv1))
    flat = relu_conv2.view(batch_size, -1)

    # Outputs
    p_logits = self.p_head(flat).view(this_p_shape)
    v = torch.tanh(self.v_head(flat).view(this_v_shape))

    return p_logits, v
