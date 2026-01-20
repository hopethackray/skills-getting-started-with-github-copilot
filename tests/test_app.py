"""
Tests for the Mergington High School Activities API
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test"""
    # Store original participants
    original_participants = {
        name: activity["participants"].copy()
        for name, activity in activities.items()
    }
    
    yield
    
    # Restore original participants after test
    for name, activity in activities.items():
        activity["participants"] = original_participants[name]


class TestGetActivities:
    """Tests for the GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client, reset_activities):
        """Test that all activities are returned"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "Basketball Team" in data
        assert "Soccer Club" in data
        assert "Chess Club" in data
    
    def test_activities_have_required_fields(self, client, reset_activities):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_details in data.items():
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)
    
    def test_chess_club_has_initial_participants(self, client, reset_activities):
        """Test that Chess Club has its initial participants"""
        response = client.get("/activities")
        data = response.json()
        chess_club = data["Chess Club"]
        
        assert len(chess_club["participants"]) == 2
        assert "michael@mergington.edu" in chess_club["participants"]
        assert "daniel@mergington.edu" in chess_club["participants"]


class TestSignup:
    """Tests for the POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_for_activity_success(self, client, reset_activities):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Basketball Team/signup?email=student@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Signed up student@mergington.edu" in data["message"]
        
        # Verify participant was added
        assert "student@mergington.edu" in activities["Basketball Team"]["participants"]
    
    def test_signup_invalid_activity(self, client, reset_activities):
        """Test signup for non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Club/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_signup_duplicate_email(self, client, reset_activities):
        """Test signup with email already registered"""
        response = client.post(
            "/activities/Chess Club/signup?email=michael@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"]
    
    def test_signup_multiple_students(self, client, reset_activities):
        """Test multiple different students can sign up for same activity"""
        client.post(
            "/activities/Soccer Club/signup?email=alice@mergington.edu"
        )
        response = client.post(
            "/activities/Soccer Club/signup?email=bob@mergington.edu"
        )
        
        assert response.status_code == 200
        assert "alice@mergington.edu" in activities["Soccer Club"]["participants"]
        assert "bob@mergington.edu" in activities["Soccer Club"]["participants"]


class TestUnregister:
    """Tests for the POST /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success(self, client, reset_activities):
        """Test successful unregistration from an activity"""
        # First signup
        client.post(
            "/activities/Art Club/signup?email=artist@mergington.edu"
        )
        
        # Then unregister
        response = client.post(
            "/activities/Art Club/unregister?email=artist@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered artist@mergington.edu" in data["message"]
        
        # Verify participant was removed
        assert "artist@mergington.edu" not in activities["Art Club"]["participants"]
    
    def test_unregister_not_registered(self, client, reset_activities):
        """Test unregistering a student who is not registered"""
        response = client.post(
            "/activities/Basketball Team/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "not registered" in data["detail"]
    
    def test_unregister_invalid_activity(self, client, reset_activities):
        """Test unregistering from non-existent activity"""
        response = client.post(
            "/activities/Fake Club/unregister?email=student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_unregister_from_existing_participant(self, client, reset_activities):
        """Test unregistering an existing participant"""
        response = client.post(
            "/activities/Chess Club/unregister?email=michael@mergington.edu"
        )
        assert response.status_code == 200
        assert "michael@mergington.edu" not in activities["Chess Club"]["participants"]
        assert "daniel@mergington.edu" in activities["Chess Club"]["participants"]


class TestIntegration:
    """Integration tests for multiple endpoints"""
    
    def test_signup_and_unregister_cycle(self, client, reset_activities):
        """Test complete signup and unregister cycle"""
        email = "integration@mergington.edu"
        activity = "Drama Club"
        
        # Signup
        response = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        assert response.status_code == 200
        assert email in activities[activity]["participants"]
        
        # Verify it appears in activities list
        response = client.get("/activities")
        assert email in response.json()[activity]["participants"]
        
        # Unregister
        response = client.post(
            f"/activities/{activity}/unregister?email={email}"
        )
        assert response.status_code == 200
        assert email not in activities[activity]["participants"]
        
        # Verify it's removed from activities list
        response = client.get("/activities")
        assert email not in response.json()[activity]["participants"]
    
    def test_multiple_signups_and_unregisters(self, client, reset_activities):
        """Test multiple signup and unregister operations"""
        activity = "Debate Team"
        students = [
            "debater1@mergington.edu",
            "debater2@mergington.edu",
            "debater3@mergington.edu"
        ]
        
        # All sign up
        for email in students:
            response = client.post(
                f"/activities/{activity}/signup?email={email}"
            )
            assert response.status_code == 200
        
        # Verify all are registered
        response = client.get("/activities")
        participants = response.json()[activity]["participants"]
        for email in students:
            assert email in participants
        
        # Unregister the middle one
        response = client.post(
            f"/activities/{activity}/unregister?email=debater2@mergington.edu"
        )
        assert response.status_code == 200
        
        # Verify state
        response = client.get("/activities")
        participants = response.json()[activity]["participants"]
        assert "debater1@mergington.edu" in participants
        assert "debater2@mergington.edu" not in participants
        assert "debater3@mergington.edu" in participants
