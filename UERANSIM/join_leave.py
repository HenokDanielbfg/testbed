import subprocess
import time
from datetime import datetime
import signal
import sys
import threading

def read_output(pipe, prefix):
    """
    Continuously read and print output from a process pipe
    """
    try:
        for line in iter(pipe.readline, ''):
            # Strip whitespace
            line = line.strip()
            if line:
                print(f"{prefix}: {line}")
    except Exception as e:
        print(f"Error reading {prefix} output: {e}")
    finally:
        pipe.close()

def run_delayed_commands():
    # First command to run as a background process
    ue_config_command = "sudo build/nr-ue -c config/free5gc-ue.yaml"
    
    # Second command to run after 30 minutes
    deregister_command = "./build/nr-cli imsi-208930000000001 --exec \"deregister switch-off\""
    
    # Process to track the UE configuration
    ue_process = None
    
    try:
        # Start the UE configuration command as a background process
        print("Starting UE configuration...")
        ue_process = subprocess.Popen(ue_config_command, shell=True, 
                                      stdout=subprocess.PIPE, 
                                      stderr=subprocess.PIPE,
                                      universal_newlines=True)
        
        # Create threads to read stdout and stderr
        stdout_thread = threading.Thread(target=read_output, 
                                         args=(ue_process.stdout, "UE STDOUT"), 
                                         daemon=True)
        stderr_thread = threading.Thread(target=read_output, 
                                         args=(ue_process.stderr, "UE STDERR"), 
                                         daemon=True)
        
        # Start the logging threads
        stdout_thread.start()
        stderr_thread.start()
        
        # Print start time
        start_time = datetime.now()
        print(f"Script started at: {start_time}")
        print(f"UE configuration running with PID: {ue_process.pid}")
        
        # Wait for 30 minutes while UE process continues
        print("Waiting 30 minutes before executing deregistration command...")
        time.sleep(30 * 60)  # 30 minutes * 60 seconds
        
        # Print deregistration execution time
        deregister_time = datetime.now()
        print(f"Executing deregistration command at: {deregister_time}")
        
        # Run the deregistration command
        deregister_result = subprocess.run(deregister_command, shell=True, check=True, 
                                           stdout=subprocess.PIPE, 
                                           stderr=subprocess.PIPE, 
                                           text=True)
        
        # Print deregistration command output
        if deregister_result.stdout:
            print("Deregistration Command Output:")
            print(deregister_result.stdout)
        
        if deregister_result.stderr:
            print("Deregistration Command Error Output:")
            print(deregister_result.stderr)
        
        print("Deregistration command executed successfully.")
    
    except subprocess.CalledProcessError as e:
        print(f"Command failed with error: {e}")
        print(f"Error output: {e.stderr}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        # Ensure UE process is terminated when script exits
        if ue_process and ue_process.poll() is None:
            print("Terminating UE configuration process...")
            try:
                # First try to terminate gracefully
                ue_process.terminate()
                # Wait a short time for process to end
                time.sleep(2)
                # If still running, kill the process
                if ue_process.poll() is None:
                    ue_process.kill()
            except Exception as e:
                print(f"Error terminating UE process: {e}")

def signal_handler(sig, frame):
    print("\nScript interrupted. Cleaning up...")
    sys.exit(0)

if __name__ == "__main__":
    # Handle interrupt signals to ensure clean process termination
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    run_delayed_commands()









# from datetime import datetime
# import subprocess
# import random
# import time
# import threading
# import os
# import yaml
# import logging

# # Configure logging
# logging.basicConfig(
#     level=logging.INFO, 
#     format='%(asctime)s - %(levelname)s - %(message)s'
# )

# class UESimulator:
#     def __init__(self, ue_config_dir, num_ues):
#         """
#         Initialize UE Simulator with thread-safe mechanisms
        
#         :param ue_config_dir: Directory containing UE configuration files
#         :param num_ues: Number of UEs to simulate
#         """
#         self.ue_config_dir = ue_config_dir
#         self.num_ues = num_ues
        
#         # Thread-safe data structures
#         self.active_ues = {}
#         self.ue_lock = threading.Lock()  # Lock for UE dictionary
#         self.counter_lock = threading.Lock()  # Lock for counter
#         self.counter = 0
        
#         # Optional: Add a thread-safe event for coordinating threads
#         self.stop_event = threading.Event()

#     def increment_counter(self):
#         """Thread-safe counter increment"""
#         with self.counter_lock:
#             self.counter += 1
#             return self.counter

#     def decrement_counter(self):
#         """Thread-safe counter decrement"""
#         with self.counter_lock:
#             self.counter = max(0, self.counter - 1)
#             return self.counter

#     def start_ue(self, config_file):
#         """
#         Start a UE process with thread-safe management
        
#         :param config_file: Path to UE configuration file
#         :return: Config file path if successful, None otherwise
#         """
#         try:
#             # Load configuration
#             with open(config_file, 'r') as f:
#                 config = yaml.safe_load(f)
#             imsi = str(config['supi'])

#             # Prepare UE start command
#             cmd = [
#                 'build/nr-ue', 
#                 '/home/henokbfg/UERANSIM',
#                 '-c', config_file
#             ]

#             # Start UE process
#             ue_process = subprocess.Popen(
#                 cmd, 
#                 stdout=subprocess.PIPE, 
#                 stderr=subprocess.PIPE
#             )

#             # Thread-safe addition to active UEs
#             with self.ue_lock:
#                 self.active_ues[config_file] = {
#                     'process': ue_process,
#                     'imsi': imsi
#                 }
#                 current_count = self.increment_counter()
#                 logging.info(f"UE Started: {imsi}, Total Active UEs: {current_count}")

#             return config_file

#         except Exception as e:
#             logging.error(f"Failed to start UE {config_file}: {e}")
#             return None

#     def stop_ue(self, config_file):
#         """
#         Stop a UE process with thread-safe management
        
#         :param config_file: Path to UE configuration file
#         """
#         try:
#             # Thread-safe retrieval of UE info
#             with self.ue_lock:
#                 ue_info = self.active_ues.get(config_file)
#                 if not ue_info:
#                     logging.warning(f"No active UE found for {config_file}")
#                     return

#                 imsi = ue_info['imsi']

#             # Attempt deregistration
#             deregister_cmd = [
#                 './build/nr-cli', 
#                 imsi, 
#                 '--exec', 
#                 "deregister switch-off"
#             ]

#             try:
#                 subprocess.run(
#                     deregister_cmd, 
#                     stdout=subprocess.PIPE, 
#                     stderr=subprocess.PIPE, 
#                     text=True,
#                     check=True,
#                     timeout=10  # Added timeout
#                 )
#             except subprocess.CalledProcessError as e:
#                 logging.error(f"Deregistration error for {imsi}: {e.stderr}")
#             except subprocess.TimeoutExpired:
#                 logging.warning(f"Deregistration timed out for {imsi}")

#             # Thread-safe removal from active UEs
#             with self.ue_lock:
#                 if config_file in self.active_ues:
#                     del self.active_ues[config_file]
#                     current_count = self.decrement_counter()
#                     logging.info(f"UE Stopped: {imsi}, Total Active UEs: {current_count}")

#         except Exception as e:
#             logging.error(f"Error stopping UE {config_file}: {e}")

#     def simulate_ue_lifecycle(self, config_file):
#         """
#         Simulate UE lifecycle with enhanced stability
        
#         :param config_file: Path to UE configuration file
#         """
#         consecutive_failures = 0
#         max_consecutive_failures = 5  # Prevent infinite loops on persistent errors

#         while not self.stop_event.is_set():
#             try:
#                 # Random delay before registration
#                 time.sleep(random.uniform(0.1, 1.0))
                
#                 # More variable connection times
#                 connection_time = random.uniform(900, 1000)
#                 disconnection_time = random.uniform(100, 200)
                
#                 # Start UE with explicit success check
#                 start_result = self.start_ue(config_file)
#                 if not start_result:
#                     consecutive_failures += 1
#                     if consecutive_failures > max_consecutive_failures:
#                         logging.error(f"Repeated failures starting UE {config_file}. Stopping.")
#                         break
#                     continue
                
#                 # Reset failure counter on successful start
#                 consecutive_failures = 0
                
#                 logging.info(f"UE {config_file} connected for {connection_time:.2f} seconds")
#                 time.sleep(connection_time)
                
#                 # Stop UE with additional safeguards
#                 self.stop_ue(config_file)
                
#                 logging.info(f"UE {config_file} disconnected for {disconnection_time:.2f} seconds")
#                 time.sleep(disconnection_time)
            
#             except Exception as e:
#                 logging.error(f"Lifecycle error for {config_file}: {e}")
#                 consecutive_failures += 1
#                 if consecutive_failures > max_consecutive_failures:
#                     logging.error(f"Too many consecutive failures for {config_file}. Stopping.")
#                     break

#     def run_simulation(self):
#         """
#         Run UE simulation across multiple threads
#         """
#         # Identify UE configuration files
#         ue_configs = [
#             os.path.join(self.ue_config_dir, f) 
#             for f in os.listdir(self.ue_config_dir) 
#             if f.endswith('.yaml')
#         ]
        
#         # Limit to specified number of UEs
#         ue_configs = ue_configs[:self.num_ues]
        
#         # Create and start threads
#         threads = []
#         for config_file in ue_configs:
#             thread = threading.Thread(
#                 target=self.simulate_ue_lifecycle, 
#                 args=(config_file,)
#             )
#             thread.start()
#             threads.append(thread)
#             time.sleep(8)  # Stagger thread starts
        
#         try:
#             # Optional: Keep main thread alive
#             while True:
#                 time.sleep(60)
#                 # Periodic state validation can be added here
#         except KeyboardInterrupt:
#             logging.info("Stopping simulation...")
#             self.stop_event.set()  # Signal threads to stop
        
#         # Wait for all threads to complete
#         for thread in threads:
#             thread.join()

# # Main execution
# if __name__ == "__main__":
#     simulator = UESimulator(
#         ue_config_dir='/home/henokbfg/UERANSIM/config/customConfigs',
#         num_ues=3
#     )
#     simulator.run_simulation()

































# from datetime import datetime
# import subprocess
# import random
# import time
# import threading
# import os
# import yaml
# import logging

# # Configure logging
# logging.basicConfig(
#     level=logging.INFO, 
#     format='%(asctime)s - %(levelname)s - %(message)s'
# )

# class UESimulator:
#     def __init__(self, ue_config_dir, num_ues):
#         """
#         Initialize UE Simulator with thread-safe mechanisms
        
#         :param ue_config_dir: Directory containing UE configuration files
#         :param num_ues: Number of UEs to simulate
#         """
#         self.ue_config_dir = ue_config_dir
#         self.num_ues = num_ues
        
#         # Thread-safe data structures
#         self.active_ues = {}
#         self.ue_lock = threading.Lock()  # Lock for UE dictionary
#         self.counter_lock = threading.Lock()  # Lock for counter
#         self.counter = 0
        
#         # Optional: Add a thread-safe event for coordinating threads
#         self.stop_event = threading.Event()

#     def increment_counter(self):
#         """Thread-safe counter increment"""
#         with self.counter_lock:
#             self.counter += 1
#             return self.counter

#     def decrement_counter(self):
#         """Thread-safe counter decrement"""
#         with self.counter_lock:
#             self.counter = max(0, self.counter - 1)
#             return self.counter

#     def start_ue(self, config_file):
#         """
#         Start a UE process with thread-safe management
        
#         :param config_file: Path to UE configuration file
#         :return: Config file path if successful, None otherwise
#         """
#         try:
#             # Load configuration
#             with open(config_file, 'r') as f:
#                 config = yaml.safe_load(f)
#             imsi = str(config['supi'])

#             # Prepare UE start command
#             cmd = [
#                 'build/nr-ue', 
#                 '/home/henokbfg/UERANSIM',
#                 '-c', config_file
#             ]

#             # Start UE process
#             ue_process = subprocess.Popen(
#                 cmd, 
#                 stdout=subprocess.PIPE, 
#                 stderr=subprocess.PIPE
#             )

#             # Thread-safe addition to active UEs
#             with self.ue_lock:
#                 self.active_ues[config_file] = {
#                     'process': ue_process,
#                     'imsi': imsi
#                 }
#                 current_count = self.increment_counter()
#                 logging.info(f"UE Started: {imsi}, Total Active UEs: {current_count}")

#             return config_file

#         except Exception as e:
#             logging.error(f"Failed to start UE {config_file}: {e}")
#             return None

#     def stop_ue(self, config_file):
#         """
#         Stop a UE process with thread-safe management
        
#         :param config_file: Path to UE configuration file
#         """
#         try:
#             # Thread-safe retrieval of UE info
#             with self.ue_lock:
#                 ue_info = self.active_ues.get(config_file)
#                 if not ue_info:
#                     logging.warning(f"No active UE found for {config_file}")
#                     return

#                 imsi = ue_info['imsi']

#             # Attempt deregistration
#             deregister_cmd = [
#                 './build/nr-cli', 
#                 imsi, 
#                 '--exec', 
#                 "deregister switch-off"
#             ]

#             try:
#                 subprocess.run(
#                     deregister_cmd, 
#                     stdout=subprocess.PIPE, 
#                     stderr=subprocess.PIPE, 
#                     text=True,
#                     check=True,
#                     timeout=10  # Added timeout
#                 )
#             except subprocess.CalledProcessError as e:
#                 logging.error(f"Deregistration error for {imsi}: {e.stderr}")
#             except subprocess.TimeoutExpired:
#                 logging.warning(f"Deregistration timed out for {imsi}")

#             # Thread-safe removal from active UEs
#             with self.ue_lock:
#                 if config_file in self.active_ues:
#                     del self.active_ues[config_file]
#                     current_count = self.decrement_counter()
#                     logging.info(f"UE Stopped: {imsi}, Total Active UEs: {current_count}")

#         except Exception as e:
#             logging.error(f"Error stopping UE {config_file}: {e}")

#     def simulate_ue_lifecycle(self, config_file):
#         """
#         Simulate UE lifecycle with random connection/disconnection
        
#         :param config_file: Path to UE configuration file
#         """
#         while not self.stop_event.is_set():
#             try:
#                 # Random delay before registration
#                 time.sleep(random.uniform(0.1, 1.0))
                
#                 # Randomize connection parameters
#                 connection_time = random.uniform(100, 150)
#                 disconnection_time = random.uniform(100, 150)
                
#                 # Start UE
#                 if self.start_ue(config_file):
#                     logging.info(f"UE {config_file} connected")
#                     time.sleep(connection_time)
                
#                 # Stop UE
#                 self.stop_ue(config_file)
#                 logging.info(f"UE {config_file} disconnected")
                
#                 time.sleep(disconnection_time)
            
#             except Exception as e:
#                 logging.error(f"Lifecycle error for {config_file}: {e}")

#     def run_simulation(self):
#         """
#         Run UE simulation across multiple threads
#         """
#         # Identify UE configuration files
#         ue_configs = [
#             os.path.join(self.ue_config_dir, f) 
#             for f in os.listdir(self.ue_config_dir) 
#             if f.endswith('.yaml')
#         ]
        
#         # Limit to specified number of UEs
#         ue_configs = ue_configs[:self.num_ues]
        
#         # Create and start threads
#         threads = []
#         for config_file in ue_configs:
#             thread = threading.Thread(
#                 target=self.simulate_ue_lifecycle, 
#                 args=(config_file,)
#             )
#             thread.start()
#             threads.append(thread)
#             time.sleep(8)  # Stagger thread starts
        
#         try:
#             # Optional: Keep main thread alive
#             while True:
#                 time.sleep(60)
#                 # Periodic state validation can be added here
#         except KeyboardInterrupt:
#             logging.info("Stopping simulation...")
#             self.stop_event.set()  # Signal threads to stop
        
#         # Wait for all threads to complete
#         for thread in threads:
#             thread.join()

# # Main execution
# if __name__ == "__main__":
#     simulator = UESimulator(
#         ue_config_dir='/home/henokbfg/UERANSIM/config/customConfigs',
#         num_ues=3
#     )
#     simulator.run_simulation()




























# from datetime import datetime
# import subprocess
# import random
# import time
# import threading
# import os
# import yaml



# class UESimulator:

#     def __init__(self, ue_config_dir, num_ues):
#         self.ue_config_dir = ue_config_dir
#         self.num_ues = num_ues
#         #self.gnb_interface = gnb_interface
#         self.active_ues = {}
#         self.lock = threading.Lock()  # Add a lock
#         self.counter = 0
    
#     def start_ue(self, config_file):
#         with self.lock:
#             # Direct translation of your terminal command
#             cmd = [
#                 'build/nr-ue',  '/home/henokbfg/UERANSIM', # Path to UERANSIM UE executable
#                 '-c', config_file,
#                 # '-i', self.gnb_interface
#             ]
#             # Start the UE process
#             self.counter+=1
#             ue_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#                 # Store process and IMSI for later deregistration
#             # Load config to extract IMSI
#             print(f"current count: {self.counter}")

#             with open(config_file, 'r') as f:
#                 config = yaml.safe_load(f) 
#             imsi = f"{config['supi']}"
#             self.active_ues[config_file] = {
#                 'process': ue_process,
#                 'imsi': imsi
#             }
#             return config_file
    
#     def stop_ue(self, config_file):
#         with self.lock:
#             # Retrieve stored UE information

#             ue_info = self.active_ues.get(config_file)
#             if not ue_info:
#                 print(f"No active UE found for {config_file}")
#                 return
            
#             # Deregister UE using CLI
#             # deregister_cmd = [
#             #     './build/nr-cli', 
#             #     ue_info['imsi'], 
#             #     '--exec', "deregister switch-off"
#             # ]
#             # deregister_cmd = ['./build/nr-cli imsi-208930000000004 --exec "deregister switch-off"']
#             deregister_cmd =['./build/nr-cli',  ue_info['imsi'],  '--exec', "deregister switch-off"]



#             try:
#                 deregister_cmd = ['./build/nr-cli', ue_info['imsi'], '--exec', "deregister switch-off"]
#                 result = subprocess.run(
#                     deregister_cmd, 
#                     stdout=subprocess.PIPE, 
#                     stderr=subprocess.PIPE, 
#                     text=True,  # Decode output as text
#                     check=True  # Raise exception if the command fails
#                 )
#                 print(f"Deregister stdout: {result.stdout}")
#                 self.counter+=1

#                 print(f"current count: {self.counter}")
#             except subprocess.CalledProcessError as e:
#                 print(f"Error during deregistration: {e.stderr}")
#             except Exception as e:
#                 print(f"Unexpected error: {e}")





            
#             # try:
                
#             #     # Execute deregistration command
#             #     deregister_process = subprocess.Popen(
#             #         deregister_cmd, 
#             #         stdout=subprocess.PIPE, 
#             #         stderr=subprocess.PIPE
#             #     )
#             #     deregister_process.wait(timeout=100)  # Wait for deregistration to complete
#             #     # Capture output for debugging
#             #     # stdout, stderr = deregister_process.communicate(timeout=80)
#             #     # print(f"Deregister stdout: {stdout.decode('utf-8')}")
#             #     # print(f"Deregister stderr: {stderr.decode('utf-8')}")
#             #     #Terminate the UE process
#             #     ue_info['process'].terminate()
#             #     ue_info['process'].wait(timeout=5)
                
#             #     # Remove from active UEs
#             #     del self.active_ues[config_file]
                
#             #     # print(f"UE {ue_info['imsi']} deregistered and stopped")
            
#             # except subprocess.TimeoutExpired:
#             #     print(f"Timeout during deregistration of {ue_info['imsi']}")
#             #     # stdout, stderr = deregister_process.communicate(timeout=80)

#             #     # print(f"Deregister stdout: {stdout.decode('utf-8')}")
#             #     # print(f"Deregister stderr: {stderr.decode('utf-8')}")
#             #     # Force kill if deregistration hangs
#             #     ue_info['process'].kill()
#             # except Exception as e:
#             #     print(f"Error stopping UE {ue_info['imsi']}: {e}")
    
#     def simulate_ue_lifecycle(self, config_file):
#         while True:

#             # Add a small random delay before registration to prevent simultaneous requests
#             time.sleep(random.uniform(0.1, 1.0))  # Random delay between 0.1 and 1 second
        
#             # Randomize connection duration
#             connection_time = random.uniform(200, 200)  # 30-300 seconds connected
#             disconnection_time = random.uniform(200, 200)  # 10-120 seconds disconnected
            
#             try:
#                 # Start UE
#                 self.start_ue(config_file)
#                 # print(f"UE {config_file} connected")
#                 print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] UE {config_file} connected")
#                 time.sleep(connection_time)
                
#                 # Stop UE
#                 self.stop_ue(config_file)
#                 # print(f"UE {config_file} disconnected")
#                 print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] UE {config_file} disconnected")
#                 time.sleep(disconnection_time)
            
#             except Exception as e:
#                 print(f"Error with UE {config_file}: {e}")
    
#     def run_simulation(self):
#         # Get all UE config files

#         ue_configs = [
#             os.path.join(self.ue_config_dir, f) 
#             for f in os.listdir(self.ue_config_dir) 
#             if f.endswith('.yaml')  # Assuming YAML configs
#         ]
        
#         # Limit to specified number of UEs
#         ue_configs = ue_configs[:self.num_ues]
        
#         # Create threads for each UE
#         threads = []
#         for config_file in ue_configs:
#             thread = threading.Thread(target=self.simulate_ue_lifecycle, args=(config_file,))
#             thread.start()
#             time.sleep(8)
#             threads.append(thread)
#             time.sleep(8)

        
#         # Wait for all threads
#         for thread in threads:
#             time.sleep(8)
#             thread.join()

# # Example usage
# simulator = UESimulator(
#     ue_config_dir='/home/henokbfg/UERANSIM/config/customConfigs',
#     num_ues=3,  # Number of UEs to simulate
#     # gnb_interface='your-gnb-interface'
# )
# simulator.run_simulation()
