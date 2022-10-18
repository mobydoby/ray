import logging
from typing import Dict, Any, Optional
from ray.rllib.offline.estimators.off_policy_estimator import OffPolicyEstimator
from ray.rllib.offline.estimators.fqe_torch_model import FQETorchModel
from ray.rllib.policy import Policy
from ray.rllib.utils.annotations import DeveloperAPI, override
from ray.rllib.utils.typing import SampleBatchType
from ray.rllib.utils.numpy import convert_to_numpy
import numpy as np

logger = logging.getLogger()


@DeveloperAPI
class DirectMethod(OffPolicyEstimator):
    """The Direct Method estimator.

    Let s_t, a_t, and r_t be the state, action, and reward at timestep t.

    This method trains a Q-model for the evaluation policy \pi_e on behavior
    data generated by \pi_b. Currently, RLlib implements this using
    Fitted-Q Evaluation (FQE). You can also implement your own model
    and pass it in as `q_model_config = {"type": your_model_class, **your_kwargs}`.

    This estimator computes the expected return for \pi_e for an episode as:
    V^{\pi_e}(s_0) = \sum_{a \in A} \pi_e(a | s_0) Q(s_0, a)
    and returns the mean and standard deviation over episodes.

    For more information refer to https://arxiv.org/pdf/1911.06854.pdf"""

    @override(OffPolicyEstimator)
    def __init__(
        self,
        policy: Policy,
        gamma: float,
        q_model_config: Optional[Dict] = None,
    ):
        """Initializes a Direct Method OPE Estimator.

        Args:
            policy: Policy to evaluate.
            gamma: Discount factor of the environment.
            q_model_config: Arguments to specify the Q-model. Must specify
            a `type` key pointing to the Q-model class.
            This Q-model is trained in the train() method and is used
            to compute the state-value estimates for the DirectMethod estimator.
            It must implement `train` and `estimate_v`.
            TODO (Rohan138): Unify this with RLModule API.
        """

        super().__init__(policy, gamma)

        q_model_config = q_model_config or {}
        model_cls = q_model_config.pop("type", FQETorchModel)
        self.model = model_cls(
            policy=policy,
            gamma=gamma,
            **q_model_config,
        )
        assert hasattr(
            self.model, "estimate_v"
        ), "self.model must implement `estimate_v`!"

    @override(OffPolicyEstimator)
    def estimate(self, batch: SampleBatchType) -> Dict[str, Any]:
        """Compute off-policy estimates.

        Args:
            batch: The SampleBatch to run off-policy estimation on

        Returns:
            A dict consists of the following metrics:
            - v_behavior: The discounted return averaged over episodes in the batch
            - v_behavior_std: The standard deviation corresponding to v_behavior
            - v_target: The estimated discounted return for `self.policy`,
            averaged over episodes in the batch
            - v_target_std: The standard deviation corresponding to v_target
            - v_gain: v_target / max(v_behavior, 1e-8)
            - v_delta: The difference between v_target and v_behavior.
        """
        batch = self.convert_ma_batch_to_sample_batch(batch)
        self.check_action_prob_in_batch(batch)
        estimates_per_epsiode = {"v_behavior": [], "v_target": []}
        # Calculate Direct Method OPE estimates
        for episode in batch.split_by_episode():
            rewards = episode["rewards"]
            v_behavior = 0.0
            v_target = 0.0
            for t in range(episode.count):
                v_behavior += rewards[t] * self.gamma ** t

            init_step = episode[0:1]
            v_target = self.model.estimate_v(init_step)
            v_target = convert_to_numpy(v_target).item()

            estimates_per_epsiode["v_behavior"].append(v_behavior)
            estimates_per_epsiode["v_target"].append(v_target)

        estimates = {
            "v_behavior": np.mean(estimates_per_epsiode["v_behavior"]),
            "v_behavior_std": np.std(estimates_per_epsiode["v_behavior"]),
            "v_target": np.mean(estimates_per_epsiode["v_target"]),
            "v_target_std": np.std(estimates_per_epsiode["v_target"]),
        }
        estimates["v_gain"] = estimates["v_target"] / max(estimates["v_behavior"], 1e-8)
        estimates["v_delta"] = estimates["v_target"] - estimates["v_behavior"]

        return estimates

    @override(OffPolicyEstimator)
    def train(self, batch: SampleBatchType) -> Dict[str, Any]:
        """Trains self.model on the given batch.

        Args:
            batch: A SampleBatchType to train on

        Returns:
            A dict with key "loss" and value as the mean training loss.
        """
        batch = self.convert_ma_batch_to_sample_batch(batch)
        losses = self.model.train(batch)
        return {"loss": np.mean(losses)}
