import pytest
from pytest import raises

from awesome_tool.statemachine.states.execution_state import ExecutionState
from awesome_tool.statemachine.states.preemptive_concurrency_state import PreemptiveConcurrencyState
import awesome_tool.statemachine.singleton
from awesome_tool.statemachine.storage.storage import StateMachineStorage
from awesome_tool.statemachine.state_machine import StateMachine
import variables_for_pytest


def create_preemption_statemachine():
    state1 = ExecutionState("FirstState", path="../test_scripts", filename="concurrence_preemption1.py")
    state1.add_outcome("FirstOutcome", 3)
    input_state1 = state1.add_input_data_port("input_data_port1", "float")

    state2 = ExecutionState("SecondState", path="../test_scripts", filename="concurrence_preemption2.py")
    state2.add_outcome("FirstOutcome", 3)
    input_state2 = state2.add_input_data_port("input_data_port1", "float")

    state3 = PreemptiveConcurrencyState("FirstConcurrencyState", path="../test_scripts",
                                        filename="concurrency_container.py")
    state3.add_state(state1)
    state3.add_state(state2)
    state3.add_outcome("State1 preempted", 3)
    input_state3 = state3.add_input_data_port("input_data_port1", "float", 3.0)
    input2_state3 = state3.add_input_data_port("input_data_port2", "float", 3.0)
    state3.add_data_flow(state3.state_id, input_state3, state1.state_id, input_state1)
    state3.add_data_flow(state3.state_id, input2_state3, state2.state_id, input_state2)
    state3.add_transition(state1.state_id, 3, None, 3)

    return StateMachine(state3)


def test_concurrency_preemption_state_execution():

    preemption_state_sm = create_preemption_statemachine()

    input_data = {"input_data_port1": 0.1, "input_data_port2": 0.1}
    preemption_state_sm.root_state.input_data = input_data
    preemption_state_sm.root_state.output_data = {}

    variables_for_pytest.test_multithrading_lock.acquire()
    awesome_tool.statemachine.singleton.state_machine_manager.add_state_machine(preemption_state_sm)
    awesome_tool.statemachine.singleton.state_machine_manager.active_state_machine_id = preemption_state_sm.state_machine_id
    awesome_tool.statemachine.singleton.state_machine_execution_engine.start()
    preemption_state_sm.root_state.join()
    awesome_tool.statemachine.singleton.state_machine_execution_engine.stop()

    assert awesome_tool.statemachine.singleton.global_variable_manager.get_variable("preempted_state2_code") == "DF3LFXD34G"
    variables_for_pytest.test_multithrading_lock.release()


def test_concurrency_preemption_save_load():
    s = StateMachineStorage("../test_scripts/stored_statemachine")

    preemption_state_sm = create_preemption_statemachine()

    s.save_statemachine_as_yaml(preemption_state_sm, "../test_scripts/stored_statemachine")
    [root_state, version, creation_time] = s.load_statemachine_from_yaml()

    input_data = {"input_data_port1": 0.1, "input_data_port2": 0.1}
    output_data = {}
    preemption_state_sm.root_state.input_data = input_data
    preemption_state_sm.root_state.output_data = output_data

    variables_for_pytest.test_multithrading_lock.acquire()
    awesome_tool.statemachine.singleton.state_machine_manager.add_state_machine(preemption_state_sm)
    awesome_tool.statemachine.singleton.state_machine_manager.active_state_machine_id = preemption_state_sm.state_machine_id
    awesome_tool.statemachine.singleton.state_machine_execution_engine.start()
    preemption_state_sm.root_state.join()
    awesome_tool.statemachine.singleton.state_machine_execution_engine.stop()

    assert awesome_tool.statemachine.singleton.global_variable_manager.get_variable("preempted_state2_code") == "DF3LFXD34G"
    variables_for_pytest.test_multithrading_lock.release()

if __name__ == '__main__':
    #pytest.main()
    test_concurrency_preemption_state_execution()
    test_concurrency_preemption_save_load()