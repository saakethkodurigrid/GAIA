from locust import HttpUser, task, between
import random
import json
import time

class GAIAUser(HttpUser):
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Called when a user starts - simulate login"""
        self.candidate_id = f"test-candidate-{self.environment.runner.user_count}"
        self.test_session_id = f"session-{random.randint(1000, 9999)}"
        print(f"[User {self.environment.runner.user_count}] Started with candidate_id: {self.candidate_id}")
        
    @task(3)
    def view_test_overview(self):
        """View test overview page"""
        self.client.get(f"/api/v1/candidate/{self.candidate_id}/test/overview")
    
    @task(2)
    def get_test_status(self):
        """Get test status"""
        self.client.get(f"/api/v1/candidate/{self.candidate_id}/test/status")
    
    @task(2)
    def heartbeat(self):
        """Send heartbeat to keep session alive"""
        self.client.post(
            f"/api/v1/candidate/{self.candidate_id}/test/heartbeat",
            json={"test_session_id": self.test_session_id}
        )
    
    @task(2)
    def submit_mcq_answer(self):
        """Submit MCQ answer"""
        self.client.post(
            f"/api/v1/candidate/{self.candidate_id}/test/mcq/submit",
            json={
                "question_id": random.randint(1, 50),
                "selected_option": random.choice(["A", "B", "C", "D"]),
                "test_session_id": self.test_session_id
            }
        )
    
    @task(1)
    def submit_code(self):
        """Submit code solution"""
        self.client.post(
            f"/api/v1/candidate/{self.candidate_id}/test/coding/submit",
            json={
                "question_id": random.randint(1, 10),
                "code": "def solution():\n    return True",
                "language": "python",
                "test_session_id": self.test_session_id
            }
        )
    
    @task(1)
    def get_system_design_question(self):
        """Get system design question"""
        self.client.get(f"/api/v1/candidate/{self.candidate_id}/test/system-design/question")

