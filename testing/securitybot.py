import os
from datetime import datetime
from CybORG import CybORG
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator
from CybORG.Agents import SleepAgent, EnterpriseGreenAgent, FiniteStateRedAgent
from CybORG.Simulator.Actions import Sleep, Remove, Restore, Analyse, DeployDecoy
from CybORG.Simulator.Actions.ConcreteActions.ControlTraffic import AllowTrafficZone, BlockTrafficZone
import openai
import numpy as np

rl_agents = load_rl_agents()

class SecurityBot:
    def __init__(self, api_key, steps):
        self.api_key = api_key
        self.steps = steps
        self.action_map = {
            "Analyse": Analyse,
            "Remove": Remove,
            "Restore": Restore,
            "Monitor": Sleep,
            "DeployDecoy": DeployDecoy,
            "BlockTrafficZone": BlockTrafficZone,
            "AllowTrafficZone": AllowTrafficZone
        }
        self.memories = []
        self.behavior_guidance = None
        self.ind = 0.0

    def run(self):
        sg = EnterpriseScenarioGenerator(blue_agent_class=SleepAgent,
                                         green_agent_class=EnterpriseGreenAgent,
                                         red_agent_class=FiniteStateRedAgent,
                                         steps=self.steps)
        cyborg = CybORG(scenario_generator=sg, seed=1234)

        os.makedirs("observations", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        with open(f"observations/observations-{timestamp}.txt", "w") as file:
            for i in range(self.steps):
                observation = cyborg.get_observation(agent='blue_agent_0')
                action_str = self.llm_agent(observation)
                
                action = self.action_map.get(action_str, Sleep)()
                cyborg.step(agent='blue_agent_0', action=action)

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

    def llm_agent(self, observation):
        # profile module
        if not self.behavior_guidance:
            self.behavior_guidance = self.profile_module(observation)

        # memory module
        self.memory_module(observation)

        # action module
        valid_actions = self.action_module(observation)

        # reflection module
        valid_actions = self.reflection_module(valid_actions)

        # collaboration with RL agents
        rl_suggestion = self.collaborate_with_rl_agents(observation, valid_actions)

        # cursor: growing to be independent
        if self.ind < 0.6:
            action_str = rl_suggestion
        else:
            action_str = self.llm_decision(observation, valid_actions)

        return action_str

    def profile_module(self, observation):
        # generate behavior guidance using LLM based on the initial observation
        prompt = f"""
        You are a cybersecurity agent managing a complex network. 
        Based on the following observation, generate an action sequence to guide your behavior.

        Observation:
        {observation}

        Action Sequence:
        1. Action: Analyse
           Goal: Gather information about suspicious activity
           Trigger: New processes or connections detected
           Following Actions: Remove or Restore
           Expected Outcome: Identify and isolate potential threats

        2. Action: Monitor
           Goal: Continuously monitor the network for anomalies
           Trigger: No immediate threats detected
           Following Actions: Analyse or DeployDecoy
           Expected Outcome: Maintain situational awareness

        3. Action: Remove
           Goal: Isolate and remove identified threats
           Trigger: Malware or unauthorized access detected
           Following Actions: Restore or Monitor
           Expected Outcome: Eliminate the threat and secure the system

        4. Action: Restore
           Goal: Recover system to a known good state
           Trigger: Critical files or configurations modified
           Following Actions: Monitor or Analyse
           Expected Outcome: Restore system integrity and functionality

        5. Action: DeployDecoy
           Goal: Deceive and divert attackers
           Trigger: Suspected active intrusion attempt
           Following Actions: Analyse or BlockTrafficZone
           Expected Outcome: Misdirect attacker and gather intelligence

        6. Action: BlockTrafficZone
           Goal: Contain the threat within a specific subnet or host
           Trigger: Compromised subnet or host identified
           Following Actions: Analyse or AllowTrafficZone
           Expected Outcome: Limit the scope of the attack

        7. Action: AllowTrafficZone
           Goal: Restore normal traffic flow to a blocked zone
           Trigger: Blocked zone confirmed to be safe
           Following Actions: Monitor or Analyse
           Expected Outcome: Resume normal network operations
        """

        response = openai.ChatCompletion.create(
            model="gpt-4-turbo-2024-04-09",
            messages=[
                {"role": "system", "content": "You are a cybersecurity agent managing a complex network."},
                {"role": "user", "content": prompt}
            ]
        )
        behavior_guidance = response.choices[0].message.content.strip()
        return behavior_guidance

    def memory_module(self, observation):
        # store current observation in memory
        importance = self.rate_importance(observation)
        memory = {
            "timestamp": datetime.now(),
            "observation": observation,
            "importance": importance
        }
        self.memories.append(memory)

    def rate_importance(self, observation):
        # rate the importance of the observation
        prompt = f"""
        Rate the importance of the following observation on a scale of 0 to 10:

        Observation:
        {observation}

        Importance (0-10):
        """

        response = openai.ChatCompletion.create(
            model="gpt-4-turbo-2024-04-09",
            messages=[
                {"role": "system", "content": "You are a cybersecurity agent managing a complex network."},
                {"role": "user", "content": prompt}
            ]
        )
        importance = int(response.choices[0].message.content.strip())
        return importance

    def search_memories(self, observation):
        # search for relevant memories based on current observation
        relevance_scores = []
        for memory in self.memories:
            relevance = self.calculate_relevance(observation, memory["observation"])
            freshness = 1 / (datetime.now() - memory["timestamp"]).total_seconds()
            score = memory["importance"] * relevance * freshness
            relevance_scores.append(score)

        top_indices = np.argsort(relevance_scores)[-2:]
        top_memories = [self.memories[i] for i in top_indices]
        return top_memories

    def calculate_relevance(self, observation1, observation2):
        # calculate relevance between two observations using cosine similarity
        vector1 = self.observation_to_vector(observation1)
        vector2 = self.observation_to_vector(observation2)
        relevance = np.dot(vector1, vector2) / (np.linalg.norm(vector1) * np.linalg.norm(vector2))
        return relevance

    def observation_to_vector(self, observation):
        # convert observation to vector representation, take note of observation format 
        # implement here       vector = np.random.rand(100)
        return vector

    def action_module(self, observation):
        # generate valid actions based on current observation and behavior guidance
        prompt = f"""
        Based on the following observation and behavior guidance, generate the valid actions that can be taken:

        Observation:
        {observation}

        Behavior Guidance:
        {self.behavior_guidance}

        Valid Actions:
        """

        response = openai.ChatCompletion.create(
            model="gpt-4-turbo-2024-04-09",
            messages=[
                {"role": "system", "content": "You are a cybersecurity agent managing a complex network."},
                {"role": "user", "content": prompt}
            ]
        )
        valid_actions = response.choices[0].message.content.strip().split('\n')
        return valid_actions

    def reflection_module(self, valid_actions):
        recent_actions = [memory["action"] for memory in self.memories[-3:]]
        recent_rewards = [memory["reward"] for memory in self.memories[-5:]]

        # dilemma case
        if len(set(recent_actions)) == 1 or all(reward <= 0 for reward in recent_rewards):
            prompt = f"""
            You have stuck in a situation for several steps. There are several reasons:
            1. The input to the environment may not be real, the defender may have fixed the 
               host that was previously attacked,
            2. The state of access you see in the environment may be fake.
               For instance, the User status of Access column maybe actually None, so the 
               Privilege host action would be failed.
            3. You may also stuck in attacking the defender host, which can not be privileged.
            When you in dilemmas, you can select an action instead of an action in action space.
            (It important to learn from you teammate if you are stucked)

            The recent actions and rewards are:

            Recent Actions: {recent_actions}
            Recent Rewards: {recent_rewards}

            Based on the above analysis, which actions should be taken to break out of the dilemma situation?
            """

            response = openai.ChatCompletion.create(
                model="gpt-4-turbo-2024-04-09",
                messages=[
                    {"role": "system", "content": "You are a cybersecurity agent managing a complex network."},
                    {"role": "user", "content": prompt}
                ]
            )
            best_action = response.choices[0].message.content.strip()
            return best_action

        return valid_actions

    def collaborate_with_rl_agents(self, observation, valid_actions):
        suggestions = []
        for agent in rl_agents:
            suggestion, confidence = agent.get_suggestion(observation)
            suggestions.append((suggestion, confidence))

        # aggregator: rank suggestions based on confidence
        suggestions.sort(key=lambda x: x[1], reverse=True)

        # caller: ask for help when in dilemma
        if len(valid_actions) == 0:
            top_suggestions = [suggestion[0] for suggestion in suggestions[:3]]
            return top_suggestions[0]
        else:
            return suggestions[0][0]

    def llm_decision(self, observation, valid_actions):
        prompt = f"""
        Based on the following observation and valid actions, choose the best action to take:

        Observation:
        {observation}

        Valid Actions:
        {valid_actions}

        Best Action:
        """

        response = openai.ChatCompletion.create(
            model="gpt-4-turbo-2024-04-09",
            messages=[
                {"role": "system", "content": "You are a cybersecurity agent managing a complex network."},
                {"role": "user", "content": prompt}
            ]
        )
        best_action = response.choices[0].message.content.strip()
        return best_action

def load_rl_agents():
    # need to implement here to load RL agents
    agents = []
    return agents

if __name__ == "__main__":
    openai.api_key = "YOUR_API_KEY"
    steps = 100
    security_bot = SecurityBot(api_key=openai.api_key, steps=steps)
    security_bot.run()