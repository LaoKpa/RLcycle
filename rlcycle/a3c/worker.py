from typing import Dict, List, Tuple

import torch
from omegaconf import DictConfig
from rlcycle.a2c.worker import TrajectoryRolloutWorker
from rlcycle.build import build_loss, build_model


class ComputesGradients:
    """TrajectorRolloutWorker wrapper for gradient parallelization

    Attributes:
        worker (TrajectoryRolloutWorker): worker that is wrapped
        hyper_params (DictConfig): algorithm hyperparameters
        critic (BaseModel): critic network
        critic_loss_fn (Loss): critic (value) loss function
        actor_loss_fn (Loss): actor (policy) loss function

    """

    def __init__(
        self,
        worker: TrajectoryRolloutWorker,
        hyper_params: DictConfig,
        model_cfg: DictConfig,
    ):
        self.worker = worker
        self.hyper_params = hyper_params

        # Build critic
        self.critic = build_model(self.model_cfg.critic)

        # Build loss functions
        self.critic_loss_fn = build_loss(
            self.worker.experiment_info.critic_loss,
            self.hyper_params,
            self.worker.experiment_info.device,
        )

        self.actor_loss_fn = build_loss(
            self.worker.experiment_info.actor_loss,
            self.hyper_params,
            self.worker.experiment_info.device,
        )

    def compute_grads_with_traj(self) -> Tuple[List[torch.Tensor], ...]:
        trajectory = self.worker.run_trajectory()
        trajectory_tensors = self._preprocess_experience(trajectory)

        # Compute loss
        critic_loss_element_wise = self.critic_loss_fn(
            (self.critic, self.worker.actor), trajectory_tensors,
        )
        critic_loss = critic_loss_element_wise.mean()

        actor_loss_element_wise = self.actor_loss_fn(
            (self.critic, self.worker.actor), trajectory_tensors,
        )
        actor_loss = actor_loss_element_wise.mean()

        # Compute (retrieve) gradients
        self.critic.zero_grad()
        critic_loss.backward()
        critic_grads = []
        for param in self.critic.parameters():
            critic_grads.append(param.grad)

        self.worker.actor.zero_grad()
        actor_loss.backward()
        actor_grads = []
        for param in self.worker.actor.parameters():
            actor_grads.append(param.grad)

        return critic_grads, actor_grads

    def synchronize(self, state_dicts: Dict[str, dict]):
        self.critic.load_state_dict(state_dicts["critic"])
        self.worker.synchronize_policy(state_dicts["actor"])