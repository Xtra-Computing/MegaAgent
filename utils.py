import os
import threading
import subprocess
import sys
from llm import written_files
import time

sys.path.insert(0, os.path.abspath('files'))
# Initialize global lock
git_lock = threading.Lock()

# Check and initialize Git repository, and switch to a new branch
def init_git_repo():
    if not os.path.exists('files/.git'):
        os.makedirs('files', exist_ok=True)
        subprocess.run(['git', 'init', 'files'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(['git','config','--global','core.autocrlf','false'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with open('files/.gitkeep', 'w') as f:
            f.write('Initial commit')
        subprocess.run(['git', '-C', 'files', 'add', '.gitkeep'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(['git', '-C', 'files', 'commit', '-m', 'Initial commit'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(['git', '-C', 'files', 'checkout', '-b', 'files_branch'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        # If the Git repository already exists, check and switch to the files_branch branch
        current_branch = subprocess.check_output(['git', '-C', 'files', 'branch', '--show-current'], text=True).strip()
        if current_branch != 'files_branch':
            # If the files_branch branch does not exist, create it
            branches = subprocess.check_output(['git', '-C', 'files', 'branch'], text=True).strip().split('\n')
            if 'files_branch' not in [branch.strip() for branch in branches]:
                subprocess.run(['git', '-C', 'files', 'checkout', '-b', 'files_branch'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.run(['git', '-C', 'files', 'checkout', '-f', 'files_branch'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Add Git configuration to avoid editor issues during merge conflicts
    subprocess.run(['git', 'config', '--global', 'merge.conflictstyle', 'diff3'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

init_git_repo()

def enqueue_output(out, queue, ready_event):
    while True:
        char = out.read(1)  # Read one character at a time
        if char == '':
            break
        queue.append(char)
        ready_event.set()
    out.close()

def start_interactive_subprocess(program_path):
    program_path = os.path.join('files', program_path)
    if not os.path.exists(program_path):
        raise FileNotFoundError(f"File {program_path} not found.")
    
    process = subprocess.Popen(
        [sys.executable, program_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,  # Unbuffered, real-time output
        text=True
    )
    
    # List to store output characters
    output_chars = []
    output_ready = threading.Event()
    
    # Start a thread to capture output
    output_thread = threading.Thread(target=enqueue_output, args=(process.stdout, output_chars, output_ready))
    output_thread.start()
    time.sleep(0.5)
    if process.poll() is not None:
        err = process.stderr.read()
        if 'Traceback' in err:
            raise Exception(err)
        elif err!='':
            return f"Program exited with output:{err}", None
    if not output_ready.wait(timeout=5):
        if process.poll() is not None:
            err = process.stderr.read()
            if 'Traceback' in err:
                raise Exception(err)
            else:
                return f"Program exited with output:{err}", None
        process.terminate()
        process.wait()
        output_thread.join()
        raise Exception("Timeout: 5 seconds elapsed without any output. Please ensure the program can terminate within 5 seconds.")
    time.sleep(0.5)
    result = ''.join(output_chars)
    output_chars.clear()
    output_ready.clear()
    if len(result) > 1000:
        result = result[:500] + '\n... (truncated) ...\n' + result[-500:]
    return result, (process, output_chars, output_ready)

def send_input(user_input, package):
    process, output_chars, output_ready = package
    if not process or process.poll() is not None:
        raise Exception("The subprocess has been terminated.")
    process.stdin.write(user_input + '\n')
    process.stdin.flush()
    time.sleep(0.5)
    if process.poll() is not None:
        err = process.stderr.read()
        if 'Traceback' in err:
            raise Exception(err)
    if not output_ready.wait(timeout=5):
        if process.poll() is not None:
            err = process.stderr.read()
            if 'Traceback' in err:
                raise Exception(err)
            else:
                return "Program exited with no output.", None
        process.terminate()
        process.wait()
        raise Exception("Timeout: 5 seconds elapsed without any output.")
    time.sleep(1)
    result = ''.join(output_chars)
    output_chars.clear()
    output_ready.clear()
    return result, (process, output_chars, output_ready)

def exec_python_file(filename):
    result = None
    try:
        with git_lock:
            result = subprocess.run(
                [sys.executable, os.path.join('files', filename)],
                capture_output=True,
                text=True,
                timeout=6,
                check=True
            )
        return result.stdout
    except subprocess.TimeoutExpired:
        return "Error: Execution timed out. Maybe your program has entered an infinite loop, or it is waiting for input? (Remember this environment does not support user input. Please write another test program to avoid user input in this case.)"
    except subprocess.CalledProcessError as e:
        if e.stderr:
            return f"Error: {e.stderr}"
        else:
            return f"Error: {result.stderr}"
    except Exception as e:
        return f"Error: {str(e)}"

def read_file(filename):
    try:
        with git_lock:
            # Get the latest commit hash
            latest_commit = subprocess.check_output(['git', '-C', 'files', 'rev-parse', 'HEAD'], text=True).strip()
        
            with open('files/' + filename, 'r') as f:
                content = f.read()
        
        return content, latest_commit
    except subprocess.CalledProcessError:
        return "No commits yet.", None
    except Exception as e:
        return str(e), None
    
def git_commit(commit_message):
    result = subprocess.run(['git', '-C', 'files', 'commit', '-a', '-m', commit_message], capture_output=True, text=True)

def write_file(filename, content, overwrite=False, base_commit_hash= None, agent_name=''):
    if base_commit_hash is None or base_commit_hash == '':
        overwrite = False
    with git_lock, open('git.log', 'a') as git_log:
        try:
            if overwrite == False:
                base_commit_hash = subprocess.check_output(['git', '-C', 'files', 'rev-parse', 'HEAD'], text=True).strip()
            file_path = 'files/' + filename
            # Ensure the current working directory is clean
            # subprocess.run(['git', '-C', 'files', 'stash'], check=True, stdout=git_log, stderr=git_log)
            
            # Roll back to the specified base_commit_hash
            subprocess.run(['git', '-C', 'files', 'checkout', base_commit_hash, '-f'], check=True, stdout=git_log, stderr=git_log)
            
            if os.path.exists(file_path) and not overwrite:
                latest_commit = subprocess.check_output(['git', '-C', 'files', 'rev-parse', 'HEAD'], text=True).strip()
        
                with open('files/' + filename, 'r') as f:
                    content = f.read()
                return f"Error: {filename} already exists or incorrect commit hash. Please use overwrite=True with correct base_commit_hash to overwrite it.\nCurrent content:\n{content}\nCurrent commit hash: {latest_commit}"

            with open(file_path, 'w') as f:
                f.write(content)
            time.sleep(0.2)
            # Commit changes
            while True:
                try:
                    result = subprocess.run(['git', '-C', 'files', 'add', filename], check=True, stdout=git_log, stderr=git_log)
                    if result.returncode == 0:
                        break
                    else:
                        time.sleep(0.1)
                        print(result)
                except subprocess.CalledProcessError:
                    time.sleep(0.1)
                    print("Error: add file failed")
                    # result = subprocess.run(['git', '-C', 'files', 'add', filename], capture_output=True, text=True)
            commit_message = f"Update {filename}"
            result = subprocess.run(['git', '-C', 'files', 'commit', '-a', '-m', commit_message], capture_output=True, text=True)
            new_commit_hash = subprocess.check_output(['git', '-C', 'files', 'rev-parse', 'HEAD'], text=True).strip()
            if new_commit_hash == base_commit_hash:
                return f"Warning: No changes made to {filename}. The current commit hash is {new_commit_hash}. Do you forget to modify the content?"
            # Switch back to the latest branch and merge new commits
            subprocess.run(['git', '-C', 'files', 'checkout', 'files_branch', '-f'], check=True, stdout=git_log, stderr=git_log)
            # subprocess.run(['git', '-C', 'files', 'merge', 'files_branch'], check=True, stdout=git_log, stderr=git_log)
            merge_result = subprocess.run(['git', '-C', 'files', 'merge', new_commit_hash], capture_output=True, text=True)
            
            if merge_result.returncode != 0:
                # Merge failed, roll back to the original state
                subprocess.run(['git', '-C', 'files', 'merge', '--abort'], check=True, stdout=git_log, stderr=git_log)
                # subprocess.run(['git', '-C', 'files', 'stash', 'pop'], check=True, stdout=git_log, stderr=git_log)
                latest_commit = subprocess.check_output(['git', '-C', 'files', 'rev-parse', 'HEAD'], text=True).strip()
                with open('files/' + filename, 'r') as f:
                    content = f.read()
                time.sleep(0.1)
                return f"Merge conflict. The current commit hash is {latest_commit}. The content of {filename} is:\n{content}"
            
            # # Merge successful, restore the original working directory state
            # try:
            #     subprocess.run(['git', '-C', 'files', 'stash', 'pop'], check=True, stdout=git_log, stderr=git_log)
            # except subprocess.CalledProcessError:
            #     pass  # Ignore errors with no stash entries
            base_commit_hash = subprocess.check_output(['git', '-C', 'files', 'rev-parse', 'HEAD'], text=True).strip()
            if agent_name in written_files:
                written_files[agent_name].add(filename)
            else:
                written_files[agent_name] = set([filename])
            # time.sleep(0.1)
        except subprocess.CalledProcessError as e:
            return f"Git error: Make sure your base_commit_hash is correct."
        except Exception as e:
            return str(e)
        return f"Successfully wrote to {filename}. The new commit hash is {base_commit_hash}"
    
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

# if __name__ == "__main__":
    # process = start_interactive_subprocess("main.py")
    # result = process.communicate()
    # print(result)
    # result = send_input(process, "1\n1\n")
    # print(result)
    # threads = []
    # filenames = [f"file{i}.txt" for i in range(1, 21)]
    # contents = [f"Content for file{i}" for i in range(1, 21)]

    # for filename, content in zip(filenames, contents):
    #     thread = threading.Thread(target=write_file, args=(filename, content))
    #     threads.append(thread)
    #     thread.start()

    # for thread in threads:
    #     thread.join()