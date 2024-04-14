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
valid_actions = ["Analyse", "Remove", "Restore", "Monitor", "DeployDecoy", "BlockTrafficZone", "AllowTrafficZone"]
action_map = {
    "Analyse": Analyse,
    "Remove": Remove,
    "Restore": Restore,
    "Monitor": Sleep, 
    "DeployDecoy": DeployDecoy,
    "BlockTrafficZone": BlockTrafficZone,
    "AllowTrafficZone": AllowTrafficZone
}

def extract_observation_details(observation):
    suspicious_files = []
    suspicious_processes = []
    suspicious_connections = []
    suspicious_sessions = []

    for host, info in observation.items():
        if isinstance(info, dict):
            if "Files" in info:
                suspicious_files.extend(info["Files"])
            if "Processes" in info:
                for process in info["Processes"]:
                    if "Connections" in process:
                        suspicious_connections.extend(process["Connections"])
                    suspicious_processes.append(process)
            if "Sessions" in info:
                suspicious_sessions.extend(info["Sessions"])

    return suspicious_files, suspicious_processes, suspicious_connections, suspicious_sessions

def llm_agent(observation, valid_actions, previous_actions):
    suspicious_files, suspicious_processes, suspicious_connections, suspicious_sessions = extract_observation_details(observation)

    prompt = f"""
    Initial instructions and rules:
    You are a cybersecurity agent managing a complex network. Your goal is to detect and respond to potential security threats.
    
    The rules are:

    Analyze suspicious activities to gather more information.
    Remove any identified malware or unauthorized access.
    Restore critical files or configurations to a known good state.
    Monitor the network when there are no immediate threats.
    Use deception techniques if you suspect an active intrusion attempt.
    Contain compromised subnets or hosts to limit the scope of the attack.
    Restore normal traffic flow to a blocked zone when it is confirmed to be safe.
    
    Memory:
    Previous actions taken:
    {previous_actions}

    Current state:
    Suspicious Files: {suspicious_files}
    Suspicious Processes: {suspicious_processes}
    Suspicious Connections: {suspicious_connections}
    Suspicious Sessions: {suspicious_sessions}

    One-shot examples of valid actions:
    Action: Analyse
    Description: Gather more information about a host with new processes or connections.

    Action: Remove
    Description: Isolate and remove identified malware or unauthorized access.

    Action: Restore
    Description: Recover critical files or configurations to a known good state.

    Action: Monitor
    Description: Continue monitoring the network when there are no immediate threats.

    Action: DeployDecoy
    Description: Use deception techniques if an active intrusion attempt is suspected.

    Action: BlockTrafficZone
    Description: Contain a compromised subnet or host to limit the attack scope.

    Action: AllowTrafficZone
    Description: Restore normal traffic flow to a blocked zone when it is confirmed safe.

    Query:
    Based on the current state and the provided examples, select the most appropriate action to take next. Respond with only the action name.

    Action:
    """

    while True:
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo-2024-04-09",
            messages=[
                {"role": "system", "content": "You are a cybersecurity agent managing a complex network."},
                {"role": "user", "content": prompt}
            ]
        )
        action_str = response.choices[0].message.content.strip()

        if action_str in valid_actions:
            return action_str
        else:
            prompt += f"\nInvalid action: {action_str}. Please select a valid action from the following list: {', '.join(valid_actions)}.\n\nAction:"



def extract_suspicious_processes_connections(observation):
    suspicious_processes = []
    suspicious_connections = []

    for host, info in observation.items():
        if isinstance(info, dict):
            if "Processes" in info:
                for process in info["Processes"]:
                    if "Connections" in process:
                        suspicious_connections.extend(process["Connections"])
                        suspicious_processes.append(process)

    return suspicious_processes, suspicious_connections

os.makedirs("observations", exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
with open(f"observations/observations-{timestamp}.txt", "w") as file:
    previous_actions = []  
    for i in range(steps):
        observation = cyborg.get_observation(agent='blue_agent_0')
        action_str = llm_agent(observation, valid_actions, previous_actions)
        
        action = action_map.get(action_str, Sleep)()
        cyborg.step(agent='blue_agent_0', action=action)

        previous_actions.append(action_str)
        previous_actions = previous_actions[-5:]

        file.write(f"Step {i+1}:\n")
        file.write("Observation:\n")
        file.write(str(observation) + "\n")
        file.write("Action: " + str(action) + "\n")
        file.write("\n")
        
        print(f"Step {i+1}:")
        print("Observation:")
        print(observation)
        print("Action:", action)
        print()