"""Portable reference checks for the station's power and decision rules.

Gameplay uses the Blueprint graphs authored by Install_StationNetwork.py and
Install_OmegaDiagnostics.py. These independent checks document their rules.
"""
from itertools import product
import json


def power_assignments(reserve_on):
    capacity = (6, 4 if reserve_on else 0)
    feasible = []
    for assignment in product((0, 1), repeat=3):
        radio, light, pump = assignment
        loads = [sum(demand for demand, source in zip((3, 2, 4), assignment)
                     if source == circuit) for circuit in (0, 1)]
        if radio != pump and all(load <= limit for load, limit in zip(loads, capacity)):
            feasible.append(assignment)
    return feasible


def omega_action(power, antenna, cable, requested):
    if not power:
        return 'wait_power'
    if not (antenna or cable):
        return 'wait_channel'
    if requested:
        return 'transmit'
    return 'ready'


def main():
    assert power_assignments(False) == []
    plans = power_assignments(True)
    assert plans and plans[0] == (0, 0, 1)
    expected = [
        ((False, False, False, True), 'wait_power'),
        ((True, False, False, True), 'wait_channel'),
        ((True, True, False, False), 'ready'),
        ((True, True, False, True), 'transmit'),
        ((True, False, True, True), 'transmit'),
        ((True, True, True, True), 'transmit'),
        ((False, True, True, True), 'wait_power'),
    ]
    for inputs, action in expected:
        assert omega_action(*inputs) == action
    print(json.dumps({'passed': True, 'reference_only': True,
                      'feasible_power_assignments': plans,
                      'agent_scenarios': len(expected)}, indent=2))


if __name__ == '__main__':
    main()
