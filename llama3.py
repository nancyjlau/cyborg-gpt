import os
from datetime import datetime
from CybORG import CybORG
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from CybORG.Agents import SleepAgent, EnterpriseGreenAgent, FiniteStateRedAgent
from CybORG.Simulator.Actions import Sleep, Remove, Restore, Analyse, DeployDecoy
from CybORG.Simulator.Actions.ConcreteActions.ControlTraffic import AllowTrafficZone, BlockTrafficZone
from groq import Groq

api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key)  

steps = 30
sg = EnterpriseScenarioGenerator(blue_agent_class=SleepAgent,
                                green_agent_class=EnterpriseGreenAgent,
                                red_agent_class=FiniteStateRedAgent,
                                steps=steps)
cyborg = CybORG(scenario_generator=sg, seed=1234)
valid_actions = ["Analyse", "Remove", "Restore", "Monitor", "DeployDecoy", "BlockTrafficZone", "AllowTrafficZone"]

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

action_map = {
    "Analyse": Analyse,
    "Remove": Remove,
    "Restore": Restore,
    "Monitor": Sleep,
    "DeployDecoy": DeployDecoy,
    "BlockTrafficZone": BlockTrafficZone,
    "AllowTrafficZone": AllowTrafficZone
}

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
    Analyse suspicious activities to gather more information.
    Remove any identified malware or unauthorized access.
    Restore critical files or configurations to a known good state.
    Monitor the network when there are no immediate threats.
    Use deception techniques if you suspect an active intrusion attempt.
    Contain compromised subnets or hosts to limit the scope of the attack.
    Restore normal traffic flow to a blocked zone when it is confirmed to be safe.
    
    Memory:
    Previous actions taken: {previous_actions}

    Current state:
    Suspicious Files: {suspicious_files}
    Suspicious Processes: {suspicious_processes}
    Suspicious Connections: {suspicious_connections}
    Suspicious Sessions: {suspicious_sessions}

    One-shot examples of valid actions:
    Action: Analyse - Gather more information about a host with new processes or connections.
    Action: Remove - Isolate and remove identified malware or unauthorized access.
    Action: Restore - Recover critical files or configurations to a known good state.
    Action: Monitor - Continue monitoring the network when there are no immediate threats.
    Action: DeployDecoy - Use deception techniques if an active intrusion attempt is suspected.
    Action: BlockTrafficZone - Contain a compromised subnet or host to limit the attack scope.
    Action: AllowTrafficZone - Restore normal traffic flow to a blocked zone when it is confirmed safe.

    Query:
    Based on the current state and the provided examples, select the most appropriate action to take next. Respond with only the action name.
    """

    response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": "You are a cybersecurity agent managing a complex network."},
            {"role": "user", "content": prompt}
        ],
        model="llama3-8b-8192"  
    )
    action_str = response.choices[0].message.content.strip()

    debug_output = ""

    debug_output += f"LLM Response: {action_str}\n"

    if action_str.lower() == "monitor":
        return "Monitor", None
    else:
        try:
            if action_str.lower() in ["analyse", "analyze"] or ',' not in action_str:
                suspicious_hosts = [host for host in observation if isinstance(observation[host], dict) and 'Files' in observation[host]]
                if suspicious_hosts:
                    hostname = suspicious_hosts[0] 
                else:
                    valid_hosts = [host for host in observation if isinstance(observation[host], dict)]
                    hostname = valid_hosts[0] if valid_hosts else None  # Choose the first valid host or None if no valid hosts
                return "Analyse", hostname
            else:
                action_str, hostname = action_str.split(',')
                action_str = action_str.strip()
                hostname = hostname.strip()

                if action_str in valid_actions and hostname in observation:
                    return action_str, hostname
                else:
                    raise ValueError("Invalid action or hostname")
        except ValueError:
            return "Monitor", None

os.makedirs("llama3", exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
with open(f"llama3/observations-{timestamp}.txt", "w") as file:
    previous_actions = []
    for i in range(steps):
        observation = cyborg.get_observation(agent='blue_agent_0')
        action_str, hostname = llm_agent(observation, valid_actions, previous_actions)

        if hostname is None:
            print("No valid host found. Skipping action.")
            action = action_map["Monitor"]()
        else:
            action = Analyse(session=0, agent='blue_agent_0', hostname=hostname) if action_str == "Analyse" else action_map[action_str]()
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