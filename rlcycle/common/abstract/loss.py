from abc import ABC, abstractmethod
from typing import Tuple

import numpy as np
from omegaconf import DictConfig
import torch
import torch.nn as nn


class Loss(ABC):
    """Abstract class for callable loss functions

    Attributes:
        hyper_params (DictConfig): algorithm hyperparameters
        device (torch.device): map location for tensor computation

    """

    def __init__(self, hyper_params: DictConfig, device: str):
        self.hyper_params = hyper_params
        self.device = torch.device(device)

    @abstractmethod
    def __call__(
        self, networks: Tuple[nn.Module, ...], data: Tuple[np.ndarray, ...],
    ) -> Tuple[torch.Tensor, ...]:
        pass
