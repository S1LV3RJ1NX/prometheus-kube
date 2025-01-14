import os, gym, copy
import numpy as np
import torch as th
from collections import defaultdict, deque

import gym_packing
from sb3_contrib.common.wrappers import ActionMasker
from sb3_contrib.ppo_mask import MaskablePPO

PATH = "packing_api/models/best_model.zip"


def get_capacity_and_max():
    """WRITE CUSTOM CODE HERE THAT GIVES YOU CAPACITY OF ALL VMS and MAX ACROSS EACH DIMENSION"""
    cap = np.array([
        [7,13,42,89],
        [7,13,42,89],
        [6,13,55,8998],
    ])
    max_vals = cap.max(axis=0)

    return cap, max_vals

def mask_fn(env: gym.Env) -> np.ndarray:
        # Use this function to return the action masks
        return env.valid_action_mask()

env = gym.make('vm-packing-v0',)
env = ActionMasker(env, mask_fn)  # Wrap to enable masking
path = PATH
model = MaskablePPO.load(path, env=env)

class prettyDict(defaultdict):
    def __init__(self, *args, **kwargs):
        defaultdict.__init__(self,*args,**kwargs)

    def __repr__(self):
        return str(dict(self))

def group_containers(a):
    x = np.split(a, np.unique(a[:, 1], return_index=True)[1])[::-1][0]
    x = x.astype(int)
    return x

def normalize_data(self, data, max_vals, type='machines'):

    if type == 'machines':
        machines = data[0].astype(int)
        machines_cap = data[1].astype(int)
        mask = np.any(machines != machines_cap, 1)

        machines_norm = machines[:,1:] / max_vals
        machines_norm = np.c_[mask.reshape(-1,1), machines_norm]
        return machines_norm

    elif type == 'containers':
        data = data / max_vals
        data = np.c_[np.zeros(np.size(data, 0)), data]
        return data

def rl_pack(machines, mid_list, containers, cid_list):
    
    cap, max_vals = get_capacity_and_max()
    demands = normalize_data(containers, type='containers')
    action_dict = {}

    for idx, container in enumerate(containers):
        cnt_idx = container[0].astype(int)
        
        machines_avail = normalize_data([machines, cap], max_vals, type='machines')
        request_norm = demands[idx]
        
        obs = np.vstack(
            [
                machines_avail, # pm_on/off, cpu, mem, disk, net
                request_norm.reshape(1,-1), # dummy, cpu, mem, disk, net
            ]
        ).astype(np.float32)
        
        env.set_obs(obs, cnt_idx)
        action_masks = mask_fn(env)

        # Predicitons: action and next hidden state to be used in recurrent policies
        m_idx, _next_hidden_state = model.predict(obs, action_masks=action_masks)
        m_idx = int(m_idx)
        if np.sum(machines[m_idx] >= container) == 4:
            machines[m_idx] -= container
            m_id = mid_list[m_idx]
            c_id = cid_list[idx]
            action_dict[c_id] = m_id 

    
    return action_dict
        





