from CybORG import CybORG
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from CybORG.Agents import SleepAgent, EnterpriseGreenAgent, FiniteStateRedAgent
from CybORG.Simulator.Actions import Sleep, Remove, Restore, Analyse, DeployDecoy
from CybORG.Simulator.Actions.ConcreteActions.ControlTraffic import AllowTrafficZone, BlockTrafficZone
import openai

openai.api_key = "OPENAI_API_KEY"

steps = 100
sg = EnterpriseScenarioGenerator(blue_agent_class=SleepAgent,
                                  green_agent_class=EnterpriseGreenAgent,
                                  red_agent_class=FiniteStateRedAgent,
                                  steps=steps)
cyborg = CybORG(scenario_generator=sg, seed=1234)

def llm_agent(observation, action_history, valid_actions):
    action_history_str = "\n".join([f"Step {i+1}: {action}" for i, action in enumerate(action_history)])
    prompt = f"Observation: {observation}\n\nAction History:\n{action_history_str}\n\nValid Actions: {', '.join(valid_actions)}\n\nWhat action should the agent take next?"

    response = openai.ChatCompletion.create(
        model="gpt-4-turbo-2024-04-09",
        messages=[
            {"role": "system", "content": "You are a cybersecurity agent navigating the CybORG environment."},
            {"role": "user", "content": prompt}
        ]
    )

    action_str = response.choices[0].message.content.strip()

    return action_str

reset = cyborg.reset(agent='blue_agent_0')
initial_obs = reset.observation

valid_actions = ["Analyse", "Remove", "Restore", "Monitor", "DeployDecoy", "BlockTrafficZone", "AllowTrafficZone"]

action_history = []

with open("observations.txt", "w") as file:
    for i in range(steps):
        observation = initial_obs if i == 0 else obs

        action_str = llm_agent(observation, action_history, valid_actions)

        action_map = {
            "Analyse": Analyse,
            "Remove": Remove,
            "Restore": Restore,
            "Monitor": Sleep,
            "DeployDecoy": DeployDecoy,
            "BlockTrafficZone": BlockTrafficZone,
            "AllowTrafficZone": AllowTrafficZone
        }

        action = action_map.get(action_str, Sleep)()

        obs = cyborg.step(agent='blue_agent_0', action=action).observation

        action_history.append(action_str)

        file.write(f"Step {i+1}:\n")
        file.write("Observation:\n")
        file.write(str(obs) + "\n")
        file.write("Action: " + str(action) + "\n")
        file.write("\n")

        print(f"Step {i+1}:")
        print("Observation:")
        print(obs)
        print("Action:", action)
        print()
