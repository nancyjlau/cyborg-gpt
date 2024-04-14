import os
from datetime import datetime
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
    
    suspicious_files = observation.get("Files", [])
    suspicious_processes = observation.get("Processes", [])
    suspicious_connections = [p.get("Connections", []) for p in suspicious_processes]
    suspicious_sessions = observation.get("Sessions", [])
    
    prompt = f"""
    Observation:
    Suspicious Files: {suspicious_files}
    Suspicious Processes: {suspicious_processes}
    Suspicious Connections: {suspicious_connections}
    Suspicious Sessions: {suspicious_sessions}

    Action History:
    {action_history_str}

    Valid Actions: {', '.join(valid_actions)}

    Examples of malicious activity:
    - Files with unknown extensions or random names in temporary directories (e.g., "/tmp/cmd.sh", "/tmp/escalate.sh").
    - Processes running from temporary directories or unusual locations.
    - Connections to unknown or blacklisted IP addresses.
    - Sessions with privileged access (e.g., "root" sessions).
    - Unexpected changes to system files or configurations.

    Specific examples:
    - Presence of "cmd.sh" in "/tmp/" indicates a potential user-level shell.
    - Presence of both "cmd.sh" and "escalate.sh" in "/tmp/" suggests a root-level shell.
    - Discovery of a new service running on port 25 (SMTP) could be a decoy service.
    - The "PrivilegeEscalate" action indicates an attempt to gain higher privileges.

    Based on the observation and examples, what action should the agent take next? Please respond with one of the valid actions: {', '.join(valid_actions)}
    """
    
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo-2024-04-09",
        messages=[
            {"role": "system", "content": "You are a cybersecurity agent managing a complex enterprise network. Your goal is to protect the network from cyber threats while minimizing disruption to legitimate activity."},
            {"role": "user", "content": prompt}
        ]
    )
    
    action_str = response.choices[0].message.content.strip()
    
    return action_str

reset = cyborg.reset(agent='blue_agent_0')
initial_obs = reset.observation

valid_actions = ["Analyse", "Remove", "Restore", "Monitor", "DeployDecoy", "BlockTrafficZone", "AllowTrafficZone"]

action_history = []

os.makedirs("observations", exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

with open(f"observations/observations-{timestamp}.txt", "w") as file:
    for i in range(steps):
        observation = initial_obs if i == 0 else obs
        
        action_str = llm_agent(observation, action_history, valid_actions)
        
        action_map = {
            "Analyse": Analyse,
            "Remove": Remove,
            "Restore": Restore,
            "Monitor": Sleep,  # Sleep is used for monitoring
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