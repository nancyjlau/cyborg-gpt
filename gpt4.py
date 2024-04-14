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

def llm_agent(observation, valid_actions):
    if "action" in observation and observation["action"] == "Sleep":
        # Check for new processes or connections
        suspicious_processes, suspicious_connections = extract_suspicious_processes_connections(observation)
        if suspicious_processes or suspicious_connections:
            # If new processes or connections are detected, choose the "Analyse" action
            return "Analyse"
        else:
            return "Monitor"

    suspicious_files, suspicious_processes, suspicious_connections, suspicious_sessions = extract_observation_details(observation)

    prompt = f"""
    Observation Details:
    Suspicious Files: {suspicious_files}
    Suspicious Processes: {suspicious_processes}
    Suspicious Connections: {suspicious_connections}
    Suspicious Sessions: {suspicious_sessions}

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


    Guidelines for choosing an action:
    - If new processes or connections are detected on a host, perform an "Analyse" action on that host to gather more information.
    - If the analysis reveals the presence of malware or unauthorized access, use the "Remove" action to isolate the threat.
    - If critical files or configurations have been modified, use the "Restore" action to recover the system to a known good state.
    - If there are no immediate threats, continue monitoring the network using the "Monitor" action.
    - If you suspect an active intrusion attempt, consider using the "DeployDecoy" action to deceive the attacker.
    - If a specific subnet or host appears compromised, use the "BlockTrafficZone" action to contain the threat.
    - If a blocked zone is confirmed to be safe, use the "AllowTrafficZone" action to restore normal traffic flow.

    Based on the provided observation details and the guidelines above, which action should be taken next?
    Please respond with one of the valid actions listed above.
    """

    # Use OpenAI API to determine the next action
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo-2024-04-09",
        messages=[
            {"role": "system", "content": "You are a cybersecurity agent managing a complex network."},
            {"role": "user", "content": prompt}
        ]
    )
    action_str = response.choices[0].message.content.strip()
    return action_str

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
    for i in range(steps):
        observation = cyborg.get_observation(agent='blue_agent_0')
        action_str = llm_agent(observation, valid_actions)
        
        action = action_map.get(action_str, Sleep)()
        cyborg.step(agent='blue_agent_0', action=action)

        # Write to file and print to console
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