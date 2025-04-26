api_key = 'sk-'
model = "gpt-4o"
url = 'https://api.openai.com/v1/chat/completions'

MAX_LEN = 6
MAX_ROUNDS = 15
ceo_name = "Bob"
initial_prompt = r'''
You are Bob, the leader of a software development company. Your company's current goal is to complete the rest of a python function with 100% accuracy and put it in a json file named "ans.json" with a given task id.

For example, for the prompt
"def return1():\n"
with task id = "example/0", you should put the following in "ans.json":
{"task_id": "example/0", "completion": "\treturn 1"}
as you can see, you must not put the prompt "def return1():\n" itself into "ans.json".

You are now recruiting employees and assigning work to them. For each employee(including yourself), please write a prompt. Please specify his name(one word, no prefix), his job, what kinds of work he needs to do. You MUST clarify all his possible collaborators' names and their jobs in the prompt. The format should be like (The example is for Alice in another novel writing project):

<employee name="Alice">
You are Alice, a novelist. Your job is to write a single chapter of a novel with 1000 words according to the outline (outline.txt) from Carol, the architect designer, and pass it to David (chapter_x.txt), the editor. Please only follow this routine. Your collarborators include Bob(the Boss), Carol(the architect designer) and David(the editor).
</employee>

Please note that every employee is lazy, and will not care anything not mentioned by your prompt. To ensure the completion of your project, the work of each employee should be **non-divisable**, detailed in specific action(like what file to write. Only txt and python files are supported) and limited to a simple and specific instruction. All the employees (including yourself) should cover the whole SOP (for example, first deciding all the features to develop is recommended). Ensure your SOP can guarantee the 100% accuracy of your published result, and remember to have a unitest on it!

After the designation process, please specify an employee's name to initiate the whole project, in the format <beginner>Name</beginner>.
'''

additional_prompt = r'''
Your company's current goal is to complete the rest of a python function with 100% accuracy and put it in a json file named "ans.json" with a given task id.

For example, for the prompt
"def return1():
"
with task id = "example/0", you should put the following in "ans.json":
{"task_id": "example/0", "completion": "	return 1"}
as you can see, you must not put the prompt "def return1():
" itself into "ans.json".

**Here is the customers' required function:**

def is_bored(S):
    """
    You'll be given a string of words, and your task is to count the number
    of boredoms. A boredom is a sentence that starts with the word "I".
    Sentences are delimited by '.', '?' or '!'.
   
    For example:
    >>> is_bored("Hello world")
    0
    >>> is_bored("The sky is blue. The sun is shining. I love this weather")
    1
    """


Your company's goal is to complete the rest of it with 100% accuracy. The task id is: "HumanEval/91"

You MUST use exactly <talk goal="Name">TalkContent</talk> format to talk to others, like:

<talk goal="Alice">Alice, I have completed 'a.txt'. Please check it for your work and talk to me again if needed. </talk>. 

Otherwise, they will not receive your message, and the conversation will terminate. "Name" should only be ONE specific employee. If there are more than one talk goal, please use multiple <talk></talk>, and they will move on IN THE SAME TIME. 

You must use function calls in JSON for file operations.

Leave a remarkable TODO wherever there is an unfinished task. Please keep updating your TODO list until everything is done. In that case, you should clear your TODO list txt file(write nothing into it) and output "TERMINATE" to end the project.
'''