import config
import re
from utils import git_lock
from llm import *
import threading
import logging
import chromadb
import time
import os

def delete_all_files_in_folder(folder_path):
    # Get all files in the folder
    files = os.listdir(folder_path)
    
    for file in files:
        file_path = os.path.join(folder_path, file)
        # Check if it is a file to prevent deleting folders
        if os.path.isfile(file_path):
            os.remove(file_path)
            print(f"{file} has been deleted.")
        else:
            print(f"{file} is not a file and has been skipped.")
    
# Example usage
folder_path = 'files'  # Specify the folder path
delete_all_files_in_folder(folder_path)
if os.path.exists('log.txt'):
    os.remove('log.txt')

from utils import *
logger = logging.getLogger()
logger.setLevel(logging.INFO)
rf_handler = logging.StreamHandler()
f_handler = logging.FileHandler('log.txt')
logger.addHandler(rf_handler)
logger.addHandler(f_handler)
begin_time = time.time()
chroma_client = chromadb.Client()

employee_dict = {}
employee_dict[config.ceo_name] = {
    'memory': [{"role": "user", "content": config.initial_prompt}],
    'lock': threading.Lock(),
    'pending': False,
    'history': chroma_client.create_collection(name=config.ceo_name)
}

llm_output = get_llm_response(employee_dict[config.ceo_name]['memory'],enable_tools=False)['choices'][0]['message']['content']
llm_output+="\n<beginner>NationLeader</beginner>"
logging.info(f"{config.ceo_name}:\n{llm_output}")

employee_dict[config.ceo_name]['memory'].append({"role": "assistant", "content": llm_output})
employee_dict[config.ceo_name]['history'].add(documents=[f"{config.ceo_name}:\n{llm_output}"], ids=[str(time.time())])

employee_pattern = re.compile(r'<employee name="(\w+)">(.*?)</employee>', re.DOTALL)
employees = employee_pattern.findall(llm_output)

for employee in employees:
    employee_dict[employee[0]] = {
        'initial_prompt': f"{employee[1]}\n{config.additional_prompt}",
        'memory': [{"role": "system", "content": f"{employee[1]}\n{config.additional_prompt}\nYou can write your TODO list in todo_{employee[0]}.txt. \n"}],
        'lock': threading.Lock(),
        'pending': False,
        'history': chroma_client.create_collection(name=employee[0]) if employee[0] != config.ceo_name else employee_dict[config.ceo_name]['history'],
        'subordinate': []
    }

for employee in employees:
    used_names.add(employee[0])
    if employee[0] != config.ceo_name:
        employee_dict[config.ceo_name]['subordinate'].append({"name": employee[0], "description": employee[1]})

employee_dict[config.ceo_name]['memory'][-1]["content"]+=f"\nYour have just recruited these agents before: {[employee['name'] for employee in employee_dict[config.ceo_name]['subordinate']]} as your ministers. DO NOT recuit them again! DO NOT recruit testers, read or write policies by yourself! (that should be done by your ministers)! Nevertheless, you can add more ministers responsible for other departments besides them, but no more than 10. After that, you MUST talk to your ministers to assign tasks and let them design policies using <talk goal=\"Name\">TalkContent</talk> format, and initiate the policy-making process. They will not start working unless you talk to them!"

beginner_pattern = re.compile(r'<beginner>(\w+)</beginner>')
beginners = beginner_pattern.findall(llm_output)
beginner_list = [beginner for beginner in beginners if beginner in employee_dict]

threads = []

def add_memory(employee_name, output):
    # Add memory to the employee's memory list
    # implemented TODO list
    if output == '' or output == 'TERMINATE':
        return
    employee = employee_dict[employee_name]
    employee['memory'].append(output)
    # employee['memory'] = [memory for memory in employee['memory'] if memory['role'] != 'tool']
    content = f"{employee_name}:\n{output['content']}"
    
    if len(employee['memory']) > config.MAX_LEN and employee['memory'][-1]['role'] == 'user':
        try:
            with git_lock:
                f = open(f"files/todo_{employee_name}.txt", 'r')
                todo_list = f.read()
                f.close()
        except FileNotFoundError:
            todo_list = ''
        
        if todo_list == '':
            todo_list = f'You have not written any TODO list yet. If you still have something to do, please write it in todo_{employee_name}.txt\n'
        else:
            with git_lock:
                commit_hash = subprocess.check_output(['git', '-C', 'files', 'rev-parse', 'HEAD'], text=True).strip()
            todo_list = f'Your TODO list:\n{todo_list}\nYou can change it in todo_{employee_name}.txt, by providing its current hash:{commit_hash}(will change if you edit TODO list)\n'
        if len(employee['subordinate']) > 0:
            todo_list += f"\nYour have recruited these subordinates: {str(employee['subordinate'])}\n"
        if employee['memory'][-1]['content'] != None:
            relevant_history = employee['history'].query(query_texts=[employee['memory'][-1]['content']], n_results=1)
            summary = f"Here are some relevant chat history:\n{relevant_history['documents'][0][0]}\nBelow is the most recent chat history:\n"
        else:
            summary = "Here is the most recent chat history:\n"
        for memory in employee['memory']:
            if memory['role'] == 'tool':
                memory['role'] = 'user'
        employee['memory'] = [{"role": "system", "content": employee['initial_prompt']+todo_list}] + [{"role": "user", "content": summary}] + employee['memory'][-config.MAX_LEN+2:]
    
    employee['history'].add(documents=[content], ids=[str(time.time())])

def work(employee_name, callback=None):
    # Main work function for each employee
    if callback == employee_name:
        callback = None
    employee = employee_dict[employee_name]
    employee['lock'].acquire()
    if employee['pending'] == False:
        employee['lock'].release()
        return
    employee['pending'] = False
    response = get_llm_response(employee['memory'])
    assistant_output = response['choices'][0]['message']
    llm_output = assistant_output['content']
    if llm_output == None:
        llm_output = ''
    add_memory(employee_name, assistant_output)
    if assistant_output['content']:
        logging.info(f"{employee_name}:\n{assistant_output['content']}")
    result = package = None
    while 'function_call' in assistant_output and len(employee['memory']) < config.max_memory_length:
        tool_call = assistant_output['function_call']
        tool_name = tool_call['name']
        tool_info = {"role": "function"}
        
        try:
            arguments = json.loads(tool_call['arguments'])
            
            if tool_name == 'exec_python_file':
                tool_info['name'] = 'exec_python_file'
                filename = arguments['filename']
                try:
                    result, package = start_interactive_subprocess(filename)
                except Exception as e:
                    result = f"Error: {e}"
                # result = exec_python_file(filename)
                tool_info['content'] = str(result)
                result = f"{filename}\n---Result---\n{result}"
            elif tool_name == 'input':
                tool_info['name'] = 'input'
                content = arguments['content']
                if package:
                    try:
                        result, package = send_input(content,package)
                    except Exception as e:
                        result = f"Error: {e}"
                else:
                    result = "Error: No process to input."
                tool_info['content'] = str(result)
                result = f"Input:\n{content}\n---Result---\n{result}"
            elif tool_name == 'read_file':
                tool_info['name'] = 'read_file'
                filename = arguments['filename']
                content, hashvalue = read_file(filename)
                result = f"{filename}\n---Content---\n{content}\n---base_commit_hash---\n{hashvalue}"
                tool_info['content'] = result
            elif tool_name == 'write_file':
                tool_info['name'] = 'write_file'
                filename = arguments['filename']
                content = arguments['content']
                if 'overwrite' in arguments:
                    overwrite = arguments['overwrite']
                    base_commit_hash = arguments['base_commit_hash'] if 'base_commit_hash' in arguments else None
                    result = write_file(filename, content, overwrite, base_commit_hash)
                else:
                    result = write_file(filename, content)
                tool_info['content'] = result
                result = f"{filename}\n---Content---\n{content}\n---Result---\n{result}"
            elif tool_name == 'add_agent':
                if len(employee['subordinate']) > 5:
                    tool_info['name'] = 'add_agent'
                    result = tool_info['content'] = f'Error: You have already recruited 5 agents. No more agents can be recruited.\nRecruited agents: {str(employee["subordinate"])}'
                else:
                    tool_info['name'] = 'add_agent'
                    tool_info['content'] = 'Success.'
                    agent_name = arguments['name']
                    if agent_name in used_names:
                        # tool_info['content'] = f"Error: {agent_name} already exists. Please use another name."
                        # logging.error(f"Error: {agent_name} already exists. Please use another name.")
                        agent_name = agent_name + '_' + str(time.time())[-5:]
                        if agent_name.startswith('Minister'):
                            tool_info['content'] = f"Error: {arguments['name']} has already been recruited!"
                        else:
                            tool_info['content'] = f"Warning: {arguments['name']} already exists. Automatically change to {agent_name}.\nSuccess."
                    employee_dict[agent_name] = {
                        'initial_prompt': arguments['initial_prompt']+config.additional_prompt+"\nYou can write your TODO list in todo_"+agent_name+".txt."+"\nYour supervisor is: "+employee_name,
                        'memory': [{"role": "system", "content": arguments['initial_prompt']+config.additional_prompt+"\nYou can write your TODO list in todo_"+agent_name+".txt."+"\nYour supervisor is: "+employee_name +". You can use the <talk goal='Name'>Content</talk> format to talk to him."}],
                        'lock': threading.Lock(),
                        'pending': False,
                        'history': chroma_client.create_collection(name=agent_name),
                        'subordinate': []
                    }
                    employee['subordinate'].append({"name": agent_name, "description": arguments['description']})
                    used_names.add(agent_name)
                    result = f"Add agent: {agent_name} success, with description: {arguments['description']}, and initial_prompt: {arguments['initial_prompt']}"
            elif tool_name == 'talk':
                pattern = re.compile(r'<talk goal=(?:"([^"]+)"|\'([^\']+)\')>(.*?)</talk>', re.IGNORECASE | re.DOTALL)
                matches = re.findall(pattern, arguments['messages'])
                tool_info['name'] = 'talk'
                result = arguments['messages']
                if matches:
                    tool_info['content'] = 'Successfully sent.'
                else:
                    tool_info['content'] = 'Error: No matched <talk goal="Name"></talk> found in your response. You must talk in this specific XML format.'
                for match in matches:
                    name = match[0] if match[0] else match[1]
                    content = match[2].strip()
                    
                    if name in employee_dict:
                        if name == callback:
                            call_backed = True
                        relevant_history = employee_dict[name]['history'].query(query_texts=content, n_results=1)
                        add_memory(name, {"role": "user", "content": f"{employee_name}:\n{content}"})
                        
                        if not employee_dict[name]['pending'] and (len(relevant_history['distances'][0])==0 or relevant_history['distances'][0][0] > 0.1):
                            threads.append(threading.Thread(target=work, args=(name, employee_name)))
                            employee_dict[name]['pending'] = True
                            threads[-1].start()
                    else:
                        logging.error(f"Error: '{name}' has not been recruited yet.")
                        employee['memory'].append({"role": "user", "content": f"Error: \"{name}\" not found in employee_dict. \"Name\" should only be ONE specific employee. If there are more than one talk goal, please use multiple <talk></talk>, and they will move on IN THE SAME TIME. If you are done with current work, please only output: TERMINATE"})
                        ok = False
                        employee['pending'] = True  
            elif tool_name == 'TERMINATE' or tool_name == 'terminate':
                content, hashvalue = read_file(f"todo_{employee_name}.txt")
                if content != '':
                    result = f"Error: You have not completed your TODO list yet. Please complete it before terminating the project, and then clear your TODO list(write nothing into it, base_commit_hash={hashvalue}) to end the your work."
                    tool_info['name'] = tool_name
                    tool_info['content'] = result
                else:
                    employee['lock'].release()
                    return
            else:
                raise ValueError(f"Error: {tool_name} is not a valid function name")
            employee['memory'].append(tool_info)
        except ValueError as e:
            employee['memory'] = employee['memory'][:-1]
            employee['memory'].append({"role": "user", "content": str(e)})
        except Exception as e:
            logging.error(e)
            employee['memory'].append({"role": "user", "content": str(e)})
        
        # too much token cost, but deduct file IO. Use for your own need
        # llm_output += f"\n{tool_name}:\n{result}"
    
        response = get_llm_response(employee['memory'])
        assistant_output = response['choices'][0]['message'] if 'message' in response['choices'][0] else response['choices'][0]['messages'][-1]
        # llm_output += f"\n{employee_name}:\n{assistant_output['content']}"
        if assistant_output['content'] != None:
            llm_output += assistant_output['content'] + '\n'
        add_memory(employee_name, assistant_output)
        logging.info(f"{tool_name}:\n{result}")
        if assistant_output['content']:
            logging.info(f"{employee_name}:\n{assistant_output['content']}")
    if len(employee['memory']) > config.max_memory_length and employee_name != config.ceo_name:
        while employee['memory'][-1]['role'] != 'user' and len(employee['memory']) > 1:
            employee['memory'].pop(-1)
        user_memory = employee['memory'][-1]
        employee['memory'].pop(-1)
        add_memory(employee_name, user_memory)
    if package:
        try:
            package[0].terminate()
        except Exception as e:
            logging.error(f"Error: {e}")
    pattern = re.compile(r'<talk goal=(?:"([^"]+)"|\'([^\']+)\')>(.*?)</talk>', re.IGNORECASE | re.DOTALL)
    if assistant_output['content']:
        matches = re.findall(pattern, assistant_output['content'])
    else:
        matches = None
    if not matches:
        employee['lock'].release()
        
        # if "TERMINATE" not in llm_output and not employee['pending']:
        #     employee['pending'] = True
        #     logging.error('Error: No matched <talk goal="Name"></talk> found')
        #     employee['memory'].append({"role": "user", "content": 'Error: No matched <talk goal="Name"></talk> found in your response. You must name someone to relay in this specific format. If you do not want to talk to others, please output "TERMINATE".'})
        #     work(employee_name, callback)
        # else:
        if callback and llm_output != 'TERMINATE' and llm_output is not None:
            add_memory(callback, {"role": "user", "content": f"{employee_name}:\n{llm_output}"})
            work(callback)
        return
    
    call_backed = False
    ok = True
    for match in matches:
        name = match[0] if match[0] else match[1]
        content = match[2].strip()
        
        if name in employee_dict:
            if name == callback:
                call_backed = True
            relevant_history = employee_dict[name]['history'].query(query_texts=content, n_results=1)
            add_memory(name, {"role": "user", "content": f"{employee_name}:\n{content}"})
            
            if not employee_dict[name]['pending'] and (len(relevant_history['distances'][0])==0 or relevant_history['distances'][0][0] > 0.1):
                threads.append(threading.Thread(target=work, args=(name, employee_name)))
                employee_dict[name]['pending'] = True
                threads[-1].start()
        else:
            logging.error(f"Error: '{name}' has not been recruited yet.")
            employee['memory'].append({"role": "user", "content": f"Error: \"{name}\" not found in employee_dict. \"Name\" should only be ONE specific employee. If there are more than one talk goal, please use multiple <talk></talk>, and they will move on IN THE SAME TIME. If you are done with current work, please only output: TERMINATE"})
            ok = False
            employee['pending'] = True
    
    if not call_backed and callback:
        add_memory(callback, {"role": "user", "content": f"{employee_name}:\n{llm_output}"})
    
    employee['lock'].release()

    if not ok:
        work(employee_name, callback)


for beginner in beginner_list:
    threads.append(threading.Thread(target=work, args=(beginner,)))
    employee_dict[beginner]['pending'] = True

for thread in threads:
    thread.start()

for thread in threads:
    thread.join()

while True:
    threads = []
    for employee_name in employee_dict:
        try:
            with git_lock:
                f = open(f"files/todo_{employee_name}.txt", 'r')
                todo_list = f.read()
                f.close()
        except FileNotFoundError:
            todo_list = ''
        if todo_list != '':
            employee_dict[employee_name]['memory'].append({"role": "user", "content": f"Please complete your TODO list:\n{todo_list}\nYou can change it in todo_{employee_name}.txt.\nIf you have completed all, please clear your TODO list(write nothing into it) to end the project."})
            employee_dict[employee_name]['pending'] = True
            threads.append(threading.Thread(target=work, args=(employee_name,)))
    for thread in threads:
        thread.start()
    if not threads: 
        employee_dict[config.ceo_name]['memory'].append({"role": "user", "content": f"All ministers have completed their TODO list. Please review all the policy files by read_file:{written_files} Make sure all the policies are detailed and contain all the needed regulations, and see if there is anything unfinished(like a placeholder), or needs further improvements. In that case, please talk to your employees. Make sure the project is ready to release, and then you may output 'TERMINATE' to end the project."})
        employee_dict[config.ceo_name]['pending'] = True
        work(config.ceo_name)
        if employee_dict[config.ceo_name]['memory'][-1]['content']==None or "TERMINATE" in employee_dict[config.ceo_name]['memory'][-1]['content']:
            break
    for thread in threads:
        thread.join()

end_time = time.time()
logging.info(f"Time elapsed: {end_time-begin_time} seconds")
logging.info(f"Input tokens: {input_token}, output tokens: {output_token}")
logging.info(f"Number of agents: {len(employee_dict)}")
# print('-----------------')
# for employee in employee_dict.values():
#     print(employee['history'].get())
#     print('-----------------')
