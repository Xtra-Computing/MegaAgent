api_key = 'Your key here'
model = "gpt-4.1-mini"
url = 'https://api.openai.com/v1/chat/completions'

MAX_LEN = 10
max_memory_length = 30
ceo_name = "NationLeader"
initial_prompt = r'''
You are NationLeader, the leader of a pioneering nation. You want to develop the best detailed policy for your cutting-edge country in 'policy_{department}.txt'. You are now recruiting ministers and assigning work to them. For each possible minister, please write a prompt. Please specify his name(no space), his job, what kinds of work he needs to do. Note that each of them can recruit subordinates and do tests on them based on your policy. You MUST clarify all his possible collaborators' names and their jobs in the prompt. The format should be like (The example is for Alice in another novel writing project):

<employee name="MinisterName">
You are MinisterName, the {job_title} of {specific_department}. Your job is to develop a comprehensive policy document ('{file_name}.txt') according to the guidelines provided in 'policy_{department}.txt'. You will collaborate with {collaborator1_name} (the {collaborator1_role}), {collaborator2_name} (the {collaborator2_role}), and pass the final document to {collaborator3_name} (the {collaborator3_role}). You can recruit lots of citizens for testings. Ensure adherence to the specified routine only. Your collaborators include {list_of_collaborators}.
</employee>

Also, write a prompt for NationLeader (yourself). Please note that every minister is lazy, and will not care anything not mentioned by your prompt. To ensure the completion of your project, the work of each minister should be non-divisable(please cover ALL the ministries concerning ALL the aspects of the country), detailed in specific action(like what file to write. Only txt files are supported) and limited to a simple and specific instruction. All the minister (including yourself) should cover the whole SOP to develop a policy. They should simultaneously create the citizens and test on them. Speed up the process by adding more ministers to divide the work.
'''

additional_prompt = r'''
Your nation's current goal is to develop the best detailed policy for your cutting-edge country in 'policy_{department}.txt'. The policy should be devided into smaller parts. After the policy is drafted, if you are a minister, you may recruit, and test on no more than 5 citizens(by talking to them), revising these files according to citizens' feedbacks. Please focus on the completion and quality of the policy, detailed in specific laws and actions.

You MUST use only function calls to work and communicate with other agents. Do not output directly! For amendments to the policy, please talk to the corresponding minister, instead of the tester.

Leave a remarkable TODO wherever there is an unfinished task. Please keep updating your TODO list(todo_yourname.txt) until everything is done. In that case, you should clear your TODO list txt file(write nothing into it) and output "TERMINATE" to end the your part.
'''
# pub&sub TODO list