#!/usr/bin/env python3
"""
Simple load test script for GAIA platform
Simulates multiple users taking tests simultaneously
"""

import requests
import threading
import time
import random
from datetime import datetime
from typing import Dict, List

BASE_URL = "https://gaia-backend.politefield-9abbbc93.eastus.azurecontainerapps.io"
NUM_USERS = 10
TEST_DURATION = 3 * 60 * 60  # 3 hours in seconds

class UserSimulator:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.candidate_id = f"test-candidate-{user_id}"
        self.test_session_id = f"session-{random.randint(1000, 9999)}"
        self.request_count = 0
        self.error_count = 0
        self.start_time = None
        
    def log(self, message: str):
        """Log with user ID"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [User {self.user_id}] {message}")
    
    def make_request(self, method: str, endpoint: str, **kwargs):
        """Make HTTP request with error handling"""
        try:
            url = f"{BASE_URL}{endpoint}"
            response = requests.request(method, url, timeout=10, **kwargs)
            self.request_count += 1
            
            if response.status_code >= 400:
                self.error_count += 1
                self.log(f"Error {response.status_code}: {endpoint}")
            
            return response
        except Exception as e:
            self.error_count += 1
            self.log(f"Exception: {e}")
            return None
    
    def simulate_test(self):
        """Simulate a user taking a test"""
        self.start_time = time.time()
        self.log(f"Started test simulation (candidate_id: {self.candidate_id})")
        
        while time.time() - self.start_time < TEST_DURATION:
            try:
                # Heartbeat (every 2 minutes)
                self.make_request(
                    "POST",
                    f"/api/v1/candidate/{self.candidate_id}/test/heartbeat",
                    json={"test_session_id": self.test_session_id}
                )
                time.sleep(120)  # 2 minutes
                
                # Get test status
                self.make_request(
                    "GET",
                    f"/api/v1/candidate/{self.candidate_id}/test/status"
                )
                time.sleep(random.uniform(5, 15))
                
                # Submit MCQ answer (every 30 seconds)
                self.make_request(
                    "POST",
                    f"/api/v1/candidate/{self.candidate_id}/test/mcq/submit",
                    json={
                        "question_id": random.randint(1, 50),
                        "selected_option": random.choice(["A", "B", "C", "D"]),
                        "test_session_id": self.test_session_id
                    }
                )
                time.sleep(30)
                
                # Get test overview (occasionally)
                if random.random() < 0.1:  # 10% chance
                    self.make_request(
                        "GET",
                        f"/api/v1/candidate/{self.candidate_id}/test/overview"
                    )
                    time.sleep(random.uniform(10, 30))
                
            except KeyboardInterrupt:
                self.log("Test interrupted by user")
                break
            except Exception as e:
                self.log(f"Unexpected error: {e}")
                time.sleep(5)
        
        elapsed = time.time() - self.start_time
        self.log(f"Completed. Requests: {self.request_count}, Errors: {self.error_count}, Duration: {elapsed/60:.2f} min")

def run_load_test():
    """Run load test with multiple users"""
    print(f"=" * 60)
    print(f"GAIA Load Test - {NUM_USERS} Users for 3 Hours")
    print(f"Backend URL: {BASE_URL}")
    print(f"=" * 60)
    
    simulators: List[UserSimulator] = []
    threads: List[threading.Thread] = []
    
    # Create simulators
    for i in range(1, NUM_USERS + 1):
        simulator = UserSimulator(i)
        simulators.append(simulator)
    
    # Start all user threads
    start_time = time.time()
    for simulator in simulators:
        thread = threading.Thread(target=simulator.simulate_test, daemon=True)
        thread.start()
        threads.append(thread)
        time.sleep(2)  # Stagger user starts
    
    print(f"\nAll {NUM_USERS} users started. Test running for 3 hours...")
    print("Press Ctrl+C to stop early\n")
    
    try:
        # Wait for all threads (or until interrupted)
        for thread in threads:
            thread.join(timeout=TEST_DURATION + 60)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    
    # Print summary
    elapsed = time.time() - start_time
    total_requests = sum(s.request_count for s in simulators)
    total_errors = sum(s.error_count for s in simulators)
    
    print(f"\n{'=' * 60}")
    print(f"LOAD TEST SUMMARY")
    print(f"{'=' * 60}")
    print(f"Users: {NUM_USERS}")
    print(f"Duration: {elapsed/60:.2f} minutes")
    print(f"Total Requests: {total_requests}")
    print(f"Total Errors: {total_errors}")
    print(f"Error Rate: {(total_errors/total_requests*100):.2f}%" if total_requests > 0 else "N/A")
    print(f"Requests per User: {total_requests/NUM_USERS:.1f}")
    print(f"{'=' * 60}\n")
    
    # Per-user summary
    print("Per-User Summary:")
    for simulator in simulators:
        print(f"  User {simulator.user_id}: {simulator.request_count} requests, {simulator.error_count} errors")

if __name__ == "__main__":
    run_load_test()

