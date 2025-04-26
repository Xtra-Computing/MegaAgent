from agent import *
import logging
import re

def init_logger():
    logger = logging.getLogger()
    formatter = logging.Formatter('%(asctime)s: %(message)s')
    f_handler = logging.FileHandler('log.txt')
    f_handler.setFormatter(formatter)
    logger.addHandler(f_handler)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.setLevel(logging.INFO)

if __name__ == "__main__":
    delete_all_files_in_folder("logs")
    delete_all_files_in_folder("files")
    git_commit("Initial commit")
    # if os.path.exists('log.txt'):
    #     os.remove('log.txt')
    init_logger()
    begin_time = time.time()
    meta_output = get_llm_response([{"role": "system", "content": config.initial_prompt}], False)['choices'][0]['message']['content']
    logging.info(meta_output)
    
    agent_pattern = re.compile(r'<agent name="(\w+)">(.*?)</agent>', re.DOTALL)
    agents = agent_pattern.findall(meta_output)

    for agent in agents:
        if agent[0] == config.ceo_name:
            agent_dict[agent[0]] = Agent(agent[0], agent[1])
    
    for agent in agents:
        if agent[0] != config.ceo_name:
            agent_dict[config.ceo_name].add_subordinate(agent[0], "", agent[1])

    agent_dict[config.ceo_name].enqueue("user","Now let's start the project. Please split the task and talk to your subordinates to assign the tasks.")

    # Wait until all agents become idle
    while True:
        time.sleep(1)
        if all(agent.state == "idle" for agent in agent_dict.values()):
            ok = True
            for agent in agent_dict.values():
                try:
                    with git_lock:
                        f = open(f"files/todo_{agent.name}.txt", 'r')
                        content = f.read()
                        f.close()
                except FileNotFoundError:
                    content = ''
                if content != '':
                    agent.enqueue("system","Other agents have terminated. However, you still have unfinished tasks in your TODO list. Please finish them and clear it. If you are waiting for someone, chances are that they have forgotten about you. Please remind them.")
                    ok = False
            if not ok:
                continue
            else:
                agent_dict[config.ceo_name].enqueue("system","All the agents have terminated. Please browse all the target files to test them if needed, and check whether the project has been completed(do not leave placeholders!). If true, please call the 'terminate' function; if not, please assign the remaining tasks.")
                while(agent_dict[config.ceo_name].state != "idle"):
                    time.sleep(1)
                if all(agent.state == "idle" for agent in agent_dict.values()):
                    break
                else:
                    continue
    end_time = time.time()
    logging.info(f"Time elapsed: {end_time-begin_time} seconds")
    # logging.info(f"Input tokens: {input_token}, output tokens: {output_token}")
    logging.info(f"Number of agents: {len(agent_dict)}")
