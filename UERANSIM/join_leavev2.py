import random
import subprocess
import time
from datetime import datetime
import signal
import sys
import threading

class UEManager:
    def __init__(self, imsi_base, num_ues=3):
        """
        Initialize UE Manager
        :param imsi_base: Base IMSI number
        :param num_ues: Number of UEs to configure
        """
        self.imsi_base = imsi_base
        self.num_ues = num_ues
        self.ue_threads = {}  # Track threads by IMSI
        self.running = True

    def read_output(self, pipe, prefix):
        """
        Continuously read and print output from a process pipe
        """
        try:
            for line in iter(pipe.readline, ''):
                line = line.strip()
                if line:
                    print(f"{prefix}: {line}")
        except Exception as e:
            print(f"Error reading {prefix} output: {e}")
        finally:
            pipe.close()

    def manage_single_ue(self, imsi):
        """
        Manage the complete lifecycle of a single UE independently
        """
        while self.running:
            try:
                # # Random delay before registration
                # reg_delay = random.uniform(1500, 2000)
                # print(f"UE {imsi} will register in {reg_delay/60:.2f} minutes")
                # time.sleep(reg_delay)

                if not self.running:
                    break

                # Start UE configuration
                ue_config_command = f"sudo build/nr-ue -c config/customConfigs/free5gc-ue{imsi[-1]}.yaml"
                print(f"Starting UE configuration for IMSI {imsi}...")
                
                ue_process = subprocess.Popen(
                    ue_config_command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )

                # Set up output reading threads
                stdout_thread = threading.Thread(
                    target=self.read_output,
                    args=(ue_process.stdout, f"UE {imsi} STDOUT"),
                    daemon=True
                )
                stderr_thread = threading.Thread(
                    target=self.read_output,
                    args=(ue_process.stderr, f"UE {imsi} STDERR"),
                    daemon=True
                )
                stdout_thread.start()
                stderr_thread.start()

                print(f"UE configuration for IMSI {imsi} running with PID: {ue_process.pid}")

                # Random connection duration
                connection_time = random.uniform(1500, 9999)
                print(f"UE {imsi} will deregister in {connection_time/60:.2f} minutes")
                time.sleep(connection_time)

                if not self.running:
                    ue_process.terminate()
                    break

                # Deregister
                try:
                    print(f"Executing deregistration for IMSI {imsi}...")
                    deregister_command = f"./build/nr-cli imsi-{imsi} --exec \"deregister switch-off\""
                    deregister_result = subprocess.run(
                        deregister_command,
                        shell=True,
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    ue_process.terminate()

                    if deregister_result.stdout:
                        print(f"Deregistration Output for {imsi}:")
                        print(deregister_result.stdout)

                    if deregister_result.stderr:
                        print(f"Deregistration Error Output for {imsi}:")
                        print(deregister_result.stderr)

                except subprocess.CalledProcessError as e:
                    print(f"Deregistration failed for {imsi} with error: {e}")

                # Terminate UE process
                if ue_process.poll() is None:
                    ue_process.terminate()
                    time.sleep(2)
                    if ue_process.poll() is None:
                        ue_process.kill()

                        
                # Random delay before registration
                reg_delay = random.uniform(500, 4000)
                print(f"UE {imsi} will register in {reg_delay/60:.2f} minutes")
                time.sleep(reg_delay)
                # Small delay before next cycle
                # if self.running:
                #     time.sleep(10)

            except Exception as e:
                print(f"Error in UE {imsi} lifecycle: {e}")
                time.sleep(10)  # Wait before retry

    def run_continuous_cycles(self):
        """
        Run independent UE cycles continuously
        """
        try:
            # Start a thread for each UE
            for i in range(self.num_ues):
                imsi = f"{self.imsi_base}{i+1:03d}"
                ue_thread = threading.Thread(
                    target=self.manage_single_ue,
                    args=(imsi,),
                    daemon=True
                )
                self.ue_threads[imsi] = ue_thread
                ue_thread.start()

            # Keep main thread running
            while self.running:
                time.sleep(1)

        except KeyboardInterrupt:
            print("\nInterrupted by user. Shutting down...")
        finally:
            self.cleanup()

    def cleanup(self):
        """
        Clean up all running processes and threads
        """
        self.running = False
        # Wait for all threads to finish
        for imsi, thread in self.ue_threads.items():
            thread.join(timeout=5)
        self.ue_threads.clear()

def signal_handler(sig, frame):
    print("\nScript interrupted. Cleaning up...")
    sys.exit(0)

if __name__ == "__main__":
    # Handle interrupt signals
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Initialize and run UE Manager
    ue_manager = UEManager("208930000000", num_ues=3)
    ue_manager.run_continuous_cycles()

