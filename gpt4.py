import os
from datetime import datetime
from CybORG import CybORG
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from CybORG.Agents import SleepAgent, EnterpriseGreenAgent, FiniteStateRedAgent
from CybORG.Simulator.Actions import Sleep, Remove, Restore, Analyse, DeployDecoy
from CybORG.Simulator.Actions.ConcreteActions.ControlTraffic import AllowTrafficZone, BlockTrafficZone
import openai

openai.api_key = "OPENAI_API_KEY"
steps = 30
sg = EnterpriseScenarioGenerator(blue_agent_class=SleepAgent,
                    green_agent_class=EnterpriseGreenAgent,
                    red_agent_class=FiniteStateRedAgent,
                    steps=steps)
cyborg = CybORG(scenario_generator=sg, seed=1234)
valid_actions = ["Analyse", "Remove", "Restore", "Monitor", "DeployDecoy", "BlockTrafficZone", "AllowTrafficZone"]

def get_action_params(observation, hostname):
    session = None
    agent = 'blue_agent_0'

    for host, info in observation.items():
        if host == hostname:
            if "Sessions" in info:
                for session_info in info["Sessions"]:
                    if session_info["agent"] == agent:
                        session = session_info["session_id"]
                        break
            break

    if session is None:
        session = 0

    return session, agent, hostname

action_map = {
    "Analyse": lambda obs, hostname: Analyse(session=get_action_params(obs, hostname)[0], agent=get_action_params(obs, hostname)[1], hostname=hostname),
    "Remove": lambda obs, hostname: Remove(session=get_action_params(obs, hostname)[0], agent=get_action_params(obs, hostname)[1], hostname=hostname),
    "Restore": lambda obs, hostname: Restore(session=get_action_params(obs, hostname)[0], agent=get_action_params(obs, hostname)[1], hostname=hostname),
    "Monitor": lambda: Sleep(),
    "DeployDecoy": lambda obs, hostname: DeployDecoy(session=get_action_params(obs, hostname)[0], agent=get_action_params(obs, hostname)[1], hostname=hostname),
    "BlockTrafficZone": lambda obs, hostname: BlockTrafficZone(session=get_action_params(obs, hostname)[0], agent=get_action_params(obs, hostname)[1], hostname=hostname),
    "AllowTrafficZone": lambda obs, hostname: AllowTrafficZone(session=get_action_params(obs, hostname)[0], agent=get_action_params(obs, hostname)[1], hostname=hostname)
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

    print("Suspicious Files:", suspicious_files)
    print("Suspicious Processes:", suspicious_processes)
    print("Suspicious Connections:", suspicious_connections)
    print("Suspicious Sessions:", suspicious_sessions)

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

        print("LLM Response:", action_str)

        if action_str == "Monitor":
            print("Selected Action: Monitor")
            return action_str, None
        else:
            try:
                action_str, hostname = action_str.split(',')
                action_str = action_str.strip()
                hostname = hostname.strip()

                print("Parsed Action:", action_str)
                print("Parsed Hostname:", hostname)

                if action_str in valid_actions and hostname in observation:
                    print("Selected Action:", action_str)
                    print("Selected Hostname:", hostname)
                    return action_str, hostname
                else:
                    raise ValueError
            except ValueError:
                print("Invalid Action or Hostname")
                prompt += f"\nInvalid action or hostname. Please provide a valid action and hostname separated by a comma, or respond with 'Monitor' if there are no immediate threats.\n\nAction:"

    
os.makedirs("observations", exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
with open(f"observations/observations-{timestamp}.txt", "w") as file:
    previous_actions = []
    for i in range(steps):
        observation = cyborg.get_observation(agent='blue_agent_0')
        action_str, hostname = llm_agent(observation, valid_actions, previous_actions)

        action = action_map.get(action_str)(observation, hostname) if hostname else action_map.get(action_str)()
        cyborg.step(agent='blue_agent_0', action=action)

        previous_actions.append(f"{action_str}, {hostname}")
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
